# NEFI – Industry energy demand by carrier (harmonized long table)

Project: INFRA-ENSHURE · Data source: AIT (NEFI Lab) · Prepared: 2026-10-15

## Files

| File | Content |
|------------------------------------|------------------------------------|
| `NEFI_v3_energy_by_carrier_long.xlsx` | sheet **`data`** – the machine-readable long table (the deliverable) |
|  | sheet `checks` – per scenario/sector/year: sum of carriers vs. AIT "Total energy", rebuilt gas mix vs. source gas aggregate |
|  | sheet **`economy`** – GDP formation and material output per sector (see section *Economy*) |
|  | sheet `economy_checks` – sum and duplicate checks of the Economy tab |
|  | sheet `dropped_rows_log` – every source row that was not carried over, with source cell and reason |
| `README.md` | this file – all assumptions and rules |
| `repair_nefi.py` | script that produces the workbook from the source xlsx |

## Source

- Workbook **`260831-industry-energy-demand-NEFI-POI-INFRAENSURE-Export.xlsx`**
  - Differences to v3 in the energy tables (cell-by-cell comparison): (a) Sc. 2.a Textiles 2050 is now filled in (was empty); (b) Sc. 1 Chemical rows 42/43: block title and the top "Hydrogen" label moved one cell (the label is now in column B). All other energy values are identical.
  - there are jumps in Scenario 1 chemical between 2025 and 2030 and the Scneario 1 "All Manuf" block does not match its sectors after 2025
- Used tabs: **`Scenario 1`** (columns A–M) and **`Scenario 2.a`** (columns A–M).
- Not used (scope decision): the CO₂-by-sector tables (right-hand side of both scenario tabs), tab `test` (AIT check sheet in GWyr). Tab `Economy` is used for the `economy` sheet only (see section *Economy*).

## Structure of the `data` sheet

One row per `scenario × sector × carrier × year`. Columns:

| Column | Values |
|------------------------------------|------------------------------------|
| `scenario` | `Scenario1` = POI_2026 in NEFI Lab · `Scenario2a` = ZEM in NEFI Lab (moderate electrification, hydrogen instead; 2b would be CCS instead of H₂) |
| `sector` | `IronSteel`, `Chemical`, `PulpPaper`, `NonMetalicMinerals`, `Machinery`, `NonFerrousMetals`, `TransportEquipment`, `FoodAndBeverages`, `Wood`, `Textiles`, `NonSpecifiedIndustry`, `Construction`, `Mining` (13 sectors) |
| `carrier` | `Waste`, `Biofuels`, `Electricity`, `ElectricityHP`, `SolarThermal`, `Coal`, `Oil`, `GasGridMix`, `DistrictHeating`, `Hydrogen` (10 carriers) |
| `unit` | always `TWh` (final energy per year) |
| `year` | 2017, 2018, 2019, 2020, 2021, 2025, 2030, 2035, 2040, 2045, 2050 |
| `value` | number at full source precision (no rounding) |

2 scenarios × 13 sectors × 10 carriers × 11 years = **2,860 rows**, no empty values. Every combination is present (carriers a sector does not use are `0`).

**All rows of a sector are additive.** There are no subtotals or totals in the table, so summing over `carrier` gives the sector total, which equals AIT's "Total energy".

## Index harmonization (source label → code)

| Source label(s) | Carrier code |
|------------------------------------|------------------------------------|
| Waste | `Waste` |
| Biofuels | `Biofuels` |
| Electricity | `Electricity` |
| El. for Heat Pumps / Electricity for HPs | `ElectricityHP` |
| Solar thermal | `SolarThermal` |
| Coal | `Coal` |
| Oil | `Oil` |
| District Heating | `DistrictHeating` |
| first "Gas grid mix" / "CH4" + "Bio-CH4" / "Biogas" + "Synth-CH4" — **no hydrogen** | `GasGridMix` |
| in-table "Hydrogen" (total hydrogen demand, pipeline and on-site) | `Hydrogen` |

