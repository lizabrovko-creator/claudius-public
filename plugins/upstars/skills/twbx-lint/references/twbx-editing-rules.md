# Editing Tableau .twbx safely — field-tested rules

Every rule here was learned from a real Tableau Desktop 2026.1 load failure or
crash during production editing of `All Projects _ High Bonus Loaders` (and
later the Alpa / ACE / Rocket Wheels dashboard builds). Follow
them and the file opens; ignore them and you get error codes D2E8DA72,
E2C30A01, 6ECEB354, or a silent crash.

## 1. Package anatomy

`.twbx` = a plain zip: one `.twb` (the XML you edit) at the root, `Data/`
(hyper extracts — **never modify, never re-compress differently, byte-identical
in = byte-identical out**), `Image/` (icons/logo referenced by the twb).
`twbx_tool.py extract` / `pack` handle this correctly.

## 2. Why raw XML at all

Tableau's official Document API (python) only edits datasource connections and
field metadata — it cannot touch styling, zones, fonts, colors, or layout. For
style-guide enforcement the only way is direct XML editing validated against
the official schema (github.com/tableau/tableau-document-schemas, bundled at
`assets/schema/`). Even Tableau states: XSD validation is necessary but not
sufficient — always finish with a real open test (`open-verify`).

## 3. Hard landmines (each one crashed or blocked a real load)

| # | Rule | If violated |
|---|------|-------------|
| 1 | Font attribute in `<format>` is **`font-family`**, never `font-name` | `Error: value 'font-name' not in enumeration` — file refuses to load |
| 2 | Inside a `<datasource>`, ALL `<column>` elements come **before** any `<column-instance>`, which come before `<group>` (full order list is in `twbx_tool.py::DS_CHILD_ORDER`) | `Error(...): element 'column' is not allowed for content model '(repository-location?,connection?,...)'` |
| 3 | Dashboard `<button><toggle-action>` accepts **only** `tabdoc:toggle-button-click-action ...`. A URL command (`tabdoc:load-url`) inside a button **hard-crashes** Tableau: logic-assert `DashboardCommandIds::ToggleButtonClickAction == id` in `ToggleDashboardButtonStrategy.cpp:46` (Error 6ECEB354) | app-level Internal Error |
| 4 | `<action name>` must match the bracketed pattern `[ ... ]` (XSD QualifiedName). Even then, worksheet URL-actions added by hand have failed DOM load (D2E8DA72) — prefer run-level hyperlinks; if you must touch `<actions>`, open-verify immediately | load failure |
| 5 | Quote escaping depends on context: in **element text** (e.g. `<toggle-action>`) a quote is `&quot;`; in **attribute values** that embed a tabdoc command (e.g. `hyperlink='tabdoc:load-url url=...'`) the workbook uses double-escaped `&amp;quot;`. Copy the escaping from a working sibling in the *same position* | `Command parse error: missing value after =` (E2C30A01) |
| 6 | Every `Image/...` string referenced in the twb must exist as a file in the package. Tableau tolerates a missing icon at load but the button/image is broken — treat as lint FAIL | broken UI element |
| 7 | Zone `id`s are unsigned ints, unique per dashboard; `<zone-style>` is the **last** child of its zone; `type-v2` values come from the schema enum (`text`, `bitmap`, `dashboard-object`, `layout-flow`, `layout-basic`, `filter`, `paramctrl`, `color`, `empty`, ...) | load failure / zones vanish |
| 8 | Clickable **link** that works = a text `<run auto-url='true' hyperlink='tabdoc:load-url url=&amp;quot;URL&amp;quot;'>label</run>`; a clickable **image icon** = zone attribute `url='URL'` (safe, ≠ button); static image = `type-v2='bitmap'` with `param='Image/x.svg'`. A URL-in-button still crashes (row 3, 6ECEB354). A **Show/Hide toggle is NOT inherently impossible** — the historical D2E8DA72 on hand-authored toggles is explained by a missing manifest capability, see §4 "A working Info toggle button" for the ground-truth shape | app Internal Error / D2E8DA72 |
| 9 | A worksheet placed on a dashboard (a `<zone name='Sheet'>`) must ALSO be registered in the dashboard window's `<viewpoints>`: `<viewpoint name='Sheet'/>`. **`validate` checks this statically** (invariant 9) — no need to spend a Tableau launch on it | Re-confirmed by experiment 2026-08-06: `open-workbook rk=early-termination` plus `logic-assert m_windowDoc->HasVisualDoc(doc->GetLocator())` (`DashboardController_VisualControllers.cpp:357`); the file does not open |
| 9b | **`corner-radius` (and its four per-corner members) in a `<zone-style>`** — XSD-valid, `validate`-clean, and Tableau still refuses the file. Bisected 2026-08-20 to this single attribute; plain `corner-radius='16'` alone is enough to trigger it. Radius is **UI-only** — see checklist §C | D2E8DA72 at DOM load, no `Error(line,col)` recoverable from the log |
| 10 | ~~A worksheet with no field on a shelf builds no visual doc → same crash~~ — **falsified, do not enforce.** `All Projects _ High Bonus Loaders` loads `rk=ok` while two of its dashboard sheets have empty `<rows/><cols/>`: `risk zone` (fields only in `<encodings>`) and `Update time` (no field at all — just `<view/>` + `<mark>`), and the latter is a checklist-required block. Empty shelves are not a sufficient condition; row 9 is the one that really crashes | nothing — a valid workbook looks like this |

