# 01 — Dashboard Structure

Canvas Structure · Layout & Containers · Spacing

---

## Canvas Structure

Standard top-to-bottom dashboard structure:

```
┌─────────────────────────────────────────────────────────────┬───────────┐
│  HEADER: Report Title            [Slack] [ⓘ Info]  upstars   │  FILTERS  │
│                          Data Update Time: … UTC              │  Traffic  │
├───────────────────────────────────────────────────────────── │  Filters  │
│  KPI 1 Title │ KPI 2 Title │ KPI 3 Title │ KPI 4 Title        │  Game     │
├─────────────────────────────┬───────────────────────────────  │  Filters  │
│  Chart 1 Title              │  Chart 2 Title                   │  User     │
│                             │                                  │  Filters  │
├─────────────────────────────┴───────────────────────────────  │  ▽ open/  │
│  Chart 3 Title                                                 │   close   │
└───────────────────────────────────────────────────────────────┴──────────┘
```

### Mandatory elements

- The **Header** must contain:
  - the **title** (Report Title);
  - the **company logo** (upstars);
  - **navigation icons**: a link to the **Slack** chat and **report Info (ⓘ)**.
- **KPIs** — when used, they must be placed **immediately after the Header and the report update time**.
- **Report update date and time in UTC** — on the right, below the header (`Data Update Time: … UTC`).
- **Filter panel** — on the right.
- The **main body of the report** — built from **vertical and horizontal containers**.

---

## Layout & Containers

1. **Delete the Phone Layout** unless it has been agreed with the report's customer that it will be viewed on a smartphone.

2. **Fix the report width and height** according to the chosen dashboard type (`Size → Fixed size`):

   | Type | Width | Length (height) |
   |------|-------|-----------------|
   | **a. Horizontal dashboard** — use it **whenever** everything can fit on a single page **without a scroll on the right** | **1200 to 1600 px** | **800 / 850 px** |
   | **b. Longread** | **1200 to 1600 px** | **depends on content** |

3. Use **only Vertical / Horizontal containers**.
   Only the **first container** should be `Tiled` (this type for the first container is selected automatically).

4. **Do not use Floating objects.** Allowed only for:
   - a popup window with report information;
   - cases where you need to place one object on top of another (e.g. a parameter/filter over a chart/table).

### Example object hierarchy (Item hierarchy)

```
#1 Basic
 └ A  "The report contains data from…"   (text / info popover)
 └ ▤  Tiled
     └ ▥  Outer Horizontal
         ├ ▤  Header + Body
         │   ├ ▥  Header
         │   └ ▤  Body
         └ ▤  Filters
```

> **Container rule in a nutshell:** the first one is `Tiled`; everything else is strictly
> `Horizontal`/`Vertical`; `Floating` is the exception only for popovers and overlapping objects.

---

## Spacing

### Outer padding

The dashboard — specifically, the **main vertical container holding the visualizations** — must have
an **outer padding of 20px on all sides**, **except the top edge near the title**.

There, the role of extra space between the title and the main body is played by the **report update
time block** (`Date as of…`).

### Inner paddings

- The distance **between semantic blocks** must be **greater** than the distance between a title and
  the content of its current block.
- Reference: **20–30px** = the sum of the outer and inner paddings.
- The **filter block** must be perceived as a **separate semantic block**.

### Spacing reference sizes

| Element | Value |
|---------|-------|
| Outer padding of the main container | **20px** (all sides except the top near the header) |
| Spacing between semantic blocks | **20–30px** |
| Filter panel width | **200px** |
| Bottom padding of the dashboard | **20px** |

> 💡 The hierarchy of paddings mirrors the hierarchy of content: blocks are spread apart more (20–30px)
> than a title is from its own content inside the block. That is what makes a dashboard "readable".

---

## Corner Radius

Tableau can round container corners (**Layout** tab). We use it for exactly
three things:

- **KPI** blocks;
- the **block under the Info button** — rounded on 3 corners, **except the
  top-right**;
- **visualizations on dashboards with a colored background**.

For a **colored-background dashboard** it matters to keep the grid intact and
leave enough breathing room so that neither outer nor inner objects touch the
block's edges. Defaults:

| Token | Value |
|-------|-------|
| **Corner Radius** | **16** |
| **Outer Padding** | **8** |
| **Inner Padding** | **8** |

> ⚠️ This 8/8 padding pair applies **only** to colored-background dashboards.
> A normal white-background dashboard keeps outer padding 20px and 20–30px
> between blocks.

In raw XML these live in a zone's `<zone-style>` as `corner-radius` (all four
corners at once) or the per-corner attributes
`corner-radius-top-left` / `-top-right` / `-bottom-right` / `-bottom-left`
— e.g. the Info block is radius 16 on three with
`<format attr='corner-radius-top-right' value='0' />`.
