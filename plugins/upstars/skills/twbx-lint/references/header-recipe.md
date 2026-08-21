# Building the Upstars header (crash-safe recipe)

The style guide wants a branded header on every dashboard (`style-checklist.md`
§D; `style-guide/02-typography-buttons-header.md`). Hand-building it is risky
for two reasons, and this file is the field-tested way through both:

1. The written guide describes an **"Info ⓘ toggle with popover"**. Hand-authored
   toggles historically hard-failed DOM load, but the cause is now known: the
   `<document-format-change-manifest>` was missing `BasicButtonObject`,
   `CollapsiblePane` and `ZoneVisibilityControl`. `twbx-editing-rules.md` §4
   ("A working Info toggle button") records Tableau's own working XML for the
   button, the `window-id`/`zone-ids` wiring and the `hidden-by-user='true'`
   popover. Two ways to ship it: build the toggle **in the Tableau UI** (always
   safe), or hand-author it from that template and `open-verify` at once. The
   **static icon with a `tip=` tooltip remains the safe fallback** when you must
   not risk a load failure.
2. Layout math is where dashboards break. Model the header on a workbook that
   already loads clean rather than inventing a zone tree.

## The proven shape (from a header that opens `rk:"ok"`)

One **horizontal `layout-flow`** zone, background `#01001F`, with a flexible
title text zone on the left and three fixed-width icon zones on the right. Zone
attributes are written **alphabetically** (Tableau's own order) — match it to
keep diffs and risk minimal:

```
<zone [fixed-size='60' is-fixed='true' only in a vert-flow parent] h='7500' id='NNN' param='horz' type-v2='layout-flow' w='100000' x='0' y='0'>
  <zone h='7500' id='NN1' type-v2='text' w='82143' x='0' y='0'>
    <formatted-text>
      <run fontcolor='#ffffff' fontname='Tableau Bold' fontsize='20'>DASHBOARD TITLE</run>
    </formatted-text>
    <zone-style>
      <format attr='padding-left' value='10' />
      <format attr='padding-top' value='10' />
    </zone-style>
  </zone>
  <zone fixed-size='50' h='7500' id='NN2' is-fixed='true' param='Image/Slack.svg' tip='Open the analytics-questions-updates Slack chat' type-v2='bitmap' url='https://go-upstars.slack.com/archives/C023N3XCQ05' w='3571' x='82143' y='0'>
    <zone-style><format attr='padding' value='8' /></zone-style>
  </zone>
  <zone fixed-size='50' h='7500' id='NN3' is-fixed='true' param='Image/Info.svg' tip='&lt;report period, e.g. data for the last N months&gt;' type-v2='bitmap' w='3571' x='85714' y='0'>
    <zone-style><format attr='padding' value='8' /></zone-style>
  </zone>
  <zone fixed-size='150' h='7500' id='NN4' is-fixed='true' param='Image/Logo.svg' type-v2='bitmap' w='10714' x='89286' y='0'>
    <zone-style><format attr='padding' value='8' /></zone-style>
  </zone>
  <zone-style>
    <format attr='background-color' value='#01001F' />
  </zone-style>
</zone>
```

Parts:
- **Title** — flexible text zone (no `fixed-size`), Tableau **Bold** 20 `#ffffff`,
  text taken from the dashboard name. The attribute is `fontname` (it's a
  `<run>`, not a `<format>` — see `twbx-editing-rules.md` §4), never `font-name`.
- **Slack** — clickable image: `type-v2='bitmap'`, `param='Image/Slack.svg'`,
  `url='<chat>'` (safe: a zone `url`, **not** a `<button>`), plus a `tip=` label.
  Standard chat: `https://go-upstars.slack.com/archives/C023N3XCQ05`.
- **Info** — two supported forms. *Fallback:* static `bitmap` + `tip='<period
  text>'`, no `url`, no toggle — the "report covers …" text lives in the `tip`.
  *Full:* a real show/hide button (`type-v2='dashboard-object'` + `<button>`
  toggling a `hidden-by-user='true'` popover) — shape and the manifest
  capabilities it needs are in `twbx-editing-rules.md` §4. The popover itself
  holds the period text (10px `#333333`, key part bold) and may carry the
  Confluence/Video icons; guide background `#D9D8FF`.
- **Logo** — static `bitmap`, `param='Image/Logo.svg'`, 150-wide.
- `<zone-style>` is the **last** child of every zone (landmine #7).
- Icon `w=` are proportions of a **1400-wide** canvas (50px→3571, 150px→10714).
  Recompute for other widths: `w = round(px / canvas_px * 100000)`; keep the
  four `x=` offsets contiguous (title_w, +3571, +3571, +10714 = 100000).

## Icons: copy into the package
Every `Image/*.svg` referenced must exist in the package (landmine #6). Copy
from `assets/design-materials/` and rename to match `param=`:
`1 Logo.svg → Image/Logo.svg`, `2 Info.svg → Image/Info.svg`,
`3 Slack.svg → Image/Slack.svg`. Create `Image/` in the workdir if absent.

**v2 optional buttons.** The guide's optional set is now **Confluence**
(186px wide) + **Video** (56px), sitting in a horizontal container **48px**
high — the ✉ Mail icon and the generic "Details" button are retired.
`assets/design-materials/` does **not** ship those two icons yet (it still
carries the obsolete `5 Mail.svg`), and in the PDF they are vector art rather
than extractable assets, so a header cannot include them until the real files
are added. Both are plain clickable bitmaps (`type-v2='bitmap'` + `url=`), the
same safe primitive as Slack — never a `<button>` (landmine #3/#8).

## Placement depends on the dashboard's root layout
Read the dashboard's outermost `<zones>` child first:
- **Root is `layout-basic`** (absolute positioning): add the header as an
  absolutely-positioned child at the top (`y='0' h='7500'` ≈ 60px on an
  800-tall canvas) and push the content zone down (`y='7500'`, reduce its `h`
  by 7500). No `fixed-size` needed. Keep the root's own `<zone-style>` last.
- **Root wraps a vertical `layout-flow`** (children stack): insert the header
  as the **first child** of that flow, pinned with `fixed-size='60'
  is-fixed='true'`. If the current first child is a default `type-v2='title'`
  zone, **replace it** — the branded header *is* the title, so keeping both
  duplicates it.

## New zone ids
`id`s are unique **per dashboard** (landmine #7); pick a small block above the
dashboard's current max (e.g. 201-205). The `Phone` device-layout zone trees are
independent and auto-generated — leaving them header-less is fine; Tableau
rebuilds them.

## Two dashboards → two headers
Each dashboard gets its own header titled with its own name; ids are per-
dashboard so the same block (e.g. 201-205) can repeat in each.

## Finish with the two gates
XSD-check the `.twb` (`xmllint`, see `twbx-editing-rules.md` §6), then `pack`
and `open-verify`. `end-workspace.open-workbook` `rk:"ok"` with no `logic-assert`
is the only proof the header loads; the visual layout you still eyeball in the
open window.

## Linting an existing header (do not rebuild it)

**If the workbook already has a header, lint it — do not rebuild it.** A
correctly wired Info **toggle** (`type-v2='dashboard-object'` + `<button>`
toggling a `hidden-by-user='true'` popover) is a legitimate §D form, and
`twbx-editing-rules` §4 records its working shape. Check the wiring before
judging it: the `<toggle-action>` `window-id` must equal the **dashboard
window's** `<simple-id uuid>`, not the `<dashboard>`'s own. Two known
`validate` **false positives** fire whenever that form is present, and both are
expected, not defects to "fix":
- *"header is missing Image/Info.svg"* — invariant 21 only counts `type-v2='bitmap'`
  zones, so a `<button>` never satisfies it, though §D permits either form.
- *"container background #d9d8ff"* — invariant 20b cannot express §D's
  prescribed popover colour.
Do **not** delete a working popover to turn those lines green: that trades a
feature the analyst uses for a linter score, and §E forbids it. Surface it as a
decision for the analyst instead, report the lines as known false positives with
the invariant number, and say plainly that `validate` therefore ends FAIL.
Converting to the static `tip=` bitmap is the right move only when the analyst
asks for it, or when there is no working toggle to preserve.
