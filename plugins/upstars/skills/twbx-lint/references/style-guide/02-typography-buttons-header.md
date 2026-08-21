# 02 — Typography, Buttons & Header

Typography · Icons & Buttons · Header

---

## Typography

**Base font** — **Tableau Book, 9px, `#333333`** + **Workbook Locale — English (United Kingdom)**.

| # | Element | Font | Size | Weight | Color |
|---|---------|------|------|--------|-------|
| 1 | **Dashboard title** | Tableau **Bold** | **20px** | regular | `#ffffff` (white) |
| 2 | **Chart / table titles** | Tableau Book | **12px** | **bold** | `#333333` |
| 3 | **Titles inside tables** | Tableau Book | **9px** | **bold** | `#333333` |
| 4 | **Filter / parameter titles** | Tableau Book | **9px** | regular | `#333333` |
| 5 | **Action-filter descriptions & comments** (placed directly on the dashboard) | Tableau Book | **9px** | regular | `#666666` |
| 6 | **Text under the "Info" icon** | Tableau Book | **10px** | regular | `#333333` |
| 7 | **Base / default text** | Tableau Book | **9px** | regular | `#333333` |

> Row 1's weight is *regular* on purpose: the boldness comes from the
> **Tableau Bold** family itself. In XML that means `fontname='Tableau Bold'`
> **without** `bold='true'` — setting both double-bolds the title.

> Base text color is `#333333`. Muted / supporting text (comments, action filters) is `#666666`.
> White `#ffffff` is used only for the dashboard title on the dark header.

---

## Icons & Buttons

> The logo and all icons can be found via the **🔗 Link** (the "Design materials" section).

We use a set of icons to make communication with the user easier.

### Mandatory icons (for **every** report) — 2 of them

1. **Link to the `analytics-questions-updates` Slack chat** — zone width **50px**
   → <https://go-upstars.slack.com/archives/C023N3XCQ05>

2. **"Info" / "Close Info" icon (ⓘ / ✕)** — width **50px**
   Under it, inside a popup window of color **`#D9D8FF`** with **10px** inner padding
   and **corner radius 16 on three corners** (square top-right), there is:
   - information about **what time period the report covers**
     (for example: *"The report contains data for the last 3 months / 6 months / 2 years"*);
   - if needed — an **additional report description**: formula breakdowns, definitions of concepts,
     a description of the calculation logic, etc.

### Additional (optional) elements

Both go into a **horizontal container 48px high**, each with its link configured:

- **"Confluence" button** — width **186px**. Use when a detailed report
  description exists on Confluence; write that page from
  **Template: Standard Report Description**.
- **"Video" button** — width **56px**. Use when a demo presentation /
  recording of the report exists.

> ⚠️ `assets/design-materials/` does not ship the Confluence/Video icons yet
> (it still carries an obsolete `5 Mail.svg`) — they must be added from the
> design-materials source before a header can reference them.

### Hidden filters

When using hidden filters, we use the **"Filter" (▽)** and **"Close filter" (✕)** icons.

---

## Header

> The logo and all icons can be found via the **🔗 Link**.

Header specification (left to right):

| Parameter | Value |
|-----------|-------|
| **Header height** | **60px** |
| **Header background color** | **`#01001F`** |
| **Inner padding** left / right | **10px** / **10px** |
| **Report Title** | **Tableau Bold, 20px** (`#ffffff`) |
| Width of the **Slack** icon zone | **50px** |
| Width of the **ⓘ Info** icon zone | **50px** |
| Width of the **upstars logo** zone | **150px** |
| **`Data Update Time: … UTC`** block | height **30px**, under the right side of the header |

### Info popover (under the ⓘ icon)

- Background color: **`#D9D8FF`**
- Inner padding: **10px** (`Inner Padding 10px`)
- **Corner radius 16 on three corners** — the **top-right stays square**
- Controls: **✕** icon (close) + the **upstars** logo
- May also host the **Confluence** and **Video** buttons (48px container)
- **Placeholder text** (replace with the real one and remove the service line):

  > The report contains data for the last **3 months / 6 months / 2 years** *(specify as needed)*.
  > Add a report description if one is needed, and delete this text.

```
Inner Paddings 10px │                                          │ 50px │ 50px │  150px  │ 10px
        ┌───────────┴──────────────────────────────────────────┴──────┴──────┴─────────┤
  60px  │ Report Title  (Tableau Bold, 20px)          bg #01001F   [Slack][ⓘ] upstars  │
        └──────────────────────────────────────────────────────────────────────────────┘
                                                          Data Update Time: … UTC  ↕ 30px
```
