---
name: twbx-lint
description: Lints and auto-fixes a Tableau packaged workbook (.twbx) against the Upstars style guide, then proves the result opens cleanly in Tableau Desktop. Takes a file path (or picks the newest .twbx in dummy/), clones it into results/ with a timestamped name, applies typography/color/layout fixes via safe XML editing, validates against the official Tableau XSD plus crash-guard invariants, and performs a real open-in-Tableau verification. Use for any request to lint, restyle, style-guide-check, or fix a .twbx/.twb workbook.
disable-model-invocation: true
---

# /twbx-lint — Upstars style lint & fix for Tableau workbooks

Argument: `$ARGUMENTS` — path to a `.twbx` (absolute, or relative to the
project). If empty, take the **newest** `.twbx` in `<project>/dummy/`.

Non-negotiable contract:
- `dummy/` is a read-only inbox (a PreToolUse hook denies writes — do not
  fight it). All work happens on a clone in `results/`.
- The run is only DONE when `validate` prints PASS on the **packed** result
  AND `open-verify` prints OK. Never report success without both lines.
  `SKIP` (no Tableau on this machine — exit 3) and `INCONCLUSIVE` are **not**
  OK: the open test never happened, so the success template does not apply.
- Keep token use flat: rely on the scripts below (they print short,
  fixed-format output); `grep` the twb for targets instead of reading it
  whole; report with the template at the bottom.
- **The whole checklist is the scope.** The deliverable is a file that
  satisfies every rule in `references/style-checklist.md`. Exactly three things
  may end up unfixed, and the report has to say which one applies:
  (a) it is a section E item ("What NOT to do");
  (b) the checklist itself says to **report** it rather than change it — it
      uses that word where it means it (e.g. corner radius on a
      colored-background dashboard);
  (c) it needs an asset that `assets/design-materials/` does not ship (name the
      missing file).
  "It's a build, not a lint fix", "that's layout surgery", "too risky",
  "the user didn't ask for it" are **not** exceptions — if they were, the rule
  would not be in the checklist. A rule that looks too big is a signal to open
  the matching recipe in `references/`, not to demote it to a note. The
  checklist's preamble says it plainly: *fix what the file violates; report
  anything you can't fix mechanically* — and "mechanically" is about whether a
  procedure exists, not about how many zones it touches.

Tooling (all paths relative to this skill directory):
`scripts/twbx_tool.py` — `doctor | clone | extract | pack | validate | open-verify`.
`scripts/verify_fixes.py <result>` — the step-9 per-item acceptance test; covers
the absence-shaped rules `validate` cannot express, one `PASS`/`FAIL` line per
rule, non-zero exit on any `FAIL`.

Before editing anything, read these two references — they encode hard-won
crash knowledge; skipping them has historically produced files that refuse
to open:
- `references/twbx-editing-rules.md` — package anatomy, load-crash landmines
  (font-family vs font-name, datasource child order, dashboard-viewpoint
  registration, hand-authored-button DOM-load failure, quote escaping, ...),
  log-based failure diagnosis.
- `references/style-checklist.md` — the lint rules themselves (typography,
  color, layout, behavior) including analyst overrides of the written guide.
Checklist §D requires a branded **header** on every dashboard, so a workbook
without one is *violating* the checklist rather than merely lacking an optional
extra — building it belongs to the run like any other fix. Read
`references/header-recipe.md` before you start: it is the crash-safe zone
recipe, and it already answers the two questions that otherwise stall the job —
how to ship the Info icon, and to use the placeholder period text when the
analyst has not given you one.

**If the workbook already has a header, lint it — do not rebuild it**, and do
not delete a working Info toggle to turn `validate` green: that form is §D-legal
and costs two known false positives. `header-recipe.md` § *Linting an existing
header* has the wiring check and the exact invariant numbers.
The full prose guide is bundled at `references/style-guide/` (01-structure …
99-checklist + palettes .tps) — consult it only when a checklist item is
ambiguous. The skill is self-contained: it never depends on where the user
keeps her own copies of guides, workbooks or design materials.

## Workflow

