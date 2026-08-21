# 99 — Quick Checklist & Design Tokens

A concise cheat sheet for day-to-day development and a **final pre-publish review**.

---

## Pre-publish checklist

### Structure & canvas
- [ ] **Phone Layout** deleted (unless smartphone viewing was agreed).
- [ ] Canvas size — **Fixed size**: 1200–1600 × 800/850 px (horizontal) or 1200–1600 × by content (longread).
- [ ] Horizontal dashboard fits **with no scroll on the right**.
- [ ] Only **Vertical/Horizontal** containers; the first one is **Tiled**.
- [ ] No unnecessary **Floating** objects (only popovers / overlapping).

### Header
- [ ] Header: height **60px**, background **`#01001F`**, inner padding **10px** left/right.
- [ ] Present: **title** (Tableau Bold, 20px, `#ffffff`), **upstars logo**, **Slack icon**, **ⓘ icon**.
- [ ] The **`Data Update Time: … UTC`** block is present (height 30px).
- [ ] Info popover: background **`#D9D8FF`**, inner padding 10px, correct report-period text (service text removed).

### KPIs & body
- [ ] KPIs (if any) — **immediately after** the header and update time.
- [ ] Main container outer padding — **20px** (except the top near the header).
- [ ] Spacing between semantic blocks — **20–30px** (> than title↔content within a block).

### Typography
- [ ] Base font everywhere — **Tableau Book, 9px, `#333333`**.
- [ ] **Workbook Locale = English (United Kingdom)**.
- [ ] Chart/table titles — 12px bold; in-table titles — 9px bold.
- [ ] Dashboard title uses the **Tableau Bold family**, weight regular (never both).
- [ ] **Corner radius**: 16 on KPI / vizzes on colored-background dashboards; Info block 16 on 3 corners (top-right square); colored-bg dashboards use Outer/Inner Padding **8**.

### Colors
- [ ] All colors — **only from the Upstars palettes** (Main/Light/Alt/…, **S1–S8**, **D1–D7**, RAG).
- [ ] RAG logic is correct: `#D04747` (bad) · **`#E0A030`** (normal) · **`#3FB587`** (good).
- [ ] **Semantic Color Mapping** applied for `Project` / `VIP Status` / `Provider` (exact hexes, not hue-matched).
- [ ] **Accessibility**: no red-green-only *critical* status — double-code with an icon or use D5 Red-White-Blue.
- [ ] Palettes imported via `Preferences.tps`.

### Filters
- [ ] Filter panel: **200px**, background **`#f5f5f5`**, `FILTERS` header (10px Bold).
- [ ] Order: specific → general (`Project`/`Country`/`Date`) → grouped (Traffic/Deposit/User).
- [ ] 2 options + All → **Single Value (dropdown)**; 3+ → **Multiple Values (dropdown)** + **Show Apply Button**.
- [ ] Local filters ≤ **180px** wide.
- [ ] Related filters combined with a **`#E6E6E6`** background and no paddings.

### Tooltips / comments
- [ ] Tooltips edited, single style, size **10px**, key parts in bold.
- [ ] Action-filter descriptions / comments — Tableau Book, **9pt, `#666666`**.
- [ ] Action-filter navigation is described.

### Mandatory before handoff
- [ ] **Slack** icon → `analytics-questions-updates`.
- [ ] **ⓘ** icon with the report-period description (+ formulas/definitions if needed).
- [ ] (Optional) **Confluence** button (186px) + **Video** button (56px) in a **48px** horizontal container.

---

## Design tokens (at a glance)

### Fonts
| Element | Specification |
|---|---|
| Base | Tableau Book · 9px · `#333333` |
| Dashboard title | Tableau Bold · 20px · `#ffffff` |
| Chart/table title | Tableau Book · 12px · **bold** · `#333333` |
| In-table headers | Tableau Book · 9px · **bold** · `#333333` |
| Filter/param title | Tableau Book · 9px · `#333333` |
| Action-filter / comment | Tableau Book · 9px · `#666666` |
| Info-icon text / tooltip | Tableau Book · 10px · `#333333` |
| Base / default text | Tableau Book · 9px · `#333333` |
| `FILTERS` header | Tableau Book · 10px · **Bold** · `#333333` |
| Filter-group caption | Tableau Book · 8px · Standard+**Bold** · `#666666` |

### Sizes
| Token | px |
|---|---|
| Canvas (horizontal) | 1200–1600 × 800/850 |
| Header height | 60 |
| Header inner padding | 10 |
| `Data as of` block | 30 |
| Body outer padding | 20 |
| Between blocks | 20–30 |
| Filter panel | 200 |
| FILTERS panel header | 50 |
| Local filter (max) | 180 |
| Show/Hide container | 40 (+10 outer top) |
| Confluence / Video container | 48 (buttons 186 / 56) |
| Corner radius (KPI, colored-bg vizzes, Info block) | 16 |
| Colored-background dashboard padding | Outer 8 / Inner 8 |

### Color constants
| Role | HEX |
|---|---|
| Header background | `#01001F` |
| Primary text | `#333333` |
| Supporting text | `#666666` |
| Text on the header | `#ffffff` |
| Filter panel background | `#f5f5f5` |
| Info-popover background | `#D9D8FF` |
| Combined-filters background | `#E6E6E6` |
| RAG bad / normal / good | `#D04747` / `#E0A030` / `#3FB587` |

---
_Full details are in files 01–05. Source: **Tableau Style Guide v2** (23 pp., Anna Kaznacheieva)._