| Source block title                  | Sector code            |
|-------------------------------------|------------------------|
| Iron & Steel / I&S                  | `IronSteel`            |
| Chemical and Petrochemical / Chem.  | `Chemical`             |
| Pulp, Paper and Print / P&P         | `PulpPaper`            |
| Non-Metalic Minerals / NMM          | `NonMetalicMinerals`   |
| Machinery                           | `Machinery`            |
| Non-Ferrous Metals / NFM            | `NonFerrousMetals`     |
| Transport Equipment / Transport Eq. | `TransportEquipment`   |
| Food and Beverages / F&B            | `FoodAndBeverages`     |
| Wood and Wood Products / Wood       | `Wood`                 |
| Textiles and Leather / Textiles     | `Textiles`             |
| Non-Specified Industry / non spec.  | `NonSpecifiedIndustry` |
| Construction                        | `Construction`         |
| Mining                              | `Mining`               |

The sector codes are the same as in the v2 harmonization rounds.

## Rules applied

### 1. Gas: `GasGridMix` = methane-type gases only

The model cannot distinguish natural gas from renewable gas, so all methane-type gases go into one carrier. **Hydrogen is never part of `GasGridMix`.**

`GasGridMix = CH4 / natural gas (first "Gas grid mix" row) + Bio-CH4 / Biogas + Synth-CH4`

`GasGridMix` is **rebuilt from the component rows** for every sector, not copied from the source aggregate row. In most sectors (all except Iron & Steel and Chemical) the source aggregate below the total ("Gas grid mix" / "Gas grid ix") *includes* the in-table hydrogen. Copying it would therefore mix H₂ into the gas. The source aggregates were used only as a check: rebuilt `GasGridMix` (+ in-table Hydrogen where the source includes it) equals the source aggregate in every sector except Sc. 1 Construction (see Data quirks).

### 2. Hydrogen: `Hydrogen` = total hydrogen demand

`Hydrogen` is the in-table "Hydrogen" row of AIT's table (directly after District Heating), in every sector. **No distinction is made between hydrogen from the pipeline and hydrogen produced on site.**

The source contains three kinds of hydrogen row. How each was treated:

| Row (position in block) | Meaning (derived from the arithmetic) | Treatment |
|------------------------|------------------------|------------------------|
| **in-table "Hydrogen"** (directly after District Heating, inside AIT's table) | AIT model hydrogen; part of AIT's "Total energy" | → `Hydrogen` (all sectors) |
| **extra "H2" row** (Sc. 1, below the total) and **top-of-block "Hydrogen"** (Sc. 2.a, and Sc. 1 Chemical row 43) | Source gas aggregate (incl. H₂) × an assumed H₂ share of the gas grid, identical in every sector (Sc. 1: 2025 10.9 %, 2030 17.6 %, 2035 32.3 %, 2040 74.2 %, 2045–2050 100 %; Sc. 2.a: 2035 27.7 %, 2040 93.4 %, 2045 86.5 %, 2050 75.5 %). In Chemical it is in-table H₂ + share × gas. Not part of AIT's "Total energy". | **dropped**. It is an alternative assumption on how much of the gas grid is hydrogen, which is not consistent with AIT's carrier split (see open question 1). |
| second "Hydrogen" below the total in Iron & Steel | exact duplicate of the in-table row (checked, all years identical) | dropped |

### 3. Electricity for hydrogen production is not counted

`El. for H2` and `Transformation losses H2` (Iron & Steel, Chemical) are **dropped**. The hydrogen they produce is already counted as `Hydrogen` (rule 2). Adding the electricity as well would count the same energy twice. In the source, El. for H2 = Hydrogen / 0.7 (70 % efficiency) and El. for H2 = Hydrogen + Transformation losses H2 in every year; the script checks this. The dropped amounts are in the `checks` sheet (`El_for_H2_in_source_not_used`).

### 4. Aggregates and totals are dropped

Dropped: "Total energy" of every sector, the gas aggregate rows, and the whole "All Manufacturing Industries" block (AllManuf is an aggregate of the sectors). The AllManuf block also carries "Chem. Ind. Foss. Rohstoffe (ölbasiert)" and "actual total"; per comment, the fossil feedstock row is ignored. AIT's "Total energy" was used to verify the result (see Checks).

### 5. Other conventions

- Units: all source values in the two scenario tabs are already TWh, so no conversion was needed.
- Full numeric precision kept, no rounding.
- No values were interpolated, imputed, averaged or otherwise corrected.

## Checks

- **Sector totals:** for all 2 × 13 × 11 = 286 scenario-sector-year combinations, the sum of the 10 carriers equals AIT's "Total energy". Maximum deviation: \< 1·10⁻¹⁴ TWh. So the table reproduces AIT's totals exactly, with nothing double counted or lost.
- **Gas aggregate:** rebuilt `GasGridMix` (+ in-table Hydrogen where the source aggregate includes it) = source gas aggregate in every sector, except Sc. 1 Construction (see below).
- **Hydrogen production:** in I&S and Chemical, El. for H2 × 0.7 = Hydrogen in every year (script stops otherwise).
- **All Manufacturing:** Sc. 2.a – the sum of the 13 sectors equals the AllManuf "Total" in every year. Sc. 1 – see Data quirk 3.

## Known Data quirks

1.  **Sc. 1 Construction (rows 238/239):** the row labelled "Gas grid mix" below the total actually contains the H₂-share values (0 until 2021, then 0.031 … 0.221). The "H2" row below it is empty. `GasGridMix` was rebuilt from components, so the output is unaffected.
2.  **Sc. 1 Chemical, break between 2025 and 2030:** from 2030, Waste, Coal, Oil, Solar thermal and heat-pump electricity drop to 0, Electricity falls from 5.48 to 2.20 TWh, and District Heating rises from 0.70 to 2.26 TWh. AIT's note on the `test` tab explains this: for Chemical and NMM, "Total E Dem." now points to the sector-specific tabs. Values kept as delivered.
3.  **Sc. 1 All Manufacturing vs. sum of sectors:** identical up to 2025. From 2030 the AllManuf block is 3–7 TWh higher than the sum of the 13 sectors (mainly electricity −5…−7.5, gas +1.4…3.2, district heating +1.4…1.7, waste −1.2…−2.3). It was apparently not updated to the changed Chemical/NMM values (see 2).
4.  **Sc. 2.a Iron & Steel, CH4 2050 = −0.005 TWh** (small negative in the source). After adding Synth-CH4 the resulting `GasGridMix` is positive (4.025 TWh).
5.  Sc. 1 Transport Equipment: the "H2" row has "H2" in the unit column (row dropped anyway).
6.  Sc. 1 Chemical row 43: the top "Hydrogen" label is in column B instead of A in the 260831 file. The script reads it correctly; the row is dropped anyway (rule 2).

## Recheck needed:

1.  Are the H2 rows treated consistently?
2.  Sc. 1 Chemical 2025→2030 break and the outdated Sc. 1 AllManuf block: intended?

## Economy (sheet `economy`)

Source: tab `Economy`, columns A–M. GDP block rows 4–39 (one table, no scenario split); produced goods Sc. 1 rows 45–80, Sc. 2a rows 84–114. Full step-by-step rules for agents: `prompt_for_nefi_economy.txt`.

Columns: `scenario | sector | variable | product | unit | year | value`. Sectors are exactly the 13 sector codes of sheet `data`.

| Variable | Unit | Content |
|------------------------------------|------------------------------------|------------------------------------|
| `Industry\|GDP formation [by Sector]\|<sector>` | `bn EUR` | GDP formation of the sector (source `10^9 EUR`); same values in both scenarios |
| `Industry\|Material Output [by Sector]\|<sector>\|<product>` | `Mt` (Bricks: `m3`) | domestic production of the product |
| `Industry\|Material Output [by Sector]\|<sector>` | `Mt` | empty value: sectors without produced goods (Machinery, TransportEquipment, FoodAndBeverages, Wood, Textiles, NonSpecifiedIndustry, Construction, Mining) |

759 rows: 286 GDP (13 × 11 × 2) + 473 Material Output (Sc1 242, Sc2a 231). Units never carry "/a".

**GDP mapping:** Construction (row 13), Mining (16), Iron and Steel → `IronSteel`, Chemical and Petrochemical → `Chemical`, Non-Ferrous Metals → `NonFerrousMetals`, Non-Metalic Minerals → `NonMetalicMinerals`, Transport Equipment → `TransportEquipment`, Machinery, Food and Beverages → `FoodAndBeverages`, Pulp, Paper and Print → `PulpPaper`, Wood and Wood Products → `Wood`, Textiles and Leather → `Textiles`, other manufacturing → `NonSpecifiedIndustry` (rows 17–27).

**Material Output products:**

| Sector | Products (source label) |
|------------------------------------|------------------------------------|
| `IronSteel` | `PrimarySteel` (Iron & Steel, primary − of which imported as HB-DRI), `SecondarySteelEAF` |
| `NonMetalicMinerals` | `Cement` (domestic production), `Lime`, `Glass`, `Bricks` (m3), `SodaAsh`, `LimestoneDolomite` |
| `Chemical` | `Ammonia`, `NitricAcid`, `Methanol` (dom. prod.), `Olefines` (Sc1 only) — kt converted to Mt (/1000) |
| `PulpPaper` | `Pulp` (source unit "Mtpaper/a" = Mt) |
| `NonFerrousMetals` | `SecondaryAluminium` — kt converted to Mt (/1000) |

**Rules:**
1. GDP is copied to both scenarios (source has one table). Rows 28/29 (duplicates of 13/16), all subtotals and all non-industry rows (Agriculture, Services, Energy, Total GDP) are dropped.
2. Material Output = domestic production only. Dropped: cement total, "of which imported clinker", methanol demand and imports, and the shares "of which from Methanol", "Wood imports", "H2 dom. Prod.".
3. `PrimarySteel` = primary steel − HB-DRI imports (only domestic ironmaking counts). Empty HB-DRI cells (before 2030) count as 0.
4. Only value transformations: kt → Mt and the HB-DRI subtraction. Bricks stay in m3 (no density assumption). Sectors without data stay empty (no proxy).

**Checks (`economy_checks`):** rows 17–27 = Manufacturing sub-total; Manufacturing + Construction + Mining = GDP INDUSTRY; Construction and Mining parts = their rows; rows 28/29 = rows 13/16; cement domestic + imported clinker = cement total (both scenarios); Sc1 methanol dom. prod. + imports = demand. All pass (max. deviation < 1·10⁻¹³).

**Data quirks:**
1. Sc1 `PrimarySteel` drops to 3.8 Mt (2030–2035), 0.93 Mt (2040–2045) and 0 Mt (2050) because iron is imported as HB-DRI. Sc2a HB-DRI is 0.
2. Sc1 domestic cement halves from 2040 (imported clinker); in Sc2a domestic = total.
3. Sc2a has no methanol demand/imports and no olefine rows; Sc2a methanol dom. prod. = Sc1 methanol demand. Sc2a has no `Olefines` product.
4. Sc2a ammonia halves from 2040.
5. Cement label "domestic produdtion" is misspelled in the source.

**Open questions for AIT:** (1) Price base of GDP? (2) Is GDP really identical in both scenarios? (3) Bricks tonnage/density? (4) Olefines in Sc2a not reported or same as Sc1?

## Reproducibility

Built with `repair_nefi.py` (Python 3, openpyxl, pandas): `python3 repair_nefi.py <source.xlsx> <output_dir>`. Block positions (first/last row per sector) are fixed in the script. Each row label is mapped by name and by position within the block. Any unknown label or unit makes the script stop instead of silently skipping it. The script also stops if a block range does not contain exactly one "Total energy" and one "District Heating" row (block positions no longer match the source file → update `BLOCKS`), or if any output value would be empty.