0. **Pre-flight.** `python3 scripts/twbx_tool.py doctor` (add `--fix` to create
   a missing `dummy/`/`results/`). It prints one block and exits 6 on a blocker.
   Run it *first*: otherwise the expensive discovery happens at step 7, after
   all the work — a machine without Tableau Desktop can never print
   `OPEN-VERIFY: OK`, and `SKIP` is not success, so such a run cannot be
   completed at all. **On a blocker, stop and report it rather than starting.**
1. **Resolve input.** Locate the source `.twbx` from `$ARGUMENTS` (else
   newest in `dummy/`). Record `shasum -a 256` of the source now; you must
   show at the end that it is unchanged.
2. **Clone.** `python3 scripts/twbx_tool.py clone "<src>"` → prints
   `RESULT=<results/TIMESTAMP__name.twbx>`. Everything below touches only
   this clone.
3. **Extract.** `... extract "<result>" <scratch-workdir>` → prints `TWB=` plus
   `EOL=`/`ZONES=`, and records them in a sidecar that `pack` checks against.
   Use a scratchpad directory, not the project.
4. **Lint.** Run `... validate "<result>"` for structural findings, then
   grep the twb against every rule in `references/style-checklist.md`
   (targeted greps: `fontsize=`, `fontcolor=`, `attr='color'`,
   `background-color`, `border-color`, `corner-radius`, `<zoom type=`,
   `caption='`, `fontalignment`, `<map to=` for semantic-mapped fields
   (`Project`/`VIP Status`/`Provider`), palette hexes).
   Then run a **presence sweep**. Grep only ever finds a wrong value that is
   *present*; it is structurally blind to a required thing that is *absent*,
   and those are precisely the rules that get missed — a grep returning `0`
   reads like "clean here" when it actually means "the rule is violated
   everywhere". For each of the following, `0` is a **finding, not a pass**:
   header zone per dashboard · legend as the last child of its viz container
   rather than in the filter panel · `#f5f5f5` on the filter container ·
   `padding-left/right/top/bottom` on containers · update-time block ·
   `fixed-size='50' is-fixed='true'` on every filter card ·
   `mode='checkdropdown'` **and** `show-apply='true'` on every filter card ·
   a captioned main-DS `<column>` for every field that renders · every `Image/`
   file the twb references · **a declared palette behind every `<color
   column=…/>` mark binding**.
   (Dashboard **fit** is the mirror image — there `Standard` means the `<zoom>`
   element is *absent*, so presence is the finding; see checklist §D.)
   That last one is the trap the others teach: a colour encoding with no
   `palette=` and no `<map to=>` writes **no hex at all**, so a hex census and a
   `palette=` grep both report "clean" while the chart renders in Tableau's
   default blue/orange. Enumerate the bindings and check each has a declaration —
   don't infer colour health from the hex list. The fix is prescribed
   (purple default, checklist §B); it is never a "report-only" item.
   **`validate` is absence-blind in exactly the same way — its findings are a
   floor, never your work-list.** This is the deeper version of the trap above,
   and it has cost a delivered run twice. Any invariant that reads an attribute
   before testing it goes silent when the attribute is missing, so the rule
   scores `0` precisely where it is most violated. Two confirmed cases, both
   found by the analyst after a run reported "146/150 fixed":
   Both known cases — a field with no caption at all, and a filter card with no
   `mode=` — are now invariants themselves (27b and 25), so `validate` does flag
   them; fix a missing `mode` **before** pinning the card to 50px, or you clip
   the list you just left in place.
   The generalisable move, which beats memorising the list: for each checklist
   rule ask **"what does the XML look like when this rule is satisfied by
   default, or not expressed at all?"** If the answer is "no attribute", then no
   grep and no invariant will ever flag it, and the only thing that finds it is
   enumerating the objects the rule is *about* — sheets, filter zones, colour
   bindings — and checking each one.
   Build one findings list: `rule → count → fix`, covering sections A–D.
   Anything in section E ("What NOT to do") is excluded from fixing.
