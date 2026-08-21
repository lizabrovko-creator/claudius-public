# 03 — Color Palettes

Palette types · Categorical · Semantic Color Mapping · Sequential · Divergent · RAG Status

> 🎨 All palettes in this section are bundled into a ready-to-import file
> **[`upstars-palettes.tps`](upstars-palettes.tps)** for Tableau (see the install
> instructions at the end of this file).

---

## Types of Palettes

| Type | Purpose |
|------|---------|
| **Categorical** | Helps display the **non-numeric** value of objects. Colors are designed to be **visually distinct** from one another. |
| **Sequential** | Follows an order that correlates with the **lightness / brightness** of the color. Suitable for data ranging **from low to high** values. |
| **Divergent** | Distributes numeric values in a triangular brightness sequence with different hues in the left and right "shoulders". It is a combination of two sequential palettes with constraints (see below). |
| **RAG Status** | A **red-amber-green** palette: highlights **bad–normal–good** values (data status). |

**Divergent palette constraints:**
1. A single hue is used for each "shoulder" of the palette.
2. The trajectory of hue and brightness is **balanced** between the two shoulders.
3. The neutral center value has **zero chroma** (use **white** or **light grey**).

---

## Categorical

### UPSTARS Main
`#5535BE` · `#210E5F` · `#12CC2A` · `#FFE200` · `#C2660A` · `#0E9FBF` · `#EF50CC` · `#005DE8` · `#D04747`

| # | HEX | # | HEX | # | HEX |
|---|-----|---|-----|---|-----|
| 1 | `#5535BE` | 4 | `#FFE200` | 7 | `#EF50CC` |
| 2 | `#210E5F` | 5 | `#C2660A` | 8 | `#005DE8` |
| 3 | `#12CC2A` | 6 | `#0E9FBF` | 9 | `#D04747` |

### UPSTARS Light
`#928EEC` · `#A6FFB1` · `#FFF393` · `#6EEDD4` · `#FFB1EE` · `#9CC4FF` · `#FFA2A2` · `#F5CE9E` · `#CECED6`

### UPSTARS Alternative
`#8794D5` · `#EDC948` · `#59CD90` · `#FF9D85` · `#6EC3D8` · `#DF90D8` · `#CECED6`

### UPSTARS Purple-Grey
`#210E5F` · `#5535BE` · `#928EEC` · `#D9D8FF` · `#CECED6` · `#A5A5AC` · `#81818E`

### UPSTARS Blue-Grey
`#003E9B` · `#005DE8` · `#3888FF` · `#9CC4FF` · `#CECED6` · `#A5A5AC` · `#81818E`

---

## Semantic Color Mapping

**These assignments are prescriptive.** When a viz colors by `Project`,
`VIP Status` or `Provider`, use the exact hex per member — do not hue-match
against a palette. A member absent from these tables gets no invented color:
leave whatever valid Upstars token it already carries and report it.

### Projects — palette: UPSTARS **Alternative**

| Member | HEX | Member | HEX |
|---|---|---|---|
| `alpa` | `#8794D5` | `king` | `#FF9D85` |
| `thor` | `#EDC948` | `bond` | `#6EC3D8` |
| `vegas` | `#59CD90` | `felix` | `#DF90D8` |

> `felix #DF90D8` sits close to Main's `#EF50CC`; if a member outside this table
> already uses `#EF50CC`, call out the visual collision rather than silently
> reassigning it.

### VIP Status — palettes: UPSTARS Main + Purple-Grey + Blue-Grey

| Member | HEX | Member | HEX |
|---|---|---|---|
| `PLATINUM` | `#EF50CC` | `NEW` | `#12CC2A` |
| `DIAMOND` | `#005DE8` | `IRON Ace Star` | `#003E9B` |
| `GOLD` | `#FFE200` | `IRON Core` | `#4C9AFF` |
| `SILVER` | `#CECED6` | `IRON exVIP_Recent` | `#A9CCF5` |
| `BRONZE` | `#C2660A` | `IRON ExVIP_Past` | `#5E7BA6` |
| `STAR` | `#210E5F` | `IRON New` | `#2FB4D4` |
| `ACE` | `#5535BE` | `ACE2` | `#928EEC` |
| `EXVIP` | `#D04747` | `ACE3` | `#D9D8FF` |

### Provider — palettes: UPSTARS Main + Purple-Grey + Blue-Grey

| Member | HEX | Member | HEX |
|---|---|---|---|
| `Affiliate_Makeberry_B2C` | `#003E9B` | `Arbitrage_Traffbaza` | `#D9D8FF` |
| `Affiliate_Makeberry_CPA` | `#005DE8` | `Inhouse` | `#EF50CC` |
| `Affiliate_Makeberry_Infl…` | `#4C9AFF` | `PR` | `#FFE200` |
| `Arbitrage_Makeberry` | `#210E5F` | `Experiments` | `#C2660A` |
| `Arbitrage_Cashbee` | `#5535BE` | `SEO` | `#D04747` |
| `Arbitrage_044Agency` | `#928EEC` | `Direct` | `#12CC2A` |

