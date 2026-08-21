#!/usr/bin/env python3
"""Per-item acceptance test for a finished /twbx-lint run.

Why this exists separately from `validate`: `validate` asserts the invariants it
can express, and it is structurally blind to rules that are violated by the
*absence* of an attribute — a field with no caption, a filter card with no
`mode=`, a colour map that collides only inside one viz. Every one of those has
shipped in a "green" run. This script re-derives each such rule from the packed
artifact and prints one line per rule, so the final report can say "I checked
every item" and mean it.

Usage:
    python3 scripts/verify_fixes.py <result.twbx | result.twb>

Exit codes: 0 = every check passed, 1 = at least one FAIL, 2 = usage error.
A FAIL is not automatically a defect — an analyst may have knowingly accepted
one (a kept Info popover, say). It means: state it in the report, with a reason
from the contract's permitted list.
"""
from __future__ import annotations

import os
import re
import sys
import zipfile
import xml.etree.ElementTree as ET

ACRONYMS = {
    "CRM", "NGR", "GGR", "ROI", "ROMI", "RFD", "RD", "LD", "ARPU", "ARPPU",
    "RTP", "AR", "HBL", "IN", "USD", "VIP", "ID", "CNT",
}
PLACEHOLDERS = ("Replace this object", "Update or Remove Chart",
                "Unknown Update Time", "Place filters in the container")
DROPDOWN_MODES = {"dropdown", "checkdropdown"}

results: list[tuple[bool, str, str]] = []


def check(ok: bool, rule: str, detail: str) -> None:
    results.append((ok, rule, detail))


# ------------------------------------------------------------------ loading --
def load(path: str) -> tuple[ET.Element, str, set[str], bytes]:
    """-> (root, twb_text, packaged_file_names, raw_bytes)"""
    if path.endswith(".twbx"):
        with zipfile.ZipFile(path) as z:
            twb = next(n for n in z.namelist() if n.endswith(".twb") and "/" not in n)
            raw = z.read(twb)
            names = set(z.namelist())
    else:
        raw = open(path, "rb").read()
        d = os.path.dirname(os.path.abspath(path))
        names = {os.path.relpath(os.path.join(r, f), d)
                 for r, _, fs in os.walk(d) for f in fs}
    return ET.fromstring(raw), raw.decode("utf-8"), names, raw


