# 04 — Filters

4 placement options · order in the right panel · formatting rules

> There are **4 filter-placement options**, which can be used **simultaneously** on a single dashboard.

---

## 1. Filters in a separate panel (on the right)

Filters placed in this panel must affect **all visualizations** on the dashboard.
These are the **main** filters for working with the dashboard: `Project`, `Country`, key dates, plus
dashboard-specific filters (`Breakdown`, `Date Granularity`, etc.).

**Panel specification:**

| Parameter | Value |
|-----------|-------|
| Type | vertical container |
| Width | **200px** |
| Inner padding | **10px** |
| Fill color | **`#f5f5f5`** |
| Panel header | height **50px**, text **`FILTERS`** — Tableau Book, **10px, Bold**, `#333333` |
| Filter-group button (Show/Hide) | zone **50px** = 40px + 10px outer padding on top |
| Button caption `Click to open/close … Filters` | Tableau Book, **8px, Standard+Bold**, `#333333` |

---

## 2. Filters in a popup container (Show/Hide)

As a rule, we place this container **inside the main side panel**. The difference is that we apply
the **`Add Show/Hide Button`** function to the container. This lets us **group filters by category**
and hide them under an icon → it saves space and reduces visual noise.

Filters in such containers must also affect all visualizations, but **not be the primary ones** for
using the dashboard.

**Specification:**

- The **`Show/Hide Button`** goes into a **horizontal container 40px high**.
- Into that same container, **on the right**, add a hint text:
  **`Click to open / close 'Group Name' Filters`** — Tableau Book, **8px, Standard+Bold**, `#666666`.
- Add a **10px outer padding on top** of the horizontal container.

> Example groups in the popover: `Traffic Filters`, `Deposit Filters`, `User Filters`
> (`user_id`, `User status`, `is One timer`, `Email Verified Status`, `Card brand`, `Bonuses enabled`, `Is Receiving Promos`…).

---

## 3. Local filters

Such filters affect **only the visualization next to which they are placed**.

- If there is **more than one** local filter for a single visualization → place them in a **horizontal container**.
- **Each filter's width must not exceed `180px`.**

> Example: a `Payments Data` table with local `Breakdown`, `Withdrawals Total`, `AR type`,
> `AVG Processing time type` filters above it.

---

## 4. Filters under the dashboard header

Allowed when the report has **a great many filters** and the previous options do not let you place
them all so that they remain accessible to the user.

In that case, filters should be **grouped, and those groups visually highlighted**
(e.g. `Main Filters`, `Traffic Filters`, `Operational Filters` blocks).

---

## Order of filters in the right panel

1. **Dashboard-specific filters**: `Breakdown` + `Top N`, `Date Granularity`, `Lifetime`, dates, etc.
   These often affect not the whole workbook, but only one or a few dashboards.
2. **Widely used filters** that appear in almost every report and should always be "at hand":
   `Project`, `Country`, `Date`, etc.
3. **Non-primary filters** that we group by category. For example:
   - **Traffic Filters** — `Provider`, `Partner Name`, `Buyer`, `Campaign Name`, `OS (registered)`, `Browser Groups (registered)`, `Browser (registered)`…
   - **Deposit Filters** — `Deposit Number`, `1st Dep CUR`, `1st Dep Group`, `Include Attempts`, `Deposit Status`…
   - **User Filters** — `User Status`, `Is One Timer`, `Email Verified`, `Card Brand`, `Bonuses Enabled`, `Is Receiving Promos`…

---

## Filter (and parameter) formatting rules

1. Titles — **Tableau Book, 9px**.
2. Words longer than **3 characters** are written with a **capital letter** (preferred).
3. The filter/parameter width is **sufficient to display its title**.
4. Filters are placed in a **vertical/horizontal container**.
5. If filters can be linked by logic — place them together in an **additional horizontal container**,
   or unite them with a **shared background `#E6E6E6`** with no paddings (outer or inner) between the
   combined filters.
6. If a filter has **2 options + `All`** (e.g. `All, True, False`; `All, Alpa, Thor`) →
   use the filter type **`Single Value (dropdown)`**.
7. If a filter has **3+ options** → use the type **`Multiple Values (dropdown)`** + the **`Show Apply Button`** function.
8. Filters of the same type are better placed side by side (first all dropdowns, then sliders, etc.).
9. If filters are placed locally in a **floating horizontal container** → it is advisable to apply the
   **`Distribute Contents Evenly`** function.

### Quick filter-type table

| Number of options | Filter type | Extra |
|-------------------|-------------|-------|
| 2 options + `All` | `Single Value (dropdown)` | — |
| 3+ options | `Multiple Values (dropdown)` | `Show Apply Button` |

> **Combining related filters:** shared `#E6E6E6` background, **no paddings at all** between them —
> so the group reads as a single element (e.g. `Breakdown` + `Top N`).
