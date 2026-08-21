# Upstars style lint checklist (operational)

Source of truth: the bundled guide in `style-guide/` next to this file
(01-structure, 02-typography, 03-palettes, 04-filters, 05-tooltips,
99-checklist). This file compresses it into **checkable, fixable rules**, and
records where the analyst's explicit decisions override the written guide —
those overrides win. Fix what the file violates; report anything you can't
fix mechanically.

## A. Typography (analyst-confirmed final rules)

| Element | Rule | Where in XML |
|---|---|---|
| ALL viz text: axes, table cells, headers, labels, data labels | Tableau Book · 9px · `#333333` | worksheet `<style>` → style-rule `axis/cell/header/label/datalabel`: formats `color`, `font-family`, `font-size` |
| Filter titles | same 9/TB/#333333 | style-rule `quick-filter` |
| Parameter titles | same 9/TB/#333333 | **dashboard** `<style>` → `parameter-ctrl` + `parameter-ctrl-title` |
| Tooltips | same 9/TB/#333333 (analyst override of guide's 10px) | `<customized-tooltip>` runs: `fontcolor='#333333' fontname='Tableau Book' fontsize='9'` |
| Viz / chart titles + KPI text-zone titles | Tableau Book · 12px · **bold** · `#333333` · **left-aligned** (`fontalignment='0'`) | worksheet `layout-options/title` runs; dashboard text zones |
| Base / default body text | Tableau Book · 9px · `#333333` | worksheet `<style>` formats; dashboard text zones |
| Dashboard title (header) | Tableau **Bold** family · 20px · `#ffffff` — do not touch header styling. The family carries the bold, so never add `bold='true'` on top of it | header text zone |
| "Data Update Time …" block | 9px `#333333` right-aligned | Update-time worksheet title runs |
| Calc / field / filter / parameter captions | Words ≥3 letters Title-Cased; keep metric acronyms as-is (NGR/GGR/NGR1/NGR2/ROI/ROMI/RFD/RD/LD/ARPU/ARPPU/RTP/AR/HBL/IN…); underscores in a raw DB name become spaces (`user_pseudo_id` → `User Pseudo ID`, analyst-confirmed 2026-08-20) | `caption='…'` on the field's **main-datasource** `<column>` (see twbx-editing-rules §4 — a plain filter/param field often has none, so add one) |