def title_case_ok(caption: str) -> bool:
    for tok in re.split(r"[ ()_/\-]", caption):
        if not tok or tok.upper() in ACRONYMS:
            continue
        letters = re.sub(r"[^A-Za-z]", "", tok)
        if len(letters) >= 3 and letters[0].islower():
            return False
    return True


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    path = sys.argv[1]
    root, text, packaged, raw = load(path)
    dss = root.find("datasources")
    main_ds = next((d for d in (dss if dss is not None else [])
                    if (d.get("name") or "").startswith("federated")), None)
    ws_parent, dash_parent = root.find("worksheets"), root.find("dashboards")
    worksheets = list(ws_parent) if ws_parent is not None else []
    dashboards = list(dash_parent) if dash_parent is not None else []

    # ---- 1. line endings survived the edit passes ---------------------------
    crlf, lf = raw.count(b"\r\n"), raw.count(b"\n") - raw.count(b"\r\n")
    check(lf == 0, "line endings",
          f"{crlf} CRLF, {lf} bare LF — a bare LF means a pass wrote without newline=''")

    # ---- 2. the load-breaker: corner-radius must not be in the file ---------
    n_cr = len(re.findall(r"attr='corner-radius", text))
    check(n_cr == 0, "corner-radius absent",
          "none" if not n_cr else
          f"{n_cr} corner-radius format(s) present — Tableau will refuse the file "
          "with D2E8DA72 (editing-rules #9b)")

    # ---- 3. every displayed field resolves to a caption --------------------
    cap = ({c.get("name"): c.get("caption") for c in main_ds.findall("column")}
           if main_ds is not None else {})
    # Resolve instance -> underlying column from EVERY column-instance in the
    # document, not just the main datasource: date-truncation instances like
    # [tdy:date:qk] are usually declared only in a worksheet's
    # <datasource-dependencies>, and a main-DS-only map sends them to the
    # regex fallback, which then reports a captioned field as "raw".
    inst = {c.get("name"): c.get("column") for c in root.iter("column-instance")}

    # Tableau pseudo-fields: shelf tokens that are not columns and never carry
    # a caption. Counting them as findings would make this check permanently red.
    PSEUDO = {":Measure Names", "Multiple Values", ":Measure Values"}

    def base_of(inner: str) -> str:
        seen = set()
        cur = f"[{inner}]"
        while cur in inst and inst[cur] and cur not in seen:   # follow the chain
            seen.add(cur)
            cur = inst[cur]
        if cur != f"[{inner}]":
            return cur
        # fallback: strip a trailing type code (:nk/:qk/:ok[:N]) and any leading
        # derivation tokens (none/usr/sum/tdy/twk/tmn/tyr/pcto:sum/...).
        s = inner
        s = re.sub(r":[a-z]{2}(:\d+)?$", "", s)
        while ":" in s:
            head, rest = s.split(":", 1)
            if re.fullmatch(r"[a-z]{3,4}", head):
                s = rest
            else:
                break
        return f"[{s}]"

    raw_named: list[str] = []
    checked = 0
    for w in worksheets:
        for shelf in ("rows", "cols"):
            el = w.find(f".//{shelf}")
            if el is None or not (el.text or "").strip():
                continue
            for f in re.findall(r"\[federated\.[^\]]*\]\.\[([^\]]+)\]", el.text):
                if f in PSEUDO:
                    continue
                b = base_of(f)
                if b.strip("[]") in PSEUDO:
                    continue
                checked += 1
                if cap.get(b) is None:
                    raw_named.append(f"{w.get('name')}:{b}")
    check(not raw_named, "field captions (no raw DB names)",
          f"{checked} shelf fields checked, all captioned" if not raw_named else
          f"{len(set(raw_named))} render the raw name: {sorted(set(raw_named))[:6]}")

    # ---- 4. captions are Title Case ---------------------------------------
    bad_case = [c.get("caption") for c in (main_ds.findall("column") if main_ds is not None else [])
                if c.get("caption") and "__tableau_internal_object_id__" not in (c.get("name") or "")
                and not title_case_ok(c.get("caption"))]
    check(not bad_case, "captions Title Case",
          f"{len(cap)} main-DS captions ok" if not bad_case else f"{bad_case}")

    # ---- 5. every filter card: multi-value dropdown + Apply + 50px pin ----
    no_mode, not_50, no_apply = [], [], []
    for dash in dashboards:
        for z in dash.iter("zone"):
            if z.get("type-v2") != "filter":
                continue
            zid = f"{dash.get('name')}:id={z.get('id')}"
            if (z.get("mode") or "") not in DROPDOWN_MODES:
                no_mode.append(f"{zid}(mode={z.get('mode')})")
            if z.get("show-apply") != "true":
                no_apply.append(zid)
            if z.get("fixed-size") != "50" or z.get("is-fixed") != "true":
                not_50.append(f"{zid}(fixed-size={z.get('fixed-size')},"
                              f"is-fixed={z.get('is-fixed')})")
    check(not no_apply, "filter Apply button",
          "show-apply='true' on every filter" if not no_apply else
          f"no show-apply='true' (goes on the zone, never the card): {no_apply}")
    check(not no_mode, "filter control type",
          "every card is a dropdown" if not no_mode else
          f"not a dropdown (mode=None means Tableau's List default): {no_mode}")
    check(not not_50, "filter card height 50px",
          "all pinned" if not not_50 else f"{not_50}")

    # ---- 6. colour: a declaration behind every binding, no per-viz collision
    decl: dict[str, dict] = {}
    member_colour: dict[str, str] = {}
    for scope in ([main_ds] if main_ds is not None else []) + worksheets:
        st = scope.find("style")
        for sr in (st.findall("style-rule") if st is not None else []):
            for enc in sr.findall("encoding"):
                if enc.get("attr") != "color":
                    continue
                decl[enc.get("field") or ""] = enc
                for m in enc.findall("map"):
                    for b in m.findall("bucket"):
                        member_colour[(b.text or "").strip()] = m.get("to")
    bindings = [c.get("column") for w in worksheets for c in w.iter("color")]
    undeclared = []
    for b in sorted(set(bindings)):
        tail = re.sub(r"^\[[^\]]*\]\.", "", b or "")
        enc = next((e for k, e in decl.items()
                    if tail in (k or "") or (k or "") in (b or "")), None)
        if enc is None:
            undeclared.append(f"{b}: no <encoding attr='color'> anywhere")
            continue
        # §B: the two dead forms that look right and render Tableau defaults.
        # A bare <encoding> with maps but no palette= is what an un-migrated
        # workbook looks like, and a hex census cannot see it.
        if not enc.get("palette"):
            undeclared.append(f"{b}: encoding has no palette= (renders defaults)")
        elif enc.get("type") == "palette" and not enc.findall("map"):
            undeclared.append(f"{b}: categorical palette= with no <map> children")
    check(not undeclared, "palette declared per colour binding",
          f"{len(set(bindings))} distinct binding(s), {len(decl)} declaration(s), "
          "each with palette= and per-member maps" if not undeclared
          else f"{undeclared}")

    collisions = []
    for w in worksheets:
        if not any((c.get("column") or "").endswith("[:Measure Names]")
                   for c in w.iter("color")):
            continue
        mem = [(g.get("member") or "").strip()
               for g in w.iter("groupfilter")
               if g.get("function") == "member" and g.get("level") == "[:Measure Names]"]
        cols = [member_colour.get(m) for m in mem if m]
        if cols and len(cols) != len(set(cols)):
            collisions.append(f"{w.get('name')}({cols})")
    check(not collisions, "no two series share a colour in one viz",
          "each colour-encoded viz has distinct hexes" if not collisions
          else f"{collisions}")

    # ---- 7. dashboard fit = Standard --------------------------------------
    zooms = [f"{wd.get('name')}:{vp.get('name')}"
             for wd in root.iter("window") if wd.get("class") == "dashboard"
             for vp in wd.iter("viewpoint") if vp.find("zoom") is not None]
    check(not zooms, "dashboard fit = Standard",
          "no <zoom> under any dashboard viewpoint" if not zooms else f"{zooms}")

    # ---- 8. every referenced Image/ file is packaged -----------------------
    refs = set(re.findall(r"Image/[^'\"<>]+", text))
    missing = sorted(r for r in refs if r not in packaged)
    check(not missing, "packaged assets",
          f"{len(refs)} Image/ ref(s) all present" if not missing else f"{missing}")

    # ---- 9. header + the three icons, in EITHER permitted form -------------
    for dash in dashboards:
        zs = list(dash.iter("zone"))
        painted = any(
            (f.get("attr"), (f.get("value") or "").lower()) == ("background-color", "#01001f")
            for z in zs for f in z.iter("format"))
        imgs = {z.get("param") for z in zs if z.get("type-v2") == "bitmap"}
        imgs |= {p.text for p in dash.iter("image-path")}          # <button> form
        want = {"Image/Logo.svg", "Image/Info.svg", "Image/Slack.svg"}
        gaps = sorted(w for w in want if w not in imgs)
        check(painted and not gaps, f"header on '{dash.get('name')}'",
              "painted #01001F, all three icons present"
              if painted and not gaps else
              f"painted={painted} missing={gaps}")

    # ---- 10. legends sit with their viz ------------------------------------
    orphans = []
    for dash in dashboards:
        for parent in dash.iter("zone"):
            kids = [k for k in parent if k.tag == "zone"]
            for z in kids:
                if z.get("type-v2") != "color":
                    continue
                if not any(s.get("name") == z.get("name") and s.get("type-v2") is None
                           for s in kids):
                    orphans.append(f"{dash.get('name')}:{z.get('name')}")
    check(not orphans, "legend is a sibling of its viz",
          "ok" if not orphans else f"{orphans}")

    # ---- 11. locale + no leftover template placeholders --------------------
    check(root.get("locale") == "en_GB", "workbook locale",
          f"locale={root.get('locale')!r}")
    left = [p for p in PLACEHOLDERS if p in text]
    check(not left, "template placeholders removed", "none" if not left else f"{left}")

    # ------------------------------------------------------------- report ---
    width = max(len(r) for _, r, _ in results)
    print(f"VERIFY {os.path.basename(path)}")
    for ok, rule, detail in results:
        print(f"  {'PASS' if ok else 'FAIL'}  {rule.ljust(width)}  {detail}")
    passed = sum(1 for ok, _, _ in results if ok)
    print(f"VERIFY: {passed}/{len(results)} checks passed")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
