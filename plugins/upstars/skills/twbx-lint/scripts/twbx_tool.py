#!/usr/bin/env python3
"""twbx_tool.py — deterministic helper for the /twbx-lint skill.

Fixed-format, short output by design: every subcommand prints a handful of
stable lines so the agent's token cost stays flat regardless of workbook size.

Subcommands
  clone   <src.twbx> [--results DIR]     copy into results/ as
                                         "YYYY-MM-DD_HH-MM-SS__<basename>"
  extract <file.twbx> <workdir>          unzip package, print TWB= path, and
                                         record a baseline sidecar (line endings,
                                         zone count) that pack checks against
  pack    <workdir> <out.twbx>           zip workdir back into a package; refuses
                                         when the .twb's line endings drifted
                                         since extract (--allow-eol-change
                                         overrides), reports the zone-count delta
  validate <file.twbx|file.twb>          full validation ladder (see below)
  open-verify <file.twbx> [--timeout N]  open in Tableau Desktop, watch its
                                         log, print one-line verdict; leaves
                                         Tableau open for human inspection

Validation ladder (everything learned the hard way in production):
  1. zip integrity (twbx)
  2. XML well-formedness of the .twb
  3. official XSD validation (tableau/tableau-document-schemas, bundled),
     with the two known-harmless quirks whitelisted (they appear on pristine
     Tableau-saved files too):
       - workbook "Missing child element(s) ... thumbnails/external/..."
       - extract attribute "_.fcp.*" "is not allowed"
  4. structural invariants the XSD alone does not catch or that crash Tableau:
       - datasource child ordering (all <column> before <column-instance>...)
       - unique dashboard zone ids
       - unique worksheet names and simple-id uuids
       - <action name> matches the bracketed [ ... ] pattern
       - every Image/... reference resolves to a file inside the package
       - every <format attr='X'> is in the XSD StyleAttribute enumeration
         (e.g. 'font-name' is NOT valid — the real one is 'font-family')
       - dashboard <button><toggle-action> may ONLY be
         tabdoc:toggle-button-click-action (anything else hard-crashes
         Tableau with logic-assert in ToggleDashboardButtonStrategy.cpp)
       - viewpoint <zoom type> in {percent, entire-view, fit-width, fit-height}
       - every worksheet zone on a dashboard is registered in that dashboard
         window's <viewpoints> (missing -> logic-assert HasVisualDoc ->
         open-workbook rk:early-termination, i.e. the file will not open)
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
import xml.etree.ElementTree as ET

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCHEMA = os.path.join(SKILL_DIR, "assets", "schema", "twb_2026.2.0.xsd")

MAX_ISSUE_LINES = 20

# Written by `extract` into the workdir, read by `pack`, never packed. Holds the
# facts about the file as it arrived that a later pass can silently destroy.
BASELINE_SIDECAR = ".twbx-lint-baseline.json"

DS_CHILD_ORDER = [
    "repository-location", "connection", "utility-dimensions", "dimension",
    "overridable-settings", "aliases", "column", "column-instance", "group",
    "mapped-images", "drill-paths", "unlinked-server-hierarchies",
    "folders-common", "folders-parameters", "actions", "calculated-members",
    "extract", "layout", "style", "semantic-values", "date-options",
    "default-date-format", "default-sorts", "field-sort-info",
    "datasource-dependencies", "explainability", "filter", "object-graph",
]
ZOOM_TYPES = {"percent", "entire-view", "fit-width", "fit-height"}

# Named so the PASS line can count them instead of carrying a literal that
# drifts. Keep in step with the numbered blocks in _structural_issues().
INVARIANTS = (
    "datasource child order", "dashboard zone id uniqueness",
    "worksheet name/uuid uniqueness", "action name pattern",
    "packaged asset references", "format attr enumeration",
    "button toggle-action", "viewpoint zoom type",
    "dashboard viewpoint registration", "mark colour palette declared",
    "dashboard viz fit = Standard", "filter card height",
    # --- style-checklist rules, enforced instead of merely written down -----
    "workbook locale", "worksheet text styling", "worksheet title run",
    "tooltip typography", "parameter control typography", "viz borders",
    "canvas width", "off-palette colours", "dashboard header",
    "filter panel", "legend beside its viz", "update-time block",
    "filter control mode", "template placeholders", "caption title case",
)

# Every colour the workbook is allowed to contain: the Upstars palettes as the
# bundled Preferences.tps spells them, plus the structural values the checklist
# names explicitly. Read from the .tps so the two can never drift apart.
STRUCTURAL_COLOURS = {
    "#333333",   # all viz text
    "#ffffff",   # header title text / palette neutral
    "#000000",   # dormant zone border (border-style='none' — must not be edited)
    "#f5f5f5",   # gridlines + filter panel background
    "#01001f",   # header background
    "#666666",   # on-dashboard comments per guide
}
TITLE_CASE_ACRONYMS = {
    "CRM", "NGR", "GGR", "ROI", "ROMI", "RFD", "RD", "LD", "ARPU", "ARPPU",
    "RTP", "AR", "HBL", "IN", "USD", "VIP", "ID",
}
PLACEHOLDERS = (
    "Replace this object", "Update or Remove Chart", "Unknown Update Time",
    "Place filters in the container",
)


def _upstars_colours() -> set[str]:
    tps = os.path.join(SKILL_DIR, "assets", "design-materials", "Preferences.tps")
    try:
        text = open(tps, encoding="utf-8").read()
    except OSError:
        return set()
    return {c.lower() for c in re.findall(r"<color>\s*(#[0-9a-fA-F]{6})\s*</color>",
                                          text)}


def _title_case_ok(caption: str) -> bool:
    """Words of 3+ letters start with a capital. Short words and known
    acronyms are left alone; trailing spaces are deliberate disambiguators
    between duplicated fields and are not a finding."""
    for tok in re.split(r"[ ()_/\-]", caption):
        if not tok or tok.upper() in TITLE_CASE_ACRONYMS:
            continue
        letters = re.sub(r"[^A-Za-z]", "", tok)
        if len(letters) >= 3 and letters[0].islower():
            return False
    return True

XSD_WHITELIST = (
    "Missing child element(s). Expected is one of",
    "_.fcp.",
    "fails to validate",
)

LOG_NOISE = (
    "EventsConfigurator", "connector-plugin-error", "libsalesforce",
    "qtwebengine_locales", "BentonSans", "Post spans request",
    "stream truncated",
)


def die(msg: str, code: int = 2) -> None:
    print(f"ERROR: {msg}")
    sys.exit(code)


def _twb_profile(path: str) -> dict:
    """Facts about a .twb that a later edit pass can destroy silently.

    Read as BYTES on purpose: Python's universal newlines convert CRLF to LF
    while reading, so a text-mode probe reports "no CRLF" even on a pristine
    CRLF file. Tableau writes CRLF, but a .twb some earlier pass already
    flattened is legitimately LF — the convention is per file, so `pack`
    compares against what `extract` saw, not against a fixed expectation.
    """
    data = open(path, "rb").read()
    crlf = data.count(b"\r\n")
    lf = data.count(b"\n") - crlf
    kind = ("mixed" if crlf and lf else
            "crlf" if crlf else "lf" if lf else "none")
    return {"eol": kind, "crlf": crlf, "lf": lf, "zones": data.count(b"<zone "),
            "preserve": {k: data.count(v) for k, v in PRESERVE_TAGS.items()}}


# Things an edit pass can destroy SILENTLY: the file stays schema-valid, opens
# in Tableau and validates, so nothing downstream notices. Measured at extract
# and re-measured at pack; a DROP is an error. Learned the hard way — a
# style-block rebuild that kept only <format/> children deleted a worksheet's
# colour palette encoding and the nested <formatted-text> of three filter
# titles, and every gate still said PASS.
PRESERVE_TAGS = {
    "encoding": b"<encoding ",
    "map": b"<map to=",
    "calculation": b"<calculation ",
    "column": b"<column ",
    "column-instance": b"<column-instance ",
    "style-rule": b"<style-rule ",
    "customized-tooltip": b"<customized-tooltip>",
    "formatted-text": b"<formatted-text>",
    "worksheet": b"<worksheet name=",
    "datasource": b"<datasource ",
    "filter": b"<filter ",
    "action": b"<action ",
}


def _load_baseline(workdir: str) -> dict | None:
    """The sidecar `extract` left, or None for a workdir made some other way."""
    side = os.path.join(workdir, BASELINE_SIDECAR)
    if not os.path.isfile(side):
        return None
    try:
        with open(side, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


# ---------------------------------------------------------------- clone ----
def cmd_clone(args: argparse.Namespace) -> None:
    src = os.path.abspath(args.src)
    if not os.path.isfile(src):
        die(f"source not found: {src}")
    if args.results:
        results = os.path.abspath(args.results)
    else:
        parent = os.path.dirname(src)
        if os.path.basename(parent) == "dummy":
            results = os.path.join(os.path.dirname(parent), "results")
        else:
            results = os.path.join(os.getcwd(), "results")
    if f"{os.sep}dummy{os.sep}" in results + os.sep:
        die("refusing to write into a dummy/ directory")
    os.makedirs(results, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    dest = os.path.join(results, f"{ts}__{os.path.basename(src)}")
    shutil.copy2(src, dest)
    print(f"RESULT={dest}")


# -------------------------------------------------------------- extract ----
def cmd_extract(args: argparse.Namespace) -> None:
    pkg = os.path.abspath(args.package)
    workdir = os.path.abspath(args.workdir)
    os.makedirs(workdir, exist_ok=True)
    with zipfile.ZipFile(pkg) as z:
        z.extractall(workdir)
    twbs = [f for f in os.listdir(workdir) if f.lower().endswith(".twb")]
    if not twbs:
        die("no .twb found at package root after extraction")
    twb = os.path.join(workdir, twbs[0])
    prof = _twb_profile(twb)
    with open(os.path.join(workdir, BASELINE_SIDECAR), "w",
              encoding="utf-8") as f:
        json.dump({"twb": twbs[0], **prof}, f)
    print(f"WORKDIR={workdir}")
    print(f"TWB={twb}")
    print(f"EOL={prof['eol']} ZONES={prof['zones']}")


# ----------------------------------------------------------------- pack ----
def cmd_pack(args: argparse.Namespace) -> None:
    workdir = os.path.abspath(args.workdir)
    out = os.path.abspath(args.out)
    if f"{os.sep}dummy{os.sep}" in out + os.sep:
        die("refusing to write into a dummy/ directory")
    twbs = [f for f in os.listdir(workdir) if f.lower().endswith(".twb")]
    if not twbs:
        die("workdir has no .twb at its root; refusing to pack")
    # Line-ending guard. A python pass that opened the .twb without newline=''
    # rewrites every CRLF as LF. The file stays schema-valid and Tableau opens
    # it, so neither validate nor open-verify notices, while every later diff
    # against a Tableau save becomes unreadable — two shipped results were
    # flattened exactly this way before this check existed.
    prof = _twb_profile(os.path.join(workdir, twbs[0]))
    base = _load_baseline(workdir)
    if base and base.get("eol") and prof["eol"] != base["eol"]:
        if not args.allow_eol_change:
            die(f"line endings changed since extract: {base['eol']} -> "
                f"{prof['eol']} (crlf {base['crlf']}->{prof['crlf']}, lf "
                f"{base['lf']}->{prof['lf']}). Redo the edit with "
                "open(path, newline='') on BOTH read and write, or pass "
                "--allow-eol-change if the change is intended.", code=4)
        print(f"WARNING: line endings {base['eol']} -> {prof['eol']} "
              "(allowed via --allow-eol-change)")
    # Destruction guard: adding is fine, losing is not. Catches a rebuild pass
    # that silently dropped children it did not know about.
    if base and base.get("preserve"):
        lost = [(k, base["preserve"][k], prof["preserve"].get(k, 0))
                for k in base["preserve"]
                if prof["preserve"].get(k, 0) < base["preserve"][k]]
        if lost and not args.allow_loss:
            die("elements disappeared since extract: "
                + "; ".join(f"{k} {was}->{now}" for k, was, now in lost)
                + ". An edit pass dropped content it did not intend to touch "
                  "(a style/zone rebuild that kept only the children it knew "
                  "about is the usual cause). Fix the pass so it preserves "
                  "unknown children, or pass --allow-loss if the removal is "
                  "deliberate.", code=5)
        if lost:
            print("WARNING: deliberate removals (--allow-loss): "
                  + "; ".join(f"{k} {was}->{now}" for k, was, now in lost))
    tmp = out + ".tmp"
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
        for root, _dirs, files in os.walk(workdir):
            for name in sorted(files):
                if root == workdir and name == BASELINE_SIDECAR:
                    continue  # bookkeeping: must never land inside a package
                full = os.path.join(root, name)
                arc = os.path.relpath(full, workdir)
                z.write(full, arc)
    os.replace(tmp, out)
    print(f"PACKED={out}")
    print(f"SIZE={os.path.getsize(out)}")
    if base:
        delta = prof["zones"] - base.get("zones", prof["zones"])
        drift = f" ({delta:+d} vs extract)" if delta else ""
        print(f"EOL={prof['eol']} ZONES={prof['zones']}{drift}")


# ------------------------------------------------------------- validate ----
def _style_attr_enum() -> set[str]:
    text = open(SCHEMA, encoding="utf-8").read()
    m = re.search(
        r'<xs:simpleType name="StyleAttribute-ST">.*?</xs:simpleType>',
        text, re.DOTALL)
    if not m:
        return set()
    return set(re.findall(r'<xs:enumeration value="([^"]+)"/>', m.group(0)))


def _xmllint_schema_issues(twb: str) -> tuple[list[str], int, bool]:
    """Returns (real_issues, ignored_count, ran)."""
    if shutil.which("xmllint") is None or not os.path.isfile(SCHEMA):
        return [], 0, False
    proc = subprocess.run(
        ["xmllint", "--noout", "--schema", SCHEMA, twb],
        capture_output=True, text=True)
    if proc.returncode == 0:
        return [], 0, True
    ignored = 0
    grouped: dict[str, tuple[int, str]] = {}  # msg -> (count, first_loc)
    for line in proc.stderr.splitlines():
        line = line.strip()
        if not line:
            continue
        if any(w in line for w in XSD_WHITELIST):
            ignored += 1
            continue
        # token-bounded output: drop enumeration dumps and temp paths,
        # group identical messages across lines
        line = re.sub(r"is not an element of the set \{.*$",
                      "is not in the schema enumeration", line)
        m = re.match(r"^(?:.*?\.twb):(\d+):\s*(.*)$", line)
        loc, msg = (f"twb:{m.group(1)}", m.group(2)) if m else ("", line)
        count, first = grouped.get(msg, (0, loc))
        grouped[msg] = (count + 1, first)
    real = [f"{c}× {msg[:180]} (first at {first})" if c > 1
            else f"{msg[:180]} ({first})" if first else msg[:200]
            for msg, (c, first) in grouped.items()]
    return real, ignored, True


def _structural_issues(twb: str, package_dir: str | None) -> list[str]:
    issues: list[str] = []
    text = open(twb, encoding="utf-8").read()
    try:
        root = ET.parse(twb).getroot()
    except ET.ParseError as e:
        return [f"XML parse error: {e}"]

    # 1. datasource child ordering
    rank = {t: i for i, t in enumerate(DS_CHILD_ORDER)}
    ds_parent = root.find("datasources")
    if ds_parent is not None:
        for ds in ds_parent.findall("datasource"):
            last, last_tag = -1, ""
            for child in ds:
                r = rank.get(child.tag)
                if r is None:
                    continue
                if r < last:
                    issues.append(
                        f"datasource '{ds.get('name')}': <{child.tag}> after "
                        f"<{last_tag}> violates content-model order")
                last, last_tag = max(last, r), child.tag

    # 2. zone id uniqueness per dashboard
    dashboards = root.find("dashboards")
    if dashboards is not None:
        for dash in dashboards.findall("dashboard"):
            ids: list[str] = []

            def walk(z):
                if z.get("id") is not None:
                    ids.append(z.get("id"))
                for c in z:
                    if c.tag == "zone":
                        walk(c)
            zones = dash.find("zones")
            if zones is not None:
                for tz in zones.findall("zone"):
                    walk(tz)
            dupes = sorted({i for i in ids if ids.count(i) > 1})
            if dupes:
                issues.append(
                    f"dashboard '{dash.get('name')}': duplicate zone ids {dupes}")

    # 3. worksheet name / simple-id uniqueness
    ws_parent = root.find("worksheets")
    if ws_parent is not None:
        names = [w.get("name") for w in ws_parent.findall("worksheet")]
        dupes = sorted({n for n in names if names.count(n) > 1})
        if dupes:
            issues.append(f"duplicate worksheet names: {dupes}")
        uuids = [w.find("simple-id").get("uuid")
                 for w in ws_parent.findall("worksheet")
                 if w.find("simple-id") is not None]
        du = sorted({u for u in uuids if uuids.count(u) > 1})
        if du:
            issues.append(f"duplicate worksheet simple-id uuids: {du}")

    # 4. action name pattern
    actions = root.find("actions")
    if actions is not None:
        for a in actions.findall("action"):
            name = a.get("name") or ""
            if not re.fullmatch(r"\[.*\]", name):
                issues.append(
                    f"action name {name!r} must match the bracketed "
                    "[ ... ] pattern")

    # 5. Image/ references resolve inside the package
    if package_dir is not None:
        refs = sorted(set(re.findall(r"Image/[^'\"<]+", text)))
        for ref in refs:
            if not os.path.isfile(os.path.join(package_dir, ref)):
                issues.append(f"missing packaged asset: {ref}")

    # 6. <format attr> enumeration
    enum = _style_attr_enum()
    if enum:
        used = set(re.findall(r"<format attr='([^']+)'", text))
        for attr in sorted(used - enum):
            issues.append(
                f"<format attr='{attr}'> is not a valid StyleAttribute "
                "(e.g. use 'font-family', never 'font-name')")

    # 7. button toggle-action constraint (crash guard)
    for m in re.finditer(r"<toggle-action>([^<]*)</toggle-action>", text):
        action = m.group(1).strip()
        if not action.startswith("tabdoc:toggle-button-click-action"):
            issues.append(
                "dashboard <button> toggle-action must be "
                f"tabdoc:toggle-button-click-action, found: {action[:70]!r} "
                "(anything else crashes Tableau on load)")

    # 8. viewpoint zoom types
    for m in re.finditer(r"<zoom type='([^']+)'", text):
        if m.group(1) not in ZOOM_TYPES:
            issues.append(f"invalid <zoom type='{m.group(1)}'>")

    # 9. a worksheet placed on a dashboard must ALSO be registered in that
    #    dashboard window's <viewpoints>; without it Tableau hits
    #    logic-assert m_windowDoc->HasVisualDoc(...) and the workbook does not
    #    open at all. Matched per dashboard window, and read through
    #    ElementTree attributes on purpose: a regex for name='…' also matches
    #    the tail of friendly-name='…'.
    ws_names = {w.get("name")
                for w in (ws_parent.findall("worksheet")
                          if ws_parent is not None else [])}
    viewpoints: dict[str, set[str]] = {}
    windows = root.find("windows")
    for win in (windows.findall("window") if windows is not None else []):
        if win.get("class") != "dashboard":
            continue
        vps = win.find("viewpoints")
        viewpoints[win.get("name")] = {
            v.get("name") for v in vps.findall("viewpoint")
        } if vps is not None else set()
    if dashboards is not None and ws_names:
        for dash in dashboards.findall("dashboard"):
            used: set[str] = set()

            def walk_names(z):
                if z.get("name") in ws_names:
                    used.add(z.get("name"))
                for c in z:
                    if c.tag == "zone":
                        walk_names(c)
            zones = dash.find("zones")
            if zones is not None:
                for tz in zones.findall("zone"):
                    walk_names(tz)
            missing = sorted(used - viewpoints.get(dash.get("name"), set()))
            if missing:
                issues.append(
                    f"dashboard '{dash.get('name')}': worksheet zone(s) "
                    f"{missing} missing from <viewpoints> — Tableau will refuse "
                    "to open the workbook (HasVisualDoc)")

    # 10. every mark colour binding must have a palette declared *somewhere*.
    #     A <color column='…'/> inside <encodings> only says WHICH field drives
    #     colour; the palette itself lives in a separate <style-rule
    #     element='mark'><encoding attr='color' … palette='…'>, or in a
    #     type='palette' encoding carrying <map to='#hex'> per member — in the
    #     worksheet's OR the datasource's <style>. With no declaration Tableau
    #     paints the viz in its own default palette and writes NO hex into the
    #     twb at all, so a hex census and a palette= grep both report "clean"
    #     while the chart on screen is Tableau blue/orange. That is why this is
    #     coded here instead of left to a lint grep.
    #     Checking merely that "a declaration exists" is NOT enough — two dead
    #     forms pass that test and still render defaults, so the shape is
    #     checked per case (shapes transcribed from a Tableau UI save):
    #       categorical -> datasource <style>, unprefixed field, <map> per member
    #       continuous  -> worksheet <style>, prefixed field, self-closing
    #       separate-domains -> one worksheet entry PER MEASURE, not one on
    #                           [Multiple Values]
    def _field(ref: str | None) -> str:
        """Last [...] segment. Bindings carry the datasource prefix
        ([ds].[none:x:nk]) while datasource-level declarations do not
        ([:Measure Names]), so compare on the tail only."""
        parts = re.findall(r"\[[^\[\]]*\]", ref or "")
        return parts[-1] if parts else (ref or "")

    ds_decl: dict[str, ET.Element] = {}
    ds_parent = root.find("datasources")
    for ds in (ds_parent.findall("datasource") if ds_parent is not None else []):
        for enc in ds.iter("encoding"):
            if enc.get("attr") == "color":
                ds_decl[_field(enc.get("field"))] = enc
    for w in (ws_parent.findall("worksheet") if ws_parent is not None else []):
        where = f"worksheet '{w.get('name')}'"
        tbl = w.find("table")
        ws_decl: dict[str, ET.Element] = {}
        for enc in (tbl.iter("encoding") if tbl is not None else []):
            if enc.get("attr") == "color":
                ws_decl[_field(enc.get("field"))] = enc
        for encs in w.iter("encodings"):
            for c in encs.findall("color"):
                fld = _field(c.get("column"))
                if c.get("separate-domains") == "true":
                    if not [k for k in ws_decl if k != fld]:
                        issues.append(
                            f"{where}: {fld} uses separate-domains but the only "
                            "palette declared is on the combined field — with "
                            "separate legends each measure needs its own "
                            "<encoding attr='color' …> or it renders Tableau "
                            "defaults (checklist B)")
                    continue
                # `or` would be wrong here: a childless Element is falsy today
                # (and the semantics change in a future Python), so a valid but
                # empty datasource declaration would silently fall through.
                enc = ds_decl.get(fld)
                if enc is None:
                    enc = ws_decl.get(fld)
                if enc is None:
                    issues.append(
                        f"{where}: colour driven by {fld} with no palette "
                        "declared — renders in Tableau's default palette "
                        "(checklist B: purple default)")
                elif fld.endswith(":nk]") and enc.find("map") is None:
                    issues.append(
                        f"{where}: categorical colour on {fld} declares "
                        f"palette={enc.get('palette')!r} with no <map> entries "
                        "— Tableau ignores a bare palette= on a dimension and "
                        "renders defaults (checklist B)")

    # 11. Fit stays Standard on every dashboard viz (analyst-confirmed).
    #     Standard is the ABSENCE of <zoom> — that is what Tableau writes — so
    #     'percent' is accepted as its explicit spelling and the three real fits
    #     are the finding. Worksheet-window <zoom> is that sheet's own view
    #     setting, not a dashboard fit, and is deliberately not checked.
    for win in (windows.findall("window") if windows is not None else []):
        if win.get("class") != "dashboard":
            continue
        vps = win.find("viewpoints")
        for v in (vps.findall("viewpoint") if vps is not None else []):
            zoom = v.find("zoom")
            if zoom is not None and zoom.get("type") not in (None, "percent"):
                issues.append(
                    f"dashboard '{win.get('name')}' viewpoint "
                    f"'{v.get('name')}': fit is '{zoom.get('type')}', must stay "
                    "Standard — delete the <zoom> element (checklist D)")

    # 12. every dashboard filter card is 50px tall (analyst-confirmed).
    #     fixed-size without is-fixed is inert, so both are required. Desktop
    #     zone tree only: Phone device layouts are auto-generated.
    if dashboards is not None:
        for dash in dashboards.findall("dashboard"):
            bad_filters: list[str] = []

            def walk_filters(z):
                if z.get("type-v2") == "filter" and (
                        z.get("fixed-size") != "50" or z.get("is-fixed") != "true"):
                    bad_filters.append(
                        f"id={z.get('id')}(fixed-size={z.get('fixed-size')},"
                        f"is-fixed={z.get('is-fixed')})")
                for c in z:
                    if c.tag == "zone":
                        walk_filters(c)
            zones = dash.find("zones")
            if zones is not None:
                for tz in zones.findall("zone"):
                    walk_filters(tz)
            if bad_filters:
                issues.append(
                    f"dashboard '{dash.get('name')}': filter card(s) not 50px — "
                    f"{', '.join(bad_filters)}; every filter zone needs "
                    "fixed-size='50' is-fixed='true' (checklist D)")

    issues += _checklist_issues(root, text, dashboards, ws_parent)
    return issues


def _fmt_map(el) -> dict[str, str]:
    """attr -> value for the generic (non field-scoped) formats of a style-rule."""
    return {f.get("attr"): f.get("value") for f in el.findall("format")
            if f.get("field") is None}


def _checklist_issues(root, text: str, dashboards, ws_parent) -> list[str]:
    """The style-checklist rules that are mechanically decidable from the XML.

    They live in code rather than in the checklist prose for one reason: a run
    that overlooks a written rule still reports success, and that is exactly
    how a delivery once shipped with no palettes and Tableau-default colours.
    An invariant cannot be overlooked — `validate` never prints PASS while one
    of these is unmet, and the skill's contract forbids reporting success
    without a PASS.
    """
    issues: list[str] = []
    TEXT_ELS = ("axis", "cell", "datalabel", "header", "label", "quick-filter")
    BODY = {"font-family": "Tableau Book", "font-size": "9", "color": "#333333"}
    worksheets = ws_parent.findall("worksheet") if ws_parent is not None else []
    dash_list = dashboards.findall("dashboard") if dashboards is not None else []

    # 13. workbook locale
    if root.get("locale") != "en_GB":
        issues.append(f"workbook locale is {root.get('locale')!r}, must be 'en_GB'")

    for w in worksheets:
        name, tbl = w.get("name"), w.find("table")
        style = tbl.find("style") if tbl is not None else None
        rules = ({r.get("element"): r for r in style.findall("style-rule")}
                 if style is not None else {})

        # 14. body typography on every text-bearing element
        for el in TEXT_ELS:
            got = _fmt_map(rules[el]) if el in rules else {}
            missing = [f"{a}={v}" for a, v in BODY.items() if got.get(a) != v]
            if missing:
                issues.append(
                    f"worksheet '{name}': style-rule '{el}' missing "
                    f"{', '.join(missing)} (checklist A: Tableau Book 9 #333333)")

        # 15. a styled title (the update-time block is the 9px/right variant)
        runs = [r for r in w.iter("run")
                if r in list(w.find("layout-options").iter("run"))] \
            if w.find("layout-options") is not None else []
        if not runs:
            issues.append(f"worksheet '{name}': no <layout-options><title> — its "
                          "name renders in Tableau's default font (checklist A)")
        else:
            r0 = runs[0]
            if r0.get("fontname") != "Tableau Book" or r0.get("fontcolor") != "#333333":
                issues.append(
                    f"worksheet '{name}': title run is "
                    f"{r0.get('fontname')!r}/{r0.get('fontcolor')!r}, must be "
                    "'Tableau Book'/'#333333' (checklist A)")
            elif r0.get("fontsize") not in ("12", "9"):
                issues.append(
                    f"worksheet '{name}': title font-size {r0.get('fontsize')!r} "
                    "— 12 bold for a viz title, 9 for the update-time block")

        # 16. tooltips
        for tt in w.iter("customized-tooltip"):
            for r in tt.iter("run"):
                if (r.get("fontname"), r.get("fontsize"), r.get("fontcolor")) != \
                        ("Tableau Book", "9", "#333333"):
                    issues.append(
                        f"worksheet '{name}': tooltip run is not Tableau Book/9/"
                        "#333333 (checklist A)")
                    break
            else:
                continue
            break

        # 18. gridlines/borders on visible vizzes
        for el in ("cell", "header", "pane"):
            if _fmt_map(rules.get(el, ET.Element("x"))).get("border-color") != "#f5f5f5":
                issues.append(
                    f"worksheet '{name}': style-rule '{el}' has no "
                    "border-color='#f5f5f5' (checklist B)")

    # 20. every colour must come from the Upstars set
    allowed = _upstars_colours() | STRUCTURAL_COLOURS
    if allowed:
        seen = {h.lower() for h in re.findall(r"#[0-9a-fA-F]{6}", text)}
        for bad in sorted(seen - allowed):
            issues.append(f"off-palette colour {bad} — not in the Upstars set "
                          "(checklist B)")

    # 26. leftover template placeholders
    for ph in PLACEHOLDERS:
        if ph in text:
            issues.append(f"template placeholder left in the workbook: {ph!r}")

    # 27. captions are Title Case (main datasource columns)
    ds_parent = root.find("datasources")
    for ds in (ds_parent.findall("datasource") if ds_parent is not None else []):
        for col in ds.findall("column"):
            cap = col.get("caption")
            if cap and "__tableau_internal_object_id__" not in (col.get("name") or "") \
                    and not _title_case_ok(cap):
                issues.append(
                    f"caption {cap!r} is not Title Case (words of 3+ letters "
                    "start with a capital; acronyms stay as-is) (checklist A)")

    # 27b. ...and a field with NO caption at all renders its raw DB name, which
    # the loop above can never see: it skips `cap is None`, and a field with no
    # main-DS <column> is not even enumerated. That is the common case — 10
    # fields once shipped as user_id / sub_id1 / user_pseudo_id in a crosstab
    # with every gate green. Enumerate what RENDERS, then demand a caption.
    main_caps = {}
    for ds in (ds_parent.findall("datasource") if ds_parent is not None else []):
        for col in ds.findall("column"):
            main_caps[(col.get("name") or "").strip("[]")] = col.get("caption")
    shown: dict[str, str] = {}
    for w in worksheets:
        for tag in ("rows", "cols"):
            el = w.find(f"table/{tag}")
            for f in re.findall(r"\[none:([^:\]]+):[a-z]+\]", (el.text or "") if el is not None else ""):
                shown.setdefault(f, f"worksheet '{w.get('name')}' {tag}")
    for dash in dash_list:
        for z in dash.iter("zone"):
            if z.get("type-v2") != "filter":
                continue
            m = re.search(r"\[none:([^:\]]+):[a-z]+\]", z.get("param") or "")
            if m:
                shown.setdefault(m.group(1), f"filter card on '{dash.get('name')}'")
    for field, where in sorted(shown.items()):
        if not main_caps.get(field):
            issues.append(
                f"field {field!r} renders ({where}) but has no caption on a "
                "main-datasource <column> — it shows its raw DB name; add a "
                "Title-Cased caption there, not in the deps copies (checklist A)")

    # ---- dashboard-level rules ------------------------------------------------
    upd_sheets = {w.get("name") for w in worksheets
                  for c in w.iter("calculation")
                  if "NOW()" in (c.get("formula") or "")}
    for dash in dash_list:
        dname = dash.get("name")
        zones = dash.find("zones")
        allz: list = []

        def walk(z):
            allz.append(z)
            for c in z:
                if c.tag == "zone":
                    walk(c)
        for tz in (zones.findall("zone") if zones is not None else []):
            walk(tz)
        zstyle = {id(z): _fmt_map(z.find("zone-style"))
                  for z in allz if z.find("zone-style") is not None}
        backgrounds = [v.get("background-color") for v in zstyle.values()
                       if v.get("background-color")]

        # 19. canvas width
        size = dash.find("size")
        if size is not None and size.get("maxwidth"):
            wpx = int(size.get("maxwidth"))
            if not 1200 <= wpx <= 1600:
                issues.append(f"dashboard '{dname}': canvas width {wpx} outside "
                              "1200–1600 (checklist C)")

        # 21. branded header
        hdr = [z for z in allz
               if (zstyle.get(id(z)) or {}).get("background-color", "").lower()
               == "#01001f"]
        if not hdr:
            issues.append(f"dashboard '{dname}': no header zone (no container "
                          "painted #01001F) — checklist D requires one per "
                          "dashboard (see header-recipe.md)")
        else:
            imgs = {z.get("param") for z in allz if z.get("type-v2") == "bitmap"}
            for want in ("Image/Logo.svg", "Image/Info.svg", "Image/Slack.svg"):
                if want not in imgs:
                    issues.append(f"dashboard '{dname}': header is missing "
                                  f"{want} (checklist D)")

        # 22. filter panel: painted, and captioned FILTERS
        if any(z.get("type-v2") == "filter" for z in allz):
            if sum(1 for b in backgrounds if b.lower() == "#f5f5f5") != 1:
                issues.append(
                    f"dashboard '{dname}': expected exactly one container "
                    "painted #f5f5f5 (the filter panel); found "
                    f"{sum(1 for b in backgrounds if b.lower() == '#f5f5f5')} "
                    "(checklist C)")
            if "FILTERS" not in "".join(
                    (r.text or "") for z in allz for r in z.iter("run")):
                issues.append(f"dashboard '{dname}': filter panel has no "
                              "'FILTERS' caption (checklist C)")

        # 20b. no stray container backgrounds beyond header + filter panel
        stray = [b for b in backgrounds if b.lower() not in ("#01001f", "#f5f5f5")]
        if stray:
            issues.append(f"dashboard '{dname}': container background(s) "
                          f"{sorted(set(stray))} — only the header (#01001F) and "
                          "the filter panel (#f5f5f5) may be painted (checklist C)")

        # 23. a legend sits with its viz, not in the filter panel
        by_parent = {id(p): [c for c in p if c.tag == "zone"] for p in allz}
        for z in allz:
            if z.get("type-v2") != "color":
                continue
            siblings = next((v for k, v in by_parent.items() if z in v), [])
            if not any(s.get("name") == z.get("name") and s.get("type-v2") is None
                       for s in siblings):
                issues.append(
                    f"dashboard '{dname}': legend for '{z.get('name')}' is not a "
                    "sibling of its viz — legends go under their viz, never in "
                    "the filter panel (checklist C)")

        # 24. the update-time block
        if upd_sheets and not any(z.get("name") in upd_sheets for z in allz):
            issues.append(f"dashboard '{dname}': no update-time block "
                          "(checklist D)")
        elif not upd_sheets:
            issues.append("no update-time worksheet in the workbook: a NOW() "
                          "calculated field shown as a text mark (checklist D)")

        # 25. every filter is Multiple Values (dropdown) + Show Apply Button.
        # Absence-shaped on both halves, so neither may be tested by "is the
        # wrong value present": Tableau's own default is the multi-value LIST
        # and it writes NO mode at all, and Apply is simply a missing attribute.
        # A run that read the old 2-vs-3+ split shipped single-value dropdowns
        # on two filters; the rule now has no member-count branch (checklist D).
        for z in allz:
            if z.get("type-v2") != "filter":
                continue
            if z.get("mode") != "checkdropdown":
                issues.append(
                    f"dashboard '{dname}': filter zone id={z.get('id')} has "
                    f"mode={z.get('mode')!r} — every filter is a multi-value "
                    "dropdown: mode='checkdropdown' (no mode at all = Tableau's "
                    "default LIST) (checklist D)")
            if z.get("show-apply") != "true":
                issues.append(
                    f"dashboard '{dname}': filter zone id={z.get('id')} has no "
                    "show-apply='true' — every filter needs the Apply button; "
                    "the attribute goes on the zone, not the card (checklist D)")

        # 17. parameter control typography
        if any(z.get("type-v2") == "paramctrl" for z in allz):
            dstyle = dash.find("style")
            drules = ({r.get("element"): r for r in dstyle.findall("style-rule")}
                      if dstyle is not None else {})
            for el in ("parameter-ctrl", "parameter-ctrl-title"):
                got = _fmt_map(drules[el]) if el in drules else {}
                if any(got.get(a) != v for a, v in BODY.items()):
                    issues.append(
                        f"dashboard '{dname}': has a parameter control but its "
                        f"<style> lacks '{el}' with Tableau Book 9 #333333 "
                        "(checklist A)")
    return issues


# --------------------------------------------------------------- doctor ----
def cmd_doctor(args: argparse.Namespace) -> None:
    """Pre-flight the environment BEFORE a run starts.

    Without this a run does all the work and only discovers at open-verify that
    it cannot finish — and a run that cannot reach `OPEN-VERIFY: OK` cannot
    report success at all, because SKIP is not success. Every check here is
    something that was missing on a real machine at least once.
    """
    project = os.path.abspath(args.project or os.getcwd())
    rows: list[tuple[str, str]] = []          # (level, message); level: OK/WARN/MISSING
    def ok(m): rows.append(("OK", m))
    def warn(m): rows.append(("WARN", m))
    def miss(m): rows.append(("MISSING", m))

    # `from __future__ import annotations` (top of this file) defers every
    # annotation to a string, so the `X | None` syntax below never needs
    # PEP 604's runtime `|` support - it is never evaluated. Verified by
    # actually running this script's doctor and full test suite under
    # Python 3.9.25: both passed clean. 3.9 is the real, tested floor, not
    # 3.10 - so this check compares against it instead of asserting a
    # number nobody has falsified.
    PY_FLOOR = (3, 9)
    py_ok = sys.version_info >= PY_FLOOR
    py_msg = (f"python {sys.version.split()[0]} "
              f"({PY_FLOOR[0]}.{PY_FLOOR[1]}+ required for this script)")
    ok(py_msg) if py_ok else miss(py_msg)

    xmllint = shutil.which("xmllint")
    ok(f"xmllint {xmllint}") if xmllint else miss(
        "xmllint not on PATH — the cheap XSD check before packing is "
        "unavailable (macOS ships it; on Linux install libxml2-utils)")

    jq = shutil.which("jq")
    ok(f"jq {jq}") if jq else warn(
        "jq not on PATH — .claude/hooks/run-tests-on-change.sh (reruns "
        "tests when the skill's own sources change) cannot parse its "
        "payload without it, and now fails loud (exit 2) instead of "
        "silently doing nothing (macOS 15+ ships jq; otherwise "
        "brew install jq / apt install jq)")

    app = _find_tableau_app()
    if app:
        try:
            installed = sorted(a for a in os.listdir("/Applications")
                               if a.startswith("Tableau Desktop") and a.endswith(".app"))
        except OSError:
            installed = []
        ok(f"Tableau Desktop -> {os.path.basename(app)}")
        if len(installed) > 1:
            warn(f"{len(installed)} Tableau versions installed; open-verify picks "
                 f"the LAST alphabetically ({os.path.basename(app)}), which is not "
                 "necessarily the newest")
    else:
        miss("Tableau Desktop not found in /Applications — open-verify would "
             "print SKIP, and SKIP is not success, so no run can be completed "
             "on this machine (macOS only)")

    logdir = os.path.dirname(TABLEAU_LOG)
    ok(f"Tableau logs {logdir}") if os.path.isdir(logdir) else warn(
        f"{logdir} does not exist — open-verify has nowhere to read the load "
        "verdict from; it appears after Tableau has run once")

    # dummy/ and results/ are runtime directories, not repo content: a fresh
    # clone has neither, and they cannot be carried as tracked placeholders
    # because the read-only guard refuses any write into dummy/ — including
    # creating a .gitkeep there. So doctor heals them instead.
    for sub in ("dummy", "results"):
        p = os.path.join(project, sub)
        if os.path.isdir(p):
            ok(f"{sub}/ present")
        elif args.fix:
            os.makedirs(p, exist_ok=True)
            ok(f"{sub}/ created (--fix)")
        else:
            miss(f"{sub}/ missing under {project} — the workflow reads its input "
                 f"from dummy/ and writes every result to results/; re-run with "
                 f"--fix to create them")

    assets = {
        "XSD schema": SCHEMA,
        "Preferences.tps": os.path.join(SKILL_DIR, "assets", "design-materials",
                                        "Preferences.tps"),
        "header-recipe.md": os.path.join(SKILL_DIR, "references", "header-recipe.md"),
        "style-checklist.md": os.path.join(SKILL_DIR, "references",
                                           "style-checklist.md"),
        "twbx-editing-rules.md": os.path.join(SKILL_DIR, "references",
                                              "twbx-editing-rules.md"),
    }
    for label, path in assets.items():
        ok(f"asset {label}") if os.path.isfile(path) else miss(
            f"asset {label} missing at {path}")
    icons = [f for f in ("1 Logo.svg", "2 Info.svg", "3 Slack.svg")
             if not os.path.isfile(os.path.join(SKILL_DIR, "assets",
                                                "design-materials", f))]
    ok("header icons (Logo/Info/Slack)") if not icons else miss(
        f"header icons missing from assets/design-materials/: {icons}")

    # The guard ships inside the plugin, but a project may also wire its own
    # copy under .claude/hooks/. Accept either, and treat "declared anywhere"
    # as wired: a plugin declares it in hooks.json, a project in settings.json.
    guard_candidates = (
        os.path.join(SKILL_DIR, "..", "..", "hooks", "protect-dummy.py"),
        os.path.join(project, ".claude", "hooks", "protect-dummy.py"),
    )
    guard = next((p for p in guard_candidates if os.path.isfile(p)), None)
    declarations = (
        os.path.join(SKILL_DIR, "..", "..", "hooks", "hooks.json"),
        os.path.join(project, ".claude", "settings.json"),
    )
    wired = any(
        os.path.isfile(d)
        and "protect-dummy" in open(d, encoding="utf-8", errors="replace").read()
        for d in declarations)
    if guard and wired:
        ok("dummy/ guard hook present and wired")
    else:
        warn("dummy/ read-only guard not active (hook file or its declaration "
             "is missing) — dummy/ is the read-only inbox by contract, so "
             "without it nothing stops a write to the source")

    user_tps = os.path.expanduser(
        "~/Documents/My Tableau Repository/Preferences.tps")
    if os.path.isfile(user_tps):
        n = len(re.findall(r"<color-palette ",
                           open(user_tps, encoding="utf-8", errors="replace").read()))
        warn(f"{n} palettes installed in your Preferences.tps. NOT VERIFIED "
             "whether Tableau needs them installed to render a workbook whose "
             "own <preferences> already carries the definitions — assume they "
             "may be required until someone tests it on a clean machine")
    else:
        warn("no Preferences.tps in ~/Documents/My Tableau Repository — the "
             "Upstars palettes may not be available to the UI; install "
             "assets/design-materials/Preferences.tps (see 03-color-palettes.md)")

    try:
        import tableauhyperapi  # noqa: F401
        ok("tableauhyperapi available (optional: reading values out of extracts)")
    except ImportError:
        rows.append(("INFO", "tableauhyperapi not installed (optional; only "
                             "needed to read values out of a .hyper extract)"))

    blockers = [m for lvl, m in rows if lvl == "MISSING"]
    warns = [m for lvl, m in rows if lvl == "WARN"]
    head = "BLOCKED" if blockers else "READY"
    tail = f" ({len(blockers)} blocker(s), {len(warns)} warning(s))" if (
        blockers or warns) else ""
    print(f"DOCTOR: {head}{tail}")
    for lvl, m in rows:
        print(f"  {lvl:<8} {m}")
    if blockers:
        print("  -> do not start a run that cannot reach OPEN-VERIFY: OK; "
              "report the blockers instead")
        sys.exit(6)


def cmd_validate(args: argparse.Namespace) -> None:
    target = os.path.abspath(args.target)
    if not os.path.isfile(target):
        die(f"not found: {target}")
    issues: list[str] = []
    tmpdir = None
    package_dir = None
    try:
        if target.lower().endswith(".twbx"):
            tmpdir = tempfile.mkdtemp(prefix="twbx-validate-")
            try:
                with zipfile.ZipFile(target) as z:
                    bad = z.testzip()
                    if bad:
                        issues.append(f"zip integrity failed at: {bad}")
                    z.extractall(tmpdir)
            except zipfile.BadZipFile as e:
                print(f"VALIDATE {os.path.basename(target)}: FAIL")
                print(f"  1. not a zip/twbx: {e}")
                sys.exit(1)
            package_dir = tmpdir
            twbs = [f for f in os.listdir(tmpdir) if f.lower().endswith(".twb")]
            if not twbs:
                print(f"VALIDATE {os.path.basename(target)}: FAIL")
                print("  1. no .twb inside the package")
                sys.exit(1)
            twb = os.path.join(tmpdir, twbs[0])
        else:
            twb = target
            maybe_pkg = os.path.dirname(twb)
            if os.path.isdir(os.path.join(maybe_pkg, "Image")):
                package_dir = maybe_pkg

        try:
            ET.parse(twb)
        except ET.ParseError as e:
            print(f"VALIDATE {os.path.basename(target)}: FAIL")
            print(f"  1. XML not well-formed: {e}")
            sys.exit(1)

        xsd_issues, ignored, xsd_ran = _xmllint_schema_issues(twb)
        issues.extend(xsd_issues)
        issues.extend(_structural_issues(twb, package_dir))

        name = os.path.basename(target)
        if issues:
            print(f"VALIDATE {name}: FAIL ({len(issues)} issue(s))")
            for i, msg in enumerate(issues[:MAX_ISSUE_LINES], 1):
                print(f"  {i}. {msg[:220]}")
            if len(issues) > MAX_ISSUE_LINES:
                print(f"  ... +{len(issues) - MAX_ISSUE_LINES} more")
            sys.exit(1)
        xsd_note = (f"XSD OK ({ignored} known-harmless quirks ignored)"
                    if xsd_ran else "XSD skipped (xmllint/schema unavailable)")
        print(f"VALIDATE {name}: PASS — zip OK, XML OK, {xsd_note}, "
              f"structure OK ({len(INVARIANTS)} invariants)")
    finally:
        if tmpdir:
            shutil.rmtree(tmpdir, ignore_errors=True)


# ---------------------------------------------------------- open-verify ----
TABLEAU_LOG = os.path.expanduser(
    "~/Documents/My Tableau Repository/Logs/log.txt")
LOCK_DIR = "/tmp/twbx-open-verify.lock"


LOG_TS_RE = re.compile(r'^\{"ts":"([0-9\-]{10}T[0-9:.]+)"')
LOG_PID_RE = re.compile(r'"pid":(\d+)')
LOG_RK_RE = re.compile(r'"rk":"([^"]+)"')
LOG_ASSERT_RE = re.compile(
    r'"condition":"([^"]*)".*?"filename":"([^"]*)".*?"linenumber":(\d+)')


def _find_tableau_app() -> str | None:
    try:
        apps = sorted(
            a for a in os.listdir("/Applications")
            if a.startswith("Tableau Desktop") and a.endswith(".app"))
    except OSError:  # no /Applications at all (i.e. not macOS)
        return None
    return f"/Applications/{apps[-1]}" if apps else None


def _tableau_pids() -> set[int]:
    """PIDs of the MAIN Tableau processes, excluding their helpers.

    Only the main process writes the load verdict, and its pid is the `"pid"`
    field of every log line — that is what makes pid a usable "is this line
    mine?" test. The workbook name cannot serve for that: the verdict line
    carries it in `ctx.wb`, but crash lines have no `ctx` block at all, so
    name-matching silently discards exactly the diagnostics we need.
    """
    try:
        out = subprocess.run(["ps", "-Ao", "pid=,command="],
                             capture_output=True, text=True, timeout=15).stdout
    except (OSError, subprocess.SubprocessError):
        return set()
    pids = set()
    for line in out.splitlines():
        pid, _, cmd = line.strip().partition(" ")
        if pid.isdigit() and cmd.strip().endswith("/MacOS/Tableau"):
            pids.add(int(pid))
    return pids


def _log_files() -> list[str]:
    """Every live instance log in Tableau's Logs directory.

    Tableau keeps ONE NUMBERED LOG PER CONCURRENT INSTANCE (log.txt, log_1.txt …
    log_5.txt) and rotates each to *_bk.txt on start. Watching only log.txt
    loses the verdict of every instance but the first — measured: a second
    instance wrote `rk=ok` into log_5.txt while log.txt got only the FileOpen
    event, which is the real reason verdicts went missing.
    """
    d = os.path.dirname(TABLEAU_LOG)
    try:
        names = sorted(os.listdir(d))
    except OSError:
        return []
    return [os.path.join(d, n) for n in names
            if n.startswith("log") and n.endswith(".txt") and "_bk" not in n]


def _workbook_locks(target: str, since: float) -> list[str]:
    """Tableau's own "I have this workbook open" markers beside the file:
    `.~<basename without extension>__<pid>.twbr`. Independent of the logs, so it
    still answers the question when a verdict lands somewhere we cannot see.
    Only locks touched after our launch count; stale ones from earlier runs sit
    in the same directory.
    """
    stem = os.path.splitext(os.path.basename(target))[0]
    out = []
    try:
        names = os.listdir(os.path.dirname(target))
    except OSError:
        return out
    for n in names:
        if not (n.startswith(f".~{stem}__") and n.endswith(".twbr")):
            continue
        try:
            if os.path.getmtime(os.path.join(os.path.dirname(target), n)) >= since - 5:
                out.append(n)
        except OSError:
            pass
    return out


def _log_fresh(line: str, since: datetime.datetime) -> bool:
    """False only when the line's own timestamp predates our launch.

    Tableau rotates log.txt on start, which forces a re-read from offset 0; this
    keeps a previous instance's verdict for the same path from being mistaken
    for ours. Unparseable timestamp -> treat as fresh rather than drop evidence.
    """
    m = LOG_TS_RE.match(line)
    if not m:
        return True
    try:
        ts = datetime.datetime.strptime(m.group(1), "%Y-%m-%dT%H:%M:%S.%f")
    except ValueError:
        return True
    return ts >= since - datetime.timedelta(seconds=5)


def _acquire_lock(timeout: float = 300.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            os.mkdir(LOCK_DIR)
            return True
        except FileExistsError:
            # stale lock (>10 min) gets broken
            try:
                if time.time() - os.path.getmtime(LOCK_DIR) > 600:
                    os.rmdir(LOCK_DIR)
                    continue
            except OSError:
                pass
            time.sleep(3)
    return False


def cmd_open_verify(args: argparse.Namespace) -> None:
    target = os.path.abspath(args.target)
    if not os.path.isfile(target):
        die(f"not found: {target}")
    app = _find_tableau_app()
    if app is None:
        # exit 3, NOT 0: the skill's contract is "done only when open-verify
        # prints OK". A zero here let a machine without Tableau run the whole
        # pipeline and report success without ever testing that the file opens.
        print("OPEN-VERIFY: SKIP — Tableau Desktop not installed; "
              "the open test did NOT run (this step is unverified)")
        sys.exit(3)
    if not _acquire_lock():
        print("OPEN-VERIFY: FAIL — could not acquire Tableau lock in 5 min")
        sys.exit(1)
    try:
        # Tableau ROTATES each log to *_bk.txt on every app start, so a raw byte
        # offset from a previous run silently skips the verdict line in the fresh
        # file (proven failure: verdict at 2.2MB, stale offset 5.9MB -> permanent
        # miss). Track every live instance log (see _log_files) by identity
        # (inode) plus a monotonic read position; restart at 0 on rotation.
        state: dict[str, tuple[int, int]] = {}
        for p in _log_files():
            try:
                st = os.stat(p)
                state[p] = (st.st_ino, st.st_size)
            except OSError:
                pass
        # Two independent ways to tell "this line is about my run", used for
        # different things: the workbook display name from ctx {"wb": "..."}
        # pins the VERDICT line (that instance may open other workbooks too),
        # while the pid pins the DIAGNOSTICS (they carry no workbook name).
        stem = os.path.splitext(os.path.basename(target))[0]
        base = os.path.basename(target)
        pids_before = _tableau_pids()
        launched = datetime.datetime.now()
        launched_epoch = time.time()
        subprocess.run(["open", "-a", app, target], check=True)
        deadline = time.time() + args.timeout
        verdict, detail, diag = None, [], []
        noise = 0
        fileopen_at = None
        ours: set[int] = set()
        while time.time() < deadline and verdict is None:
            time.sleep(3)
            if not ours:
                # `open -a` starts a process only when Tableau was NOT running;
                # a warm instance handles the open itself and no new pid
                # appears, which leaves `ours` empty and the name as the only
                # available signal.
                ours = _tableau_pids() - pids_before
            for path in _log_files():
                try:
                    st = os.stat(path)
                except OSError:
                    continue
                # a log created after our launch is a new instance's: read it whole
                ino, pos = state.get(path, (st.st_ino, 0))
                if st.st_ino != ino or st.st_size < pos:  # rotated or truncated
                    ino, pos = st.st_ino, 0
                if st.st_size == pos:
                    state[path] = (ino, pos)
                    continue
                # binary mode + manual position: text-mode iteration forbids
                # tell(), and we need an exact resume offset between polls
                with open(path, "rb") as f:
                    f.seek(pos)
                    for raw in f:
                        pos += len(raw)
                        line = raw.decode("utf-8", errors="replace")
                        if not _log_fresh(line, launched):
                            continue
                        # The verdict is the open-workbook result kind. rk=ok
                        # means loaded; anything else (early-termination, error)
                        # is a failure, and the diagnostics collected below
                        # explain it.
                        if ("end-workspace.open-workbook" in line
                                and stem in line):
                            m = LOG_RK_RE.search(line)
                            rk = m.group(1) if m else "?"
                            verdict = "OK" if rk == "ok" else "FAIL"
                            if verdict == "FAIL":
                                detail.append(f"open-workbook rk={rk}")
                            break
                        if "Processing FileOpen event" in line and base in line:
                            # Proof that Tableau received THIS file — matched by
                            # our own filename, so it counts from any instance.
                            m = LOG_TS_RE.match(line)
                            fileopen_at = m.group(1) if m else "?"
                            continue
                        lp = LOG_PID_RE.search(line)
                        lpid = int(lp.group(1)) if lp else None
                        if ours and lpid is not None and lpid not in ours:
                            continue  # another instance's line
                        if '"k":"logic-assert"' in line:
                            # NOT a verdict on its own: a healthy start emits a
                            # dozen of these (condition 'wbc') and then loads
                            # fine (measured: 14 asserts, then rk=ok 63s later).
                            # Keep them as evidence for a bad verdict.
                            m = LOG_ASSERT_RE.search(line)
                            diag.append("logic-assert %s (%s:%s)" % (
                                m.group(1), os.path.basename(m.group(2)),
                                m.group(3)) if m else "logic-assert (unparsed)")
                            continue
                        if "show-detailed-error-dialog" in line:
                            verdict = "FAIL"
                            detail.append(line.strip()[:300])
                            break
                        if '"sev":"error"' in line:
                            if any(n in line for n in LOG_NOISE):
                                noise += 1
                            elif stem in line or (ours and lpid in ours):
                                detail.append(line.strip()[:300])
                state[path] = (ino, pos)
                if verdict is not None:
                    break
            if verdict is None and ours and not (_tableau_pids() & ours):
                verdict = "FAIL"
                detail.append(f"the instance we launched (pid {sorted(ours)}) "
                              "exited without writing a verdict — hard crash")
        # collapse repeated diagnostics: 14 identical asserts are one fact
        seen: dict[str, int] = {}
        for d in diag:
            seen[d] = seen.get(d, 0) + 1
        diag_lines = [f"{d} ×{n}" if n > 1 else d for d, n in seen.items()]
        if verdict == "OK":
            print(f"OPEN-VERIFY: OK — workbook loaded (rk=ok, "
                  f"{noise} irrelevant startup errors ignored, "
                  f"{len(diag)} benign startup asserts). "
                  "Tableau left open for inspection.")
            sys.exit(0)
        if verdict == "FAIL":
            print("OPEN-VERIFY: FAIL — Tableau reported a load error:")
            for d in detail[-5:] + diag_lines[-5:]:
                print(f"  {d}")
            sys.exit(1)
        # No verdict. Do NOT call that a failure: measured on a HEALTHY workbook
        # opened by an already-running Tableau, the FileOpen event is logged and
        # no open-workbook event follows (the instance that actually loaded it
        # wrote rk=ok into its own log file). So report what is known, and use
        # Tableau's own lock file as the independent answer to "did it open?".
        locks = _workbook_locks(target, launched_epoch)
        print(f"OPEN-VERIFY: INCONCLUSIVE — no load verdict in {args.timeout}s")
        if fileopen_at:
            print(f"  Tableau did receive the file (FileOpen event at "
                  f"{fileopen_at})")
        else:
            print("  no FileOpen event for this file in any watched log — "
                  "Tableau may never have received it")
        if locks:
            print(f"  but it holds an open-workbook lock on it ({locks[0]}), so "
                  "the file did open — only the rk verdict is missing")
        elif fileopen_at:
            print("  and no open-workbook lock (.twbr) appeared beside it, "
                  "which is how a file that fails to load looks — treat as "
                  "suspect and check the Tableau window")
        if pids_before and not ours:
            print(f"  Tableau was already running (pid {sorted(pids_before)}); "
                  "quitting it and re-running gives an unambiguous verdict")
        if diag_lines or detail:
            print("  evidence seen meanwhile (may be unrelated):")
            for d in (detail[-3:] + diag_lines[-3:]):
                print(f"    {d}")
        sys.exit(1)
    finally:
        try:
            os.rmdir(LOCK_DIR)
        except OSError:
            pass


# ----------------------------------------------------------------- main ----
def main() -> None:
    p = argparse.ArgumentParser(prog="twbx_tool.py")
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("clone")
    c.add_argument("src")
    c.add_argument("--results", default=None)
    c.set_defaults(fn=cmd_clone)

    e = sub.add_parser("extract")
    e.add_argument("package")
    e.add_argument("workdir")
    e.set_defaults(fn=cmd_extract)

    k = sub.add_parser("pack")
    k.add_argument("workdir")
    k.add_argument("out")
    k.add_argument("--allow-eol-change", action="store_true",
                   help="pack even if the .twb's line endings drifted since "
                        "extract (default: refuse)")
    k.add_argument("--allow-loss", action="store_true",
                   help="pack even if elements disappeared since extract "
                        "(default: refuse — a silent drop is the usual sign of "
                        "a rebuild pass that discarded children it did not "
                        "know about)")
    k.set_defaults(fn=cmd_pack)

    d = sub.add_parser("doctor")
    d.add_argument("project", nargs="?", default=None,
                   help="project root holding dummy/ and results/ "
                        "(default: current directory)")
    d.add_argument("--fix", action="store_true",
                   help="create the dummy/ and results/ directories if absent "
                        "(the only thing doctor is allowed to change)")
    d.set_defaults(fn=cmd_doctor)

    v = sub.add_parser("validate")
    v.add_argument("target")
    v.set_defaults(fn=cmd_validate)

    o = sub.add_parser("open-verify")
    o.add_argument("target")
    # 240s: eval runs proved 90s is too short for a cold Tableau start
    # (3x INCONCLUSIVE on a valid file that loaded fine at ~150s)
    o.add_argument("--timeout", type=int, default=240)
    o.set_defaults(fn=cmd_open_verify)

    args = p.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