⚠️ **The caption rule is violated hardest where there is no caption**, so build
the work-list from the sheets and never from `validate`'s caption findings.
`validate` invariant 27 reads `cap = col.get("caption"); if cap and …` — a
column with no caption is skipped, and a field with **no main-DS `<column>` at
all** is never even enumerated. That second case is the common one: a field the
analyst never re-captioned has no main-DS `<column>`, so the crosstab header
renders the **raw BigQuery name** (`user_id`, `sub_id1`, `user_pseudo_id`) — the
loudest possible violation, at zero findings. Measured 2026-08-20: 9 of the 11
row fields on a `RAW data` crosstab were raw names after a run that reported
"146/150 fixed".
Procedure: for each worksheet, read `<rows>`/`<cols>`, resolve every
`[federated…].[…]` reference through the main DS `column-instance` → `column`
chain, and list the effective display name. `None` is a finding. Fix by adding a
captioned `<column>` to the main datasource (child-order landmine #2) and
mirroring the caption into the `<datasource-dependencies>` copies, which is what
Tableau itself writes. Before renaming, check the new caption does not collide
with an existing field — this workbook family disambiguates duplicates with a
**trailing space** (`Deposits` / `Deposits `), so reuse that convention rather
than inventing a new name.

## B. Color

- **Semantic Color Mapping wins over hue-matching** (guide p15). If a field
  is `Project`, `VIP Status` or `Provider`, its colors are *prescribed per
  member* — never pick "the nearest token" for them. Full tables are in
  `style-guide/03-color-palettes.md § Semantic Color Mapping`. Projects
  (UPSTARS **Alternative**): `alpa #8794D5` · `thor #EDC948` · `vegas #59CD90` ·
  `king #FF9D85` · `bond #6EC3D8` · `felix #DF90D8`. A member absent from the
  table (e.g. `zeus`) gets **no** invented color — leave whatever valid Upstars
  token it already has and report it.
- Off-palette colors → nearest Upstars token. Known offenders and fixes:
  `#0433ff`→`#005DE8`, `#757575`→`#333333` (viz text) , `#666666` only for
  on-dashboard comments/action descriptions per guide.
- **An undeclared palette is a finding, not a pass — and it is invisible to
  grep.** A `<color column='…' />` inside `<encodings>` says only *which field*
  drives colour. The palette itself lives somewhere else entirely: a
  `<style-rule element='mark'><encoding attr='color' … palette='…'>` (or a
  `type='palette'` encoding carrying `<map to='#hex'>` per member), in the
  worksheet's or the **datasource's** `<style>` block. When that declaration is
  missing, Tableau paints the viz in **its own default palette** and writes **no
  hex into the twb at all** — so a hex census and a `palette=` sweep both come
  back clean while the chart on screen is Tableau blue/orange. This is
  absence-shaped, so it belongs to SKILL.md's presence sweep, not to a grep for
  wrong values.
  ⚠️ **Tableau's own default diverging palette IS `orange_blue_diverging_10_0`.**
  On a workbook that already names it, a working edit and a dead one render
  *identically* — so this rule can never be judged by eye on an orange/blue viz.
  **The declaration has three different shapes, not one** — transcribed from
  Tableau's own save (ground truth 2026-08-12, established by the §4
  "learning an undocumented UI setting" procedure). Do not collapse them:

  | Colour driven by | Declaration lives in | `field=` | Form |
  |---|---|---|---|
  | a categorical **dimension** | the **`<datasource>`**'s `<style>` | **unprefixed** — `[none:employee_name:nk]` | `palette='…' type='palette'` **plus one `<map to='#hex'><bucket>"member"</bucket></map>` per member** |
  | a continuous **measure** | the **worksheet**'s `<style>` | **prefixed** — `[ds].[usr:X:qk]` | self-closing `palette='…' type='interpolated'`, no maps |
  | `[Multiple Values]` with `separate-domains='true'` | the **worksheet**'s `<style>` | **one entry per measure**, prefixed | as the continuous row |

  Two dead forms that look right and do nothing — both cost a full round trip
  to discover, so check for them explicitly:
  - `palette='…'` on a **categorical** field with **no `<map>` children**.
    Tableau materialises the per-member assignment; the bare attribute alone is
    ignored and the viz stays on defaults.
  - a single entry on **`[Multiple Values]`** when the binding carries
    `separate-domains='true'`. With separate legends only the per-measure
    entries render; the combined one is decoration. (A `total`-style crosstab
    had 12 measures → 12 entries.)

  Fix with the **purple default** (analyst-confirmed 2026-08-12) — no per-case
  decision, pick the row by what colour is driven by:
  | Colour driven by | Palette (`palette='…'`) | Colors |
  |---|---|---|
  | a categorical **dimension** | `UPSTARS Purple-Grey` | `#210E5F` `#5535BE` `#928EEC` `#D9D8FF` `#CECED6` `#A5A5AC` `#81818E` |
  | a continuous **measure** | `S1 Purple-Grey` | `#F3F3F3` → `#928EEC` |
  | a continuous **signed** measure (delta, ±) | `D7 Upstars Purple` | `#76E0E7` → `#8576E4` → `#CA76E7` |
  The palette must also exist in the workbook `<preferences>` as
  `<color-palette custom='true' name='…' type='regular|ordered-sequential|ordered-diverging'>`
  with **lowercase** hexes — that is the shape Tableau writes — and the name must
  match `assets/design-materials/Preferences.tps` character for character,
  because the encoding resolves it **by name**.
  This default **never overrides** two things: a `Project`/`VIP Status`/
  `Provider` field (semantic mapping wins — see the first bullet), and an
  encoding that already names a valid Upstars palette. It fills the gap where
  nothing at all is declared.
  ⚠️ A high-cardinality dimension (hundreds of members — e.g. colour by
  operator) will cycle those 7 colors many times over. That is expected and is
  **not** a reason to skip the rule: apply the palette, and note the cardinality
  in the report so the analyst can decide whether colour is the right encoding
  at all.
  ⚠️ **But never cycle blindly — check the collision per viz.** The `<map>` list
  is datasource-wide while a legend is per-viz, so what matters is whether two
  members that appear in the **same** viz got the same hex. Assigning the palette
  in document order and letting it wrap is what produces that bug: measured
  2026-08-20, a naive 7-colour cycle over 9 `[:Measure Names]` members gave
  `Daily Conversions dynamic` two identical series out of three, and every gate
  stayed green because each hex was individually on-palette.
  The same structure is also the way out: group the members by the viz that
  shows them (read each sheet's `groupfilter function='member'
  level='[:Measure Names]'` entries). Sets that are **disjoint across vizzes**
  can each restart at the top of the palette, so three 3-member charts all get
  the same clean dark→light ramp and nothing collides. Verify by listing, for
  each colour-encoded sheet, the hex per displayed member and asserting they are
  distinct — that check is cheap and it is the only thing that proves the fix.
  Members that the live calculation can no longer emit (buckets left behind by
  an edited formula) can safely share one grey; say so in the report rather than
  spending real palette slots on them.
  **Choosing a palette is never a question for the analyst** (analyst-confirmed
  2026-08-12): take any palette from the Upstars set that matches the encoding
  type, and **when in doubt take the purple one** — `UPSTARS Purple-Grey`,
  `S1 Purple-Grey`, `D7 Upstars Purple`. Stopping the run to ask which colour to
  use is a wrong answer; shipping Tableau defaults because the choice felt
  ambiguous is a worse one.
- Risk/RAG semantics: bad `#D04747` · normal `#E0A030` ·
  good `#3FB587`; light set (RAG #2) `#FFA2A2` · `#FFDE8B` · `#9CE8CC`.
  ⚠️ Seeing v1's `#FFB804`/`#00CE84`/`#6EEDBF` **in a RAG role** is now a
  finding (`#FFB804` is still legitimate elsewhere — see the membership table
  below; `#00CE84` and `#6EEDBF` are gone everywhere).
  A sequential palette on a categorical risk field is a bug —
  but a diverging palette on a **continuous** measure (e.g. a signed Delta,
  −red…+green) is correct, not a bug.
- **Accessibility** (guide p18): red-green is unreadable for deuteranopia.
  For *critical* statuses either double-code with an icon or switch to
  **D5 Red-White-Blue**. Flag a red/green-only critical status as a finding.
- Palettes must come from the Upstars set — **v2 inventory**: Main/Light/Alt +
  Purple-Grey/Blue-Grey, **S1–S8**, **D1–D7**, RAG#1/#2/Alt.
  `assets/design-materials/Preferences.tps` has all definitions;
  custom palettes used by the workbook live in `<preferences>` of the twb.
  Migrating a workbook built against the old palettes — a hex counts as
  off-palette only relative to the palette it is used *from*:
  | Palette | v1 | v2 |
  |---|---|---|
  | Main pos.5 / pos.6 | `#FFB804` / `#00CE84` | `#C2660A` / `#0E9FBF` |
  | Light pos.4 / pos.8 | `#6EEDBF` / `#FFDE8B` | `#6EEDD4` / `#F5CE9E` |
  | Alternative pos.5 (+1 new) | `#7D84B2` | `#6EC3D8`, plus `#DF90D8` (6→7 colors) |
  | RAG #1 normal / good | `#FFB804` / `#00CE84` | `#E0A030` / `#3FB587` |
  Still valid elsewhere: `#FFB804` (S4 Amber end, D1/D2 left shoulder),
  `#FFDE8B` (RAG #2 normal). Gone entirely: `#00CE84` (→ `#3FB587` in Main,
  D3, D4, RAG#1), `#6EEDBF`, `#7D84B2`, and the dropped diverging palettes
  (v1 `D5` Light Red-White-Green, `D6` Light Red-White-Blue, `D9 Upstars Blue`).
- Borders/gridlines on **visible** vizzes: `#f5f5f5` (`border-color` on
  worksheet `cell`/`header`/`pane` style-rules). Do **not** rewrite a
  `border-color` inside a dashboard `<zone-style>` that sits next to
  `border-style='none'`/`border-width='0'` — the border is off, so that value is
  Tableau's dormant default and changing its colour is invisible no-op churn.

## C. Layout & canvas

- Canvas `<size>`: fixed; width 1200–1600 (clamp 1700→1600); height fixed
  800/850 for one-screen, content-height for longreads is acceptable.
- Container backgrounds: **none** (remove `background-color`) on all layout
  containers AND sheet zones — including the chart/table card zones that
  carry `#f5f5f5` (e.g. "Dynamic by month", "risk zone", "stats by users").
  Two intentional exceptions: the header keeps `#01001f`, and the **filter
  container is painted `#f5f5f5`** (see the filter-panel rule below).
  Post-check that catches stragglers:
  `grep -c "background-color' value='#f5f5f5'" <twb>` must equal **the number
  of filter containers** (1 on a single-dashboard workbook, 0 if the workbook
  has no filter panel) — every extra hit is a card zone still to strip
  (eval evidence: a run that skipped this check left 3 of 12 behind).
- Zone spacing model (analyst-confirmed): sheet zones `margin=4` all sides +
  `padding=0`; containers `margin=0` + inner `padding-left/right/top/bottom=10`
  only on sides adjacent to a sibling container (first KPI: right only; middle
  KPIs: left+right; last: left; KPI row: bottom; chart block: top+bottom).
- Filter panel (analyst-confirmed): a **separate container outside the body** —
  per the guide's hierarchy `Outer Horizontal → [ Header+Body (vert), Filters ]`,
  so the panel runs the **full canvas height** beside the header, never nested
  inside the body. Width 200px, inner padding 10, and its container background
  **is painted `#f5f5f5`** (this is the one intentional `#f5f5f5` background —
  see the container-background rule above, which targets viz/card zones).
  `FILTERS` caption 10px bold `#333333`.
- **Legends go under their viz** (analyst-confirmed), never in the filter panel:
  make the viz's container a vertical `layout-flow` and add the legend zone as
  its last child with `fixed-size` (~60px) + `is-fixed='true'`. A legend keeps
  its `name=` and `pane-specification-id=`, so moving the zone does not rebind it.
  Arrange its items in a **single row** — `leg-item-layout='horz'` on the legend
  zone — so it reads as a strip under the chart rather than a tall column.
- **Header content takes no inner padding** (analyst-confirmed): every child of
  the header zone (title text, icon bitmaps) gets **outer padding 4** —
  `<format attr='margin' value='4' />` — and no `padding*` format. The header
  container itself keeps `padding-left/right=10` + `background-color`.
- **Icon bitmaps in the header: no Fit/Center Image.** Do not set `is-scaled`
  (Fit Image) or `is-centered` (Center Image) on the Slack and Info icons — they
  are already sized by `fixed-size`. The logo may keep `is-scaled='1'`.
- **Corner radius (guide p7).** Tableau's Layout → Corner Radius is used for
  exactly three things: **KPI zones**, the **block under the Info button**
  (rounded on 3 corners — *not* the top-right), and **vizzes on a
  colored-background dashboard**. Default trio for a colored-background
  dashboard: `Corner Radius 16` · `Outer Padding 8` · `Inner Padding 8`.
  That 8/8 pair conflicts with the analyst-confirmed spacing model above; per
  this file's preamble the analyst's decision wins, so **report** the difference
  on a colored-background dashboard rather than silently re-spacing it. A plain
  white-background dashboard is unaffected.
  ⛔ **Radius is NOT editable from raw XML — this is a report-only item.**
  `StyleAttribute-ST` does carry `corner-radius` and the four per-corner members
  (`corner-radius-top-left/-top-right/-bottom-right/-bottom-left`), so a
  `<format attr='corner-radius' value='16' />` inside a `<zone-style>` passes
  the XSD **and** `validate` — and then Tableau Desktop 2026.1 refuses the
  workbook with **D2E8DA72** at DOM load. Measured 2026-08-20 on
  `Vegas Remarketing monitoring board [gyro 635]`, bisected to this single
  attribute: plain `corner-radius='16'` alone fails, so it is not just the
  per-corner members. An earlier version of this file claimed the opposite;
  it was wrong, and the claim cost a run seven `open-verify` cycles.
  Treat radius like the `<Data Update Time>` title token — **UI-only**: report
  it, and tell the analyst to set Layout → Corner Radius in Tableau. If you
  ever need the real XML shape, have them set it once in the UI and save, then
  read it off Tableau's own output (twbx-editing-rules §4, "learning an
  undocumented UI setting"). Do not re-derive it from the schema enum.
- Delete leftover template placeholders. v1 wording: "Place filters in the
  container and after that - remove this object". The **v2 template** ships
  different ones: `Replace this object by Chart N`, `Update or Remove Chart N
  Title`, `Unknown Update Time UTC`.

## D. Behavior / misc

- **Fit stays `Standard` on every viz, no exceptions by chart type**
  (analyst-confirmed 2026-08-12 — this *replaces* the former "force
  `<zoom type='entire-view'/>` on every dashboard viewpoint" rule; do not
  reintroduce it). `Standard` is the **absence** of a `<zoom>` element under the
  `<viewpoint>` — that is what Tableau itself writes, so the fix is to **delete**
  the `<zoom>` line, not to add one. `percent` is the same thing written
  explicitly and is accepted; `entire-view`, `fit-width` and `fit-height` are all
  findings. Enforced by `validate` (invariant "dashboard viz fit = Standard"),
  because a squashed crosstab looks plausible in XML and only shows up on screen.
  Scope: dashboard `<viewpoint>`s. A `<zoom>` inside a **worksheet** window is
  that sheet's own view setting, not a dashboard fit — leave it and report it.
- Workbook locale `en_GB`.
- Header must contain: title, upstars logo, Slack icon (clickable bitmap →
  `analytics-questions-updates` chat, zone width 50px), Info ⓘ icon (50px).
  **Build it with `header-recipe.md`.** Info may be shipped either way: as a real
  **show/hide button** (`type-v2='dashboard-object'` + `<button>` toggling a
  `hidden-by-user='true'` popover — ground-truth XML and the required manifest
  capabilities are in twbx-editing-rules §4), or, when a load failure is
  unacceptable, as a **static bitmap with a `tip=`** tooltip carrying the
  report-period text. Missing packaged icons → copy from
  `assets/design-materials/`.
- **Optional icons**: the ✉ Mail icon and the generic "Details" button are
  retired — flag them if present. The set is **Confluence** (button width **186px**,
  link to a page written from *Template: Standard Report Description*) and
  **Video** (width **56px**, a demo recording of the report), both inside a
  horizontal container **48px** high. ⚠️ `assets/design-materials/` does **not**
  yet ship `Confluence`/`Video` icons (it still has the obsolete
  `5 Mail.svg`) — they are vector art in the PDF, not extractable as clean
  assets, so they must be added from the design-materials source before a
  header can include them.
- Info popover (when built in the Tableau UI): background `#D9D8FF`, inner
  padding 10, and **corner radius 16 on three corners** — square top-right.
  Background and padding are editable from XML; the radius is **not** (§C) —
  report it. Note the background here is a deliberate exception to §C's
  "only two painted containers": `validate` invariant 20b cannot express the
  exception and will flag `#d9d8ff` whenever the popover exists. That is a
  known false positive, not a defect to fix by stripping the colour.
- Update-time worksheet must show a real value: if the title references
  `<Data Update Time>` with no bound field, add a `NOW()` calculated column to
  the main datasource (respect column ordering!) and declare it in the
  worksheet's datasource-dependencies.
- **Every filter is Multiple Values (dropdown) + Show Apply Button —
  no exceptions by member count** (analyst-confirmed 2026-08-21, this
  **overrides** guide 04-filters §6-7, which splits on 2-vs-3+ options).
  In XML: `mode='checkdropdown'` **and** `show-apply='true'` on every
  `type-v2='filter'` zone. A 2-member field is no exception — this was
  fixed on `remarketing_type` (2 members) and `had_remarketing_session`
  (boolean) after a run applied the old 2-vs-3+ split to them.
  ⚠️ Never infer the member count from the saved `<filter>` enumeration:
  it records the *selection*, not the domain, and a live connection can
  hold more members than the ones stored. Local filters ≤180px. The control type is the `mode=`
  attribute on the `type-v2='filter'` zone: `dropdown` = single-value dropdown,
  `checkdropdown` = multi-value dropdown, `radiolist`/`checklist` = the
  single/multi **list** forms the rule is steering away from.
  ⚠️ **A card with no `mode=` at all is a finding, not a default-is-fine.**
  "Multiple Values (List)" is Tableau's own default and it writes **no
  attribute**, so a checkbox-list card is invisible to a `mode=` grep *and* to
  `validate` (invariant 25 only tests `mode in ('radiolist','checklist')`,
  which `None` never matches). Enumerate every filter zone and treat a missing
  `mode` as "list" — measured 2026-08-20, two `remarketing_type` cards sat in
  list mode through a whole run at 0 findings.
  This compounds with the 50px rule below: pinning a *list* card to
  `fixed-size='50'` clips it, so the two rules have to be applied together —
  set `mode='checkdropdown'` first, then the height. A card that looks
  suspiciously tall in the source (82px, 93px) is the tell that it is a list.
- **Every filter card is 50px tall** (analyst-confirmed 2026-08-12): on each
  filter zone (`type-v2='filter'`) set `fixed-size='50'` **and**
  `is-fixed='true'` — `fixed-size` alone does nothing without the pin. Recompute
  the cached `h` to match: `h = round(50 / canvas_height_px * 100000)`. Applies
  to every filter card regardless of control type; a date/relative-date card is
  no exception. Desktop zone tree only — `Phone` device layouts are
  auto-generated and Tableau rebuilds them. Enforced by `validate` (invariant
  "filter card height"). Note: this is the *card* height; the 200px filter
  **panel** width is a separate §C rule, and `paramctrl` zones are not filters
  and keep their own size.

## E. What NOT to do

- Don't touch `Data/*.hyper`, connection details, calculations' formulas,
  filters' selections, or sheet/dashboard names.
- Don't "improve" anything the user didn't ask for beyond this checklist.
- Don't make dashboard buttons clickable-to-URL (see landmine #3 in
  twbx-editing-rules.md).