## 4. Cheap facts that save research time

- `fontalignment` on `<run>`: `0`=left, `1`=center, `2`=right.
- "Fit → Entire View" lives NOT in the worksheet but in
  `<windows><window class='dashboard'><viewpoints><viewpoint name='SHEET'><zoom type='entire-view'/>`.
  Valid types: `percent`, `entire-view`, `fit-width`, `fit-height`.
- Workbook locale: `<workbook locale='en_GB' ...>` attribute.
- Parameter title styling has no worksheet: add to the **dashboard**
  `<style>` block: `style-rule element='parameter-ctrl'` and
  `'parameter-ctrl-title'` (both are valid StyleElement enum members).
- Worksheet-level text styling: `style-rule` elements `axis`, `cell`,
  `header`, `label`, `datalabel`, `quick-filter`, `legend` with formats
  `color` / `font-family` / `font-size`; borders via `border-color` on
  `cell`/`header`/`pane`.
- Tooltip text = `<run>`s inside `<customized-tooltip>`; attributes
  `fontcolor`, `fontname`, `fontsize`, `bold`.
- style-rule ordering inside worksheet `<style>` follows the element order
  Tableau itself writes (axis, cell, datalabel, header, label, mark, pane,
  quick-filter, table, worksheet) — keep new rules in that order.
- Known-harmless XSD complaints (present on pristine Tableau-saved files,
  auto-whitelisted by `twbx_tool.py validate`): workbook "Missing child
  element(s) ... thumbnails/external/…" and extract `_.fcp.*` attributes.