> ⚠️ `#4C9AFF`, `#A9CCF5`, `#5E7BA6` and `#2FB4D4` are not members of any
> palette listed above, even though the guide requires colors to come only from
> the palettes. They are used here as given; flag for the guide's author.

---

## Sequential

Format: `light (low values) → saturated (high values)`.

| Code | Name | From | To |
|------|------|------|-----|
| **S1** | Purple-Grey | `#F3F3F3` | `#928EEC` |
| **S2** | Purple-White | `#FFFFFF` | `#928EEC` |
| **S3** | Red | `#F3F3F3` | `#D04747` |
| **S4** | Amber | `#F3F3F3` | `#FFB804` |
| **S5** | Green | `#F3F3F3` | `#3FB587` |
| **S6** | Blue | `#F3F3F3` | `#005DE8` |
| **S7** | Blue-Green | `#D0FFD6` | `#005DE8` |
| **S8** | Grey-White | `#FFFFFF` | `#81818E` |

> ⚠️ The guide prints S3 Red's end label as `#005DE8` — a copy-paste of S6 Blue.
> The rendered swatch is red; sampling the gradient's end pixel gives
> `#D04848` ≈ **`#D04747`**, which is the value used above and in the `.tps`.
> Confirm with the guide's author.

---

## Divergent

Format: `left shoulder → neutral center → right shoulder`.

| Code | Name | Left | Center | Right |
|------|------|------|--------|-------|
| **D1** | Yellow-White-Purple | `#FFB804` | `#FFFFFF` | `#928EEC` |
| **D2** | Yellow-Grey-Purple | `#FFB804` | `#F3F3F3` | `#928EEC` |
| **D3** | Red-White-Green | `#D04747` | `#FFFFFF` | `#3FB587` |
| **D4** | Red-Grey-Green | `#D04747` | `#F3F3F3` | `#3FB587` |
| **D5** | Red-White-Blue | `#D04747` | `#FFFFFF` | `#003E9B` |
| **D6** | Red-Amber-Green | `#D04747` | `#E0A030` | `#3FB587` |
| **D7** | Upstars Purple | `#76E0E7` | `#8576E4` | `#CA76E7` |

---

## RAG Status

Color order: **red (bad) · amber (normal) · green (good)**.

| Set | Bad (red) | Normal (amber) | Good (green) |
|-----|-----------|----------------|--------------|
| **RAG #1** | `#D04747` | `#E0A030` | `#3FB587` |
| **RAG #2** (light) | `#FFA2A2` | `#FFDE8B` | `#9CE8CC` |
| **RAG Alternative** | `#FF9D85` | `#EDC948` | `#59CD90` |

### Accessibility

> **red-green is unreadable for deuteranopia.** For **critical** statuses either
> duplicate the signal with an **icon**, or use **D5 Red-White-Blue** instead of
> a red-green pair.

---

## Reference — shared "anchor" colors

Colors that repeat across palettes (use them as anchors):

| HEX | Where it appears |
|-----|------------------|
| `#5535BE` | Main, Purple-Grey (saturated purple); VIP `ACE`, Provider `Arbitrage_Cashbee` |
| `#210E5F` | Main, Purple-Grey (dark purple); VIP `STAR`, Provider `Arbitrage_Makeberry` |
| `#928EEC` | Light, Purple-Grey, S1, S2, D1/D2 right shoulder; VIP `ACE2` |
| `#005DE8` | Main, Blue-Grey, S6, S7; VIP `DIAMOND` |
| `#3FB587` | S5, D3, D4, D6, RAG #1 (green good) |
| `#D04747` | Main, S3, D3–D6, RAG #1 (red bad); VIP `EXVIP`, Provider `SEO` |
| `#E0A030` | RAG #1 (amber), D6 center |
| `#FFB804` | S4 Amber end, D1/D2 left shoulder |
| `#C2660A` | Main; VIP `BRONZE`, Provider `Experiments` |
| `#EDC948` | Alternative, RAG Alt; Project `thor` |
| `#CECED6` / `#A5A5AC` / `#81818E` | neutral greys (Light, Alternative, Purple-Grey, Blue-Grey, S8) |
| `#FFFFFF` / `#F3F3F3` | neutral center of Divergent; light end of Sequential |

---

## How to load the palettes into Tableau (Preferences.tps)

1. Take the file **[`upstars-palettes.tps`](upstars-palettes.tps)** from this set
   (or the official Preferences file from the link in the guide).
2. Rename / place it as **`Preferences.tps`** in the Tableau repository folder:
   - **Windows:** `Documents\My Tableau Repository\Preferences.tps`
   - **macOS:** `~/Documents/My Tableau Repository/Preferences.tps`
   (if the file already exists — merge the `<preferences>…</preferences>` contents into the existing
   one, without duplicating the `<workbook>` tag).
3. **Restart Tableau Desktop.**
4. The palettes will appear in `Edit Colors → Palette` (categorical ones in the discrete list;
   sequential/divergent ones in the ranged list).

> ⚠️ Colors are taken **only** from these palettes. Do not add custom shades outside the system —
> that is the main cause of "inconsistency" between reports.
