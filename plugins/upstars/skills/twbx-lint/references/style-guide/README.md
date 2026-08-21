# Upstars — Tableau Style Guide

> A practical best-practices reference for building Tableau dashboards.
> Source: **"Tableau Style Guide v2"** (23 pages), author — **Anna Kaznacheieva** for Upstars.
> These `.md` files are a verbatim, meticulous distillation of the guide, reformatted as a working reference.

---

## Why this matters

Applying a consistent style across all reports **makes dashboards easier to use** for end users.
It also raises the overall value of the analytics product by reducing the risk tied to poor
interpretation of visualizations or plain difficulty in using a report.

The **Tableau Style Guide for developers** is, first and foremost, **time saved** on choosing
formats and design while building dashboards — time that can be redirected to high-value analytical
work without sacrificing the quality of the final product.

---

## How to use this set

1. Start a new report with **[01 — Dashboard Structure](01-dashboard-structure.md)** (canvas, containers, spacing).
2. Format text and the header per **[02 — Typography, Buttons & Header](02-typography-buttons-header.md)**.
3. Take colors **only** from **[03 — Color Palettes](03-color-palettes.md)** (ready-made `.tps` is in `assets/`).
4. Lay out filters per **[04 — Filters](04-filters.md)**.
5. Polish tooltips and comments per **[05 — Tooltips, Actions & Comments](05-tooltips-and-comments.md)**.
6. Before publishing, run the **[99 — Quick Checklist](99-quick-checklist.md)**.

## File index

| File | Contents |
|------|----------|
| [`01-dashboard-structure.md`](01-dashboard-structure.md) | Canvas Structure · Layout & Containers · Spacing |
| [`02-typography-buttons-header.md`](02-typography-buttons-header.md) | Typography · Icons & Buttons · Header |
| [`03-color-palettes.md`](03-color-palettes.md) | Palette types · Categorical · **Semantic Color Mapping** · Sequential (S1–S8) · Divergent (D1–D7) · RAG · Accessibility (all HEX) |
| [`04-filters.md`](04-filters.md) | 4 filter-placement options · order · formatting rules |
| [`05-tooltips-and-comments.md`](05-tooltips-and-comments.md) | Tooltips · Actions and Comments |
| [`99-quick-checklist.md`](99-quick-checklist.md) | Condensed checklist + design-tokens table |
| [`assets/upstars-palettes.tps`](assets/upstars-palettes.tps) | Ready-to-import `Preferences.tps` with all palettes for Tableau |

---

## Useful links (from the original guide)

- 🔗 **Tableau Template** — the report starter template.
- 🔗 **Design materials** — logo and all icons.
- 🔗 **Preferences file for loading palettes** (+ 🔗 **Instructions for loading palettes**).
- 💬 **Slack `analytics-questions-updates`** — <https://go-upstars.slack.com/archives/C023N3XCQ05>

> ℹ️ The Template and Design-materials URLs are embedded in the PDF as hyperlinks under the text
> (the raw URLs are not visible) — substitute your team's current links. The only link stated
> explicitly in the guide is the Slack one (above).

---

## Key design tokens (quick cheat sheet)

| Token | Value |
|-------|-------|
| Base font | **Tableau Book, 9px, `#333333`** |
| Workbook Locale | **English (United Kingdom)** |
| Dashboard title | Tableau **Bold, 20px, `#ffffff`** |
| Header background | `#01001F` |
| Canvas size (horizontal) | 1200–1600 × 800/850 px, **Fixed size** |
| Filter panel width | **200px**, fill `#f5f5f5`, inner padding 10px |
| Body outer padding | **20px** on all sides (except the top, near the header) |
| Spacing between semantic blocks | **20–30px** |
| Info-popover background | `#D9D8FF`, inner padding 10px, radius 16 on 3 corners |
| Combined-filters background | `#E6E6E6` |
| RAG (bad · normal · good) | `#D04747` · **`#E0A030`** · **`#3FB587`** |
| Corner radius (KPI · colored-bg vizzes · Info block) | **16** (Info: 3 corners, top-right square) |
| Colored-background dashboard padding | **Outer 8 / Inner 8** |
| Optional header buttons | **Confluence 186px · Video 56px**, container **48px** |

Full specifications are in the corresponding files.