- A calculated field lives in the datasource `<column>` list (order rule #2!)
  and must be re-declared inside each consuming worksheet's
  `<datasource-dependencies>`.
- A field's **displayed name** (dashboard filter title, viz row/column header)
  comes from the `<column caption='…'>` in the **main `<datasource>`** column
  list — NOT the copies inside worksheet/dashboard `<datasource-dependencies>`.
  A plain field with no original caption has **no** main-DS `<column>` at all,
  so captioning only the deps copies changes nothing on screen; add a captioned
  `<column>` to the main datasource (before the first `<column-instance>`,
  rule #2). Sanity check: a field that renders right has its caption once more
  than a broken one (the extra 6-space main-DS line). Shared-view copies don't
  count either — only the main `<datasource>` block; this is the #1 reason a
  re-styled **filter/parameter title "didn't take".** Each dashboard's filter
  uses its own datasource — caption the field in *that* one.
- Clickable **image icon** = zone attribute `url='URL'`; **tooltip** on any zone
  = `tip='…'`. Both are safe — not the crashing button mechanism (rule #8).
- A **floating** dashboard object = an absolutely-positioned `<zone>` that is a
  normal child of the layout-basic root, placed **after** the content zones
  (later document order = higher z-order = on top). There is no `floating`
  attribute; `hidden='true'` starts it collapsed.
- A **dynamic title field-token** (e.g. `<Data Update Time>`) is **UI-only** —
  raw XML has no representation that resolves; an escaped literal shows as text.
- **Read values out of the extract** (e.g. the max date for a "Data as of"):
  `pip install --user tableauhyperapi`, then
  `SELECT MAX("col") FROM "Extract"."<internal-table>"` (list tables via the
  connection catalog first — two-table extracts are common).
- **Counting dashboards/worksheets:** `grep "<dashboard name="` returns 0 even
  when dashboards exist — the real tag carries an attribute first
  (`<dashboard enable-sort-zone-taborder='true' name='…'>`). Count with
  `grep -c "<dashboard "` or the `<window class='dashboard'>` entries. A
  workbook can be **dashboard-less** (worksheets only) → all dashboard-only
  rules (header, filter panel, container backgrounds, viewpoints) are N/A.
- **`fontname` vs `font-family`:** a `<run>` (titles, tooltips, dashboard text
  zones) uses `fontname`/`fontcolor`/`fontsize`; a worksheet `<format>` inside a
  style-rule uses `font-family`/`color`/`font-size`. Landmine #1 (font-family,
  never font-name) is about `<format>` only — runs correctly use `fontname`.
- **Styling a title-less worksheet:** a sheet with no `<layout-options>` shows
  its name in the default font. To give it a Book·12·bold·`#333333` title,
  insert `<layout-options><title><formatted-text><run …/></formatted-text>`
  `</title></layout-options>` right after `<worksheet name='…'>` and **before**
  `<repository-location>` (worksheet child order).
- **Zone attributes are written alphabetically** by Tableau (fixed-size, h, id,
  is-fixed, param, tip, type-v2, url, w, x, y). Match that order in hand-authored
  zones — cheap insurance and clean diffs.
- **A working Info toggle button** — recorded from Tableau's own save, so this is
  ground truth rather than a guess. Three parts must all be present:
  1. **Declare the capabilities** in `<document-format-change-manifest>`:
     `<BasicButtonObject />`, `<CollapsiblePane />`, `<ZoneVisibilityControl />`.
     A UI-built button adds exactly these. Their absence is the most likely cause
     of the historical D2E8DA72 DOM-load failure on hand-authored toggles — the
     same undeclared-feature pattern as DZV.
  2. **The button zone** — `type-v2='dashboard-object'`, `<button>` as the FIRST
     child, `<zone-style>` last:
     ```
     <zone fixed-size='42' h='7500' id='219' is-fixed='true' type-v2='dashboard-object' w='4167' x='65166' y='0'>
       <button action='' active-visual-state-index='1'>
         <toggle-action>tabdoc:toggle-button-click-action window-id=&quot;{DASHBOARD-WINDOW-UUID}&quot; zone-id=&quot;219&quot; zone-ids=[214]</toggle-action>
         <button-visual-state><image-path>Image/2.1 Close Info.svg</image-path></button-visual-state>
         <button-visual-state><image-path>Image/2 Info.svg</image-path></button-visual-state>
       </button>
       <zone-style><format attr='margin' value='4' /></zone-style>
     </zone>
     ```
     `window-id` is the **dashboard window's** `<simple-id uuid>` (from
     `<windows><window class='dashboard'>`) — *not* the `<dashboard>`'s own
     simple-id. `zone-id` is the button's own id; `zone-ids=[N]` lists what it
     toggles. Quotes in this element text are `&quot;` (landmine #5). Visual
     states are ordered close-image first, open-image second, and
     `active-visual-state-index='1'` means the popover starts hidden.
  3. **The target popover** — a floating `param='vert' type-v2='layout-flow'`
     zone at the dashboard-root level placed **after** the content zones (later
     document order = on top), carrying **`hidden-by-user='true'`** — and every
     descendant zone carries it too. This is the collapse mechanism; it is
     `hidden-by-user`, not `hidden`.
  Not yet verified by us: whether hand-authoring all three from scratch loads.
  The manifest hypothesis has precedent but was never open-verified — build it,
  then `open-verify` immediately.
- **Legend "Arrange Items"** = attribute `leg-item-layout` on the legend zone
  (`type-v2='color'`). Confirmed value: **`horz`** = *Single Row*. Tableau also
  re-flows the zone on save (h/y recomputed) and mirrors the attribute into the
  Phone device-layout copy.
- **Filter "Show Apply Button"** = `show-apply='true'` on the filter **zone**
  (`type-v2='filter'`), written between `param=` and `type-v2=`. It is NOT on the
  worksheet `<card>` — the card mirrors `mode=` only, so a card-side edit is a
  silent no-op. Ground truth 2026-08-21, established by the procedure below: the
  analyst ticked it on one filter in the UI, saved, and the attribute was read
  off that save and propagated to the rest. The same save also measured what a UI
  round trip costs: only cached `h`/`y` are recomputed and `padding-*` reordered —
  zone structure, captions, palettes and style-rules survived untouched.
- **Learning an undocumented UI setting.** `<zone>` and `<card>` both carry
  `<xs:anyAttribute>`, so an invented attribute name passes XSD *and* `validate`
  while doing nothing — a silent no-op you would then wrongly report as fixed.
  When the schema has no member for a setting and no bundled workbook contains
  it, don't guess: have the analyst apply it once in the Tableau UI, save, then
  diff that zone against your build to read the real attribute off Tableau's own
  output. That is how `leg-item-layout` above was established.
- **A UI save prunes unreferenced `<preferences>` palettes.** A `<color-palette>`
  block that the workbook doesn't use *by name* (e.g. colours assigned per member
  through `<map to='…'>`) is dropped when Tableau re-saves. Don't treat its
  absence after a UI round-trip as a regression, and don't keep re-adding it.
- **Building the header** (title + Slack + Info + logo on `#01001F`): follow
  `header-recipe.md` — it assembles the safe primitives above and resolves the
  guide's crashing "Info toggle popover" (ship Info as a `tip=` tooltip icon).

## 4b. Edit-pass traps (each one shipped a silently wrong file)

These are not load crashes — the file opens, XSD passes, `validate` passed at
the time. They are ways an edit pass destroys or misses content while every
gate says OK. `pack` now refuses on element loss (`--allow-loss` to override),
which catches the first one mechanically; the rest still need care.

- **Rebuilding a `<style>` block must preserve children you do not recognise.**
  A pass that re-emitted only `<format/>` children deleted a worksheet's
  `<style-rule element='mark'><encoding attr='color' … palette=…>` (the whole
  colour palette of that viz) and the nested `<formatted-text>` inside three
  `<format attr='title'>` filter captions. Both are legal children of a
  style-rule; neither is a `<format/>`. Rebuild by **splicing into the existing
  block** (insert your formats after the opening tag) rather than regenerating
  it from a parsed model.
- **A worksheet can carry an empty self-closing `<style />`.** Regex for
  `<style>…</style>` misses it, so an "insert if absent" pass adds a *second*
  block and the file fails XSD with `Element 'style': This element is not
  expected. Expected is ( panes )`. Match `<style( />|>.*?</style>)`.
- **Trailing spaces in a `caption=` are deliberate.** `Project ` vs `Project`,
  `User id ` vs `User id`, `Contact datetime ` vs `Contact datetime` — the
  analyst duplicated a field and disambiguated the copy with a space. Trimming
  merges the two names in every field list. Change the case, never the spaces.
- **A filter title lives in two places at once.** `<format attr='title'
  value='X'>` may carry a nested `<formatted-text><run>X</run>`; editing only
  the attribute leaves the rendered text unchanged. Rewrite both.
- **A UI colour edit can re-emit a legend as a NEW zone and lose its
  placement.** Observed 2026-08-12: after assigning a palette to `Awols graph`
  in Tableau, the legend zone that had been placed under its viz was dropped and
  recreated with a fresh id as a sibling *outside* that container — silently
  undoing checklist C's "legends go under their viz". Any UI round trip
  therefore invalidates zone placement: re-run `validate` **after** the analyst
  saves, never only before.

## 5. Diagnosing a failed load (deterministic, low-token)

Tableau log: `~/Documents/My Tableau Repository/Logs/log.txt` (JSON lines).
`twbx_tool.py open-verify` automates this — including the trap that Tableau
**rotates** log.txt → log_bk.txt on every app start, which invalidates any
byte offset recorded before the launch (reset to 0 when the inode changes or
the file shrinks). Manually: launch, then read the log and grep for:
- success: line with `end-workspace.open-workbook` **and** `"rk":"ok"`
- failure: `logic-assert` (crash + C++ stack, read `condition`) or
  `show-detailed-error-dialog` (read `error-short-message`)
- `Error(LINE,COL)` codes in dialogs map to line numbers in the .twb.
Ignore noise errors: EventsConfigurator, connector-plugin-error/libsalesforce,
qtwebengine locale, BentonSans font, "Post spans request".

**Log topology — this was the real cause of "INCONCLUSIVE often".** Tableau keeps
**one numbered log per concurrent instance** (`log.txt`, `log_1.txt` …
`log_5.txt`), each rotated to `*_bk.txt` on start. Measured 2026-08-06: opening a
file while an instance was already running put only the `FileOpen event` line in
`log.txt`, while the instance that actually loaded the workbook wrote `rk=ok`
into **`log_5.txt`**. A watcher reading only `log.txt` therefore misses most
verdicts — `open-verify` now reads every `log*.txt` (skipping `*_bk`), tracking
inode + offset per file, and both verdicts came back in seconds afterwards.

Three more facts from the same experiment:
- **`logic-assert` on its own is NOT a failure.** A healthy start emits ~14 of
  them (`condition:"wbc"` in `Parameters.cpp:884` / `ContextParameters.cpp:47`)
  and then loads fine. The verdict is the `rk` of `end-workspace.open-workbook`
  (`ok` vs `early-termination`); asserts are evidence to attach to a bad verdict,
  nothing more. Crash lines carry **no `ctx.wb` at all**, so they can never be
  filtered by file name — attribute them by `pid`.
- **`Processing FileOpen event … File:<path>`** proves Tableau received your exact
  file; it separates "never got it" from "got it and wrote no verdict".
- **`.~<basename>__<pid>.twbr`** appears beside a workbook Tableau has open — an
  independent answer to "did it open?" when no verdict is logged, and the cheapest
  way to tell that a result is currently open in Tableau.

**Resolving an INCONCLUSIVE: re-test the identical bytes at a fresh path.**
Repeatedly opening and `kill -TERM`ing the same path poisons later runs.
Measured 2026-08-20 on one byte-identical artifact: `OK` (verdict elapsed
15.9 s) → then `INCONCLUSIVE` twice after kill/relaunch cycles on that path →
then `OK` again immediately, from a plain `cp` to a new filename. So an
INCONCLUSIVE that follows a kill is about the path, not the workbook. Copy the
packed file to a new name and re-run; `OK` there clears the artifact, and a
second INCONCLUSIVE genuinely implicates it.
Two traps worth stating explicitly, because both wasted a turn here:
- **`end-central-widget.on-view-activated` and
  `end-workspace.setup-sheet-tabs.set-active-sheet-widget` do NOT prove a
  successful load.** They look like proof — view activated, sheet tab set, zero
  error dialogs — but the `element='tooltip'` hang reaches exactly those keys and
  *then* goes quiet, which is the same signature. They only rule out the
  D2E8DA72 shape (which has `show-detailed-error-dialog` ≥ 1 and never activates
  a view). Do not promote them to a success signal.
- The controls that do discriminate stay `.twbr` **plus**
  `end-workspace.open-workbook`. On the `OK` runs both were present; on the
  INCONCLUSIVE runs neither was. A sleeping process at ~0 % CPU does not settle
  it either — the hang sleeps too.
Whatever the evidence, never print `OPEN-VERIFY: OK` yourself: the report quotes
that line verbatim from the tool, so if you could not obtain it, say
INCONCLUSIVE and what you did about it.

**On D2E8DA72 you usually cannot read the cause from the log — bisect instead.**

**On D2E8DA72 you usually cannot read the cause from the log — bisect instead.**
The `Error(line,col)` detail lives in a `detailed-error-msg` line that Tableau
writes only when the error dialog is **dismissed by a human**; `kill -TERM` on
the instance does not flush it (measured 2026-08-20 — the 2026-08-03 precedent
in this file shows the same 7-minute gap between the dialog opening and the
detail line, which is simply when someone clicked it). So do not burn turns
grepping for a detail that is not there. Bisect with `open-verify`, which is
cheap because a *failing* load verdicts in ~2 s while a good one takes ~30-60 s:

1. Confirm the **pristine clone** opens `rk=ok` first. If it does not, the defect
   is pre-existing and that changes the whole job. (Missing `Image/` files do
   **not** break the load — landmine #6 — so a missing icon is not your suspect.)
2. Split the edit passes into cumulative halves, re-`extract`/re-apply/re-`pack`
   each time, and keep every pass in its own script so the chain is replayable.
   Seven runs isolated one attribute out of ~50 edits.
3. Suspect first anything that is *schema-valid but never observed in a
   Tableau-written file* — that is the exact profile of a silent DOM-load
   killer (`corner-radius` here, `element='tooltip'` before it).

Still true: instances pile up when you re-`pack` and re-open the same path — pick
the **newest by start time** (`ps -Ao pid,lstart,command | grep -a Tableau`) and
confirm the verdict's `ts` is **after your last `pack`**, else you may read a
stale instance still holding the pre-edit version.

**BigQuery-connected workbooks may stall on the FIRST open** (live-connection
OAuth): the DOM loads clean and the extract serves the data, and it opens
`rk:"ok"` once the connection is warm. `qp.run-query` `early-termination`s on
open are just the unauthenticated live queries — harmless.

## 6. Editing discipline

1. Work only on the clone in `results/` (never `dummy/` — a PreToolUse hook
   enforces this).
2. Prefer exact-string `Edit` operations on the extracted `.twb`; scripted
   bulk replaces (python) for repetitive changes or multi-line inserts. **Guard
   scripted passes with exact `.count()` assertions** (expected N; abort on
   mismatch) so a wrong anchor fails loudly instead of silently mangling.
3. After packing, **re-extract the packaged artifact and validate it again**
   (round-trip) — this catches wrong-file/stale-zip mistakes.
4. Never claim done without `validate` PASS **and** `open-verify` OK.
5. **Cheap XSD check before packing** (invaluable on 100 MB+ packages where
   `pack`+`validate` is slow): `xmllint --noout --schema
   assets/schema/twb_2026.2.0.xsd "<twb>"` on the edited `.twb` — it catches
   column-order (rule #2) and structural breakage in seconds. Ignore the one
   known-harmless line `Element 'workbook': Missing child element(s) …
   thumbnails/external` (present on pristine Tableau-saved files).