5. **Fix.** Apply fixes to the extracted `.twb` — exact-string `Edit` for
   one-off changes, a small python pass for bulk replaces (guard it with exact
   `.count()` assertions so a wrong anchor fails loudly, not silently).
   **Every python pass reads and writes with `newline=''`** — a plain
   `open(p).read()` / `.write()` silently rewrites Tableau's CRLF as LF, which
   still validates and still opens, while making every later diff against a
   Tableau save unreadable; `pack` refuses such a file. Respect every
   landmine in `references/twbx-editing-rules.md` (especially: only
   `font-family`, column ordering, no URL buttons, correct quote escaping).
   Missing packaged icons come from `assets/design-materials/`.
   Scope note: when the user narrows the task ("поменяй только X, больше
   ничего не трогай"), the narrowing applies to *styling choices* — it never
   waives workability: pre-existing packaging defects that `validate` flags
   (missing referenced assets, invalid attrs, broken structure) are always
   in scope, because the deliverable is contractually "рабочий файл".
   Mention such repairs separately in the report.
6. **Pack + round-trip.** On a large package (100 MB+, where `pack`+`validate`
   is slow), first XSD-check the edited `.twb` cheaply: `xmllint --noout
   --schema assets/schema/twb_2026.2.0.xsd "<twb>"` (ignore the harmless
   "workbook: Missing child element … thumbnails/external" line). Then
   `... pack <workdir> "<result>"` and re-run `... validate "<result>"` on the
   packed file. It must print PASS; if it prints FAIL, fix and repeat — do not proceed.
   If `pack` itself refuses with `line endings changed since extract`, redo the
   edit with `newline=''`; do not reach for `--allow-eol-change`.
7. **Open-verify.** Do not `kill -TERM` a Tableau instance holding this path
   just before running it — on the evidence so far that correlates with a
   missing verdict span and a spurious INCONCLUSIVE (references §5, which also
   gives the log keys that distinguish "loaded, verdict absent" from a real
   failure, and warns that a missing `.twbr` is not a reliable negative).
   `... open-verify "<result>"` — opens the file in
   Tableau Desktop, watches Tableau's own log for the load verdict, prints
   one line, and leaves the workbook open so the analyst can look at it
   immediately. If FAIL: diagnose via the log lines it printed (see
   references §5), fix, go to step 6. If INCONCLUSIVE: say so honestly.
8. **Acceptance on the open workbook.** `validate` reads XML; it cannot see a
   declaration that Tableau ignores. Everything below has been shipped wrong at
   least once *with every gate green*, so ask the analyst to confirm it in the
   window `open-verify` just left open — naming the sheet, not "please check":
   - **colours** on every viz that colours by a field. ⚠️ Tableau's default
     diverging palette **is** `orange_blue_diverging_10_0`, so an orange/blue
     viz proves nothing either way — say which palette should be visible.
   - **filter cards** — all the same height, nothing clipped (a date/relative-
     date card is the one that clips first at 50px).
   - **fit** — no viz squashed to fit its zone.
   - **header** — icons visible, i.e. the `Image/` files really resolved.
   Two traps around this step:
   - **Look at the right window.** Instances pile up across re-packs (§5). If
     more than one is open on the same path, the analyst is probably looking at
     the older one. Confirm exactly one via `.~<basename>__<pid>.twbr`.
   - **A UI edit invalidates the file you validated.** If the analyst fixes
     anything in Tableau and saves, re-run `validate` on the *saved* file: a UI
     save re-emits zones (a colour change recreated a legend outside its
     container — §4b) and materialises what actually took effect. Tableau's own
     save is also the ground truth for learning any shape you had to guess (§4).
9. **Per-item verification — always, and always last.**
   `python3 scripts/verify_fixes.py "<result>"` on the **packed** artifact. It
   prints one `PASS`/`FAIL` line per rule and exits non-zero on any `FAIL`.
   It re-derives the absence-shaped rules from the artifact: a shelf field still
   showing its raw DB name, a filter card with no `mode=`, an `<encoding>` with
   no `palette=`, two series sharing a hex in one viz, a bare `\n` from a pass
   that forgot `newline=''`.
   Then close the loop by hand: walk the step-4 findings list and tick off
   **every line** against this output plus `validate`. The point is that
   "I made the edit" and "the edit is in the shipped file" are different claims,
   and only the second one counts — a pass that asserted its anchors can still
   have been rebuilt over, packed from the wrong workdir, or undone by a later
   pass. Three gates, all on the same packed file, all quoted in the report:
   `verify_fixes` · `validate` · `open-verify`.
   A `FAIL` here is not automatically a defect — the analyst may have knowingly
   accepted one (a kept Info popover). It means: name it on the `Не сделано:`
   line with a reason from the permitted list, never leave it unmentioned.
   If `verify_fixes` and `validate` disagree, say so and explain which is right;
   that disagreement is information (it is how the Info-button false positives
   were characterised) and it is how this script earns its keep.
   Extend the script when a run teaches you a new absence-shaped rule — that is
   cheaper than re-teaching every future run, and it is what turned two
   analyst-found misses into two permanent checks.
10. **Integrity.** Re-hash the source in `dummy/` — must equal step 1.
11. **Report** using exactly this template (fill the placeholders, keep it
   this short):

```
✅ <full path to result file>
Исправлено (N): <category: count; category: count; ...>
Чеклист: A типографика <✓ | ✗N> · B цвет <✓ | ✗N> · C макет <✓ | ✗N> · D поведение <✓ | ✗N>
Не сделано: <rule → why → E | report-only | нет ассета | Tableau отвергает (с доказательством)>  (или «—»)
Проверка: <the VERIFY: N/N line from verify_fixes.py>
Валидация: <the PASS line from validate>
Tableau: <the exact open-verify line — OK, or SKIP/INCONCLUSIVE if it wasn't OK>
Приёмка: <what the analyst must confirm in the open window — or «подтверждено»>
Исходник dummy/: не изменён (sha256 совпадает)
```

The `Чеклист:` line is the point of the template: it makes you state a verdict
on all four sections, including the ones your greps never returned a hit for,
so a section can't pass by being forgotten. Every `✗` needs a matching entry on
the `Не сделано:` line, and every entry there has to end in one of the permitted
categories from the contract above. If you find yourself writing a reason that is
none of them, the rule isn't exempt — go and fix it.

There is a fourth permitted category, and it is deliberately expensive to claim:
**Tableau itself rejects the edit.** It costs a measurement, not an opinion —
quote the two `open-verify` runs (with the attribute → FAIL, identical build
without it → `rk=ok`) that isolate the offending change. That is how the
`corner-radius` rule moved from "editable from raw XML" to report-only. Without
that evidence it is not this category, it is an excuse, and the rule stands.
"Too risky", "layout surgery", "validate disagrees with the checklist" are still
not exits — the last one means characterise the false positive and say which
source is right, not skip the rule.

If any step cannot succeed after honest retries, stop and report the exact
failing command output instead of the success template.

## Setup on a new machine

`doctor` (step 0) checks everything checkable, so this section only covers what
it cannot tell you itself:

- **macOS only, in practice.** `open-verify` looks for `Tableau Desktop*.app`
  in `/Applications` and nowhere else. On Windows or Linux it returns SKIP —
  and since SKIP is not success, the workflow has no valid ending there. Treat
  the skill as macOS-only until someone writes the other launcher.
- **The bundled XSD is `twb_2026.2.0.xsd`.** Against a much newer Tableau it
  will start reporting attributes it has never heard of. That is a stale
  schema, not a broken workbook — refresh it from
  github.com/tableau/tableau-document-schemas rather than deleting the check.
- **`dummy/` and `results/` are runtime directories, not repo content.** A
  fresh clone has neither; `doctor --fix` creates them. They cannot ship as
  tracked placeholders because the read-only guard refuses every write into
  `dummy/`, including creating a file there — as intended.
- **Upstars palettes (`Preferences.tps`).** `doctor` reports whether they are
  installed but flags the finding as unverified: nobody has yet tested whether
  Tableau renders a workbook whose own `<preferences>` carries the definitions
  on a machine where the palettes are *not* installed. Until that is measured,
  install them (`03-color-palettes.md`) and do not assume either way.
- **Python 3.10+** (the script uses `X | None` annotations) and `xmllint`
  (macOS ships it; on Linux it is `libxml2-utils`). `tableauhyperapi` is
  optional and only needed to read values out of a `.hyper` extract.
