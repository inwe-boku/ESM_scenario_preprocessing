"""Build the harmonized long table from the NEFI v3 export (energy by carrier only).
Usage: python3 -I repair_nefi.py <source.xlsx> <out_dir>
"""
import json
import sys

import openpyxl
import pandas as pd

SRC, OUT = sys.argv[1], sys.argv[2]
YEARS = [2017, 2018, 2019, 2020, 2021, 2025, 2030, 2035, 2040, 2045, 2050]
YCOLS = list(range(3, 14))  # columns C..M
TOL = 0.002  # TWh, tolerance for sum checks (source rounding)

# (sector code, first row, last row) of each block, per sheet
BLOCKS = {
    ("Scenario1", "Scenario 1"): [
        ("IronSteel", 24, 40), ("Chemical", 43, 59), ("PulpPaper", 64, 77),
        ("NonMetalicMinerals", 81, 95), ("Machinery", 99, 113), ("NonFerrousMetals", 117, 131),
        ("TransportEquipment", 135, 149), ("FoodAndBeverages", 153, 167), ("Wood", 171, 185),
        ("Textiles", 189, 203), ("NonSpecifiedIndustry", 207, 221), ("Construction", 225, 239),
        ("Mining", 243, 257)],
    ("Scenario2a", "Scenario 2.a"): [
        ("IronSteel", 38, 54), ("Chemical", 58, 74), ("PulpPaper", 78, 92),
        ("NonMetalicMinerals", 98, 112), ("Machinery", 116, 130), ("NonFerrousMetals", 134, 148),
        ("TransportEquipment", 152, 166), ("FoodAndBeverages", 170, 184), ("Wood", 188, 202),
        ("Textiles", 206, 220), ("NonSpecifiedIndustry", 224, 238), ("Construction", 242, 256),
        ("Mining", 260, 274)],
}
H2_EFF = 0.7  # El. for H2 = Hydrogen / 0.7 in the source (verified)

SIMPLE = {  # source label -> carrier code (kept as-is)
    "Waste": "Waste", "Biofuels": "Biofuels", "Electricity": "Electricity",
    "El. for Heat Pumps": "ElectricityHP", "Electricity for HPs": "ElectricityHP",
    "Solar thermal": "SolarThermal", "Coal": "Coal", "Oil": "Oil",
    "District Heating": "DistrictHeating",
}
CARRIERS = ["Waste", "Biofuels", "Electricity", "ElectricityHP", "SolarThermal", "Coal",
            "Oil", "GasGridMix", "DistrictHeating", "Hydrogen"]
GAS_AGG_LABELS = {"Gas grid mix", "Gas grid ix", "Natural gas, Bio-CH4 and Syn-CH4"}

wb = openpyxl.load_workbook(SRC, data_only=True)
records, checks, log = [], [], []


def vals(ws, r):
    out = []
    for c in YCOLS:
        v = ws.cell(r, c).value
        out.append(float(v) if isinstance(v, (int, float)) else None)
    return out


def add(a, b):
    return [None if (x is None and y is None) else (x or 0.0) + (y or 0.0) for x, y in zip(a, b)]


for (scen, sheet), blocks in BLOCKS.items():
    ws = wb[sheet]
    for sector, r0, r1 in blocks:
        rows = []
        for r in range(r0, r1 + 1):
            lab = ws.cell(r, 1).value
            unit = str(ws.cell(r, 2).value or "").strip()
            if unit == "Hydrogen":  # label shifted into column B (260831 file, Sc. 1 Chemical row 43)
                lab, unit = "Hydrogen", ""
            if lab is None:
                continue
            rows.append((r, str(lab).strip(), unit, vals(ws, r)))
        labels = [x[1] for x in rows]
        for key in ("Total energy", "District Heating"):  # guard against shifted block rows
            if labels.count(key) != 1:
                raise ValueError(f"{sheet} rows {r0}-{r1} ({sector}): expected exactly one {key!r}, "
                                 f"found {labels.count(key)}; update BLOCKS for this source file")
        i_total = labels.index("Total energy")
        i_dh = labels.index("District Heating")
        comp = {}            # carrier -> values
        ng = bio = syn = h2_block = None
        el_h2 = None
        given_total = rows[i_total][3]
        given_gas_agg = None
        for idx, (r, lab, unit, v) in enumerate(rows):
            if unit not in ("", "TWh", "H2"):
                raise ValueError(f"unexpected unit {unit!r} at {sheet}!B{r}")
            if idx < i_total:  # inside the AIT table
                if lab in SIMPLE:
                    comp[SIMPLE[lab]] = v
                elif lab in ("Gas grid mix", "CH4"):
                    ng = v
                elif lab in ("Bio-CH4", "Biogas"):
                    bio = v
                elif lab == "Synth-CH4":
                    syn = v
                elif lab == "Hydrogen" and idx == i_dh + 1:
                    h2_block = v
                elif lab == "Hydrogen":  # top-of-block row = grid-share H2 (or empty)
                    log.append((scen, sector, f"{sheet}!A{r}", lab, "dropped: H2 share of gas grid (not direct use)"))
                else:
                    raise ValueError(f"unhandled label {lab!r} at {sheet}!A{r}")
            elif idx == i_total:
                log.append((scen, sector, f"{sheet}!A{r}", lab, "dropped: aggregate (used for check)"))
            else:  # below the total
                if lab == "El. for H2":
                    el_h2 = v
                    log.append((scen, sector, f"{sheet}!A{r}", lab, "dropped: H2 is counted as Hydrogen (no double count)"))
                elif lab == "Transformation losses H2":
                    log.append((scen, sector, f"{sheet}!A{r}", lab, "dropped: part of El. for H2 (no double count)"))
                elif lab in GAS_AGG_LABELS and given_gas_agg is None:
                    given_gas_agg = (r, v)
                    log.append((scen, sector, f"{sheet}!A{r}", lab, "dropped: gas aggregate (rebuilt from components, used for check)"))
                elif lab in ("H2", "Hydrogen") and sector == "IronSteel":
                    same = all(abs((a or 0) - (b or 0)) < 1e-9 for a, b in zip(v, h2_block))
                    log.append((scen, sector, f"{sheet}!A{r}", lab, "dropped: exact duplicate of in-table Hydrogen" if same else "dropped: DIFFERS from in-table Hydrogen"))
                elif lab in ("H2", "Gas grid mix"):
                    log.append((scen, sector, f"{sheet}!A{r}", lab, "dropped: H2 share of gas grid (not direct use)"))
                else:
                    raise ValueError(f"unhandled label {lab!r} at {sheet}!A{r}")

        zero = [0.0 if x is not None else None for x in given_total]
        bio = bio or zero; syn = syn or zero; h2_block = h2_block or zero
        # GasGridMix = methane-type gases only (natural gas, Bio-CH4/Biogas, Synth-CH4), never H2
        gas = add(add(ng, bio), syn)
        comp["GasGridMix"] = gas
        # Hydrogen = total H2 demand (pipeline + produced on site), no distinction.
        # El. for H2 / transformation losses are NOT added to Electricity (would double count).
        comp["Hydrogen"] = h2_block
        if el_h2 is not None:  # sanity: El. for H2 == Hydrogen / 0.7
            for h, e in zip(h2_block, el_h2):
                if h is not None and e is not None and abs(e * H2_EFF - h) > TOL:
                    raise ValueError(f"El. for H2 != Hydrogen/0.7 in {scen} {sector}")

        # checks
        # gas aggregate in source: incl. in-table H2 everywhere except IronSteel/Chemical
        agg_has_h2 = sector not in {"IronSteel", "Chemical"}
        for k, y in enumerate(YEARS):
            if given_total[k] is None:
                continue
            s = sum((comp[c][k] or 0.0) for c in CARRIERS)
            chk = {"scenario": scen, "sector": sector, "year": y,
                   "sum_carriers": s,
                   "AIT_total_energy": given_total[k],
                   "diff_total": s - given_total[k],
                   "El_for_H2_in_source_not_used": (el_h2[k] if el_h2 else 0.0),
                   "GasGridMix_built": gas[k],
                   "Hydrogen": h2_block[k],
                   "gas_aggregate_in_source": (given_gas_agg[1][k] if given_gas_agg else None),
                   "source_gas_row": (f"{sheet}!A{given_gas_agg[0]}" if given_gas_agg else ""),
                   "source_aggregate_includes_H2": agg_has_h2}
            ref = gas[k] + ((h2_block[k] or 0.0) if agg_has_h2 else 0.0)
            chk["diff_gas"] = (None if chk["gas_aggregate_in_source"] is None
                               else ref - chk["gas_aggregate_in_source"])
            checks.append(chk)

        for c in CARRIERS:
            for k, y in enumerate(YEARS):
                records.append({"scenario": scen, "sector": sector, "carrier": c,
                                "unit": "TWh", "year": y, "value": comp[c][k]})

df = pd.DataFrame(records)
missing = df[df["value"].isna()]
if not missing.empty:
    raise ValueError(f"{len(missing)} empty source values:\n{missing.to_string()}")
ck = pd.DataFrame(checks)
ck["total_ok"] = ck["diff_total"].abs() <= TOL
ck["gas_ok"] = ck["diff_gas"].isna() | (ck["diff_gas"].abs() <= TOL)
# ---------------- Economy sheet: GDP formation and material output ----------------
ECO = "Economy"
SCENARIOS = [scen for scen, _ in BLOCKS]
SECTORS = [s for s, _, _ in BLOCKS[("Scenario1", "Scenario 1")]]  # identical to sheet `data`
GDP_VAR = "Industry|GDP formation [by Sector]"
MAT_VAR = "Industry|Material Output [by Sector]"
GDP_FIRST, GDP_LAST = 5, 39
GDP_ROWS = {  # source row -> (expected label, sector); GDP has no scenario split in the source
    13: ("Construction", "Construction"), 16: ("Mining", "Mining"),
    17: ("Iron and Steel", "IronSteel"), 18: ("Chemical and Petrochemical", "Chemical"),
    19: ("Non-Ferrous Metals", "NonFerrousMetals"), 20: ("Non-Metalic Minerals", "NonMetalicMinerals"),
    21: ("Transport Equipment", "TransportEquipment"), 22: ("Machinery", "Machinery"),
    23: ("Food and Beverages", "FoodAndBeverages"), 24: ("Pulp, Paper and Print", "PulpPaper"),
    25: ("Wood and Wood Products", "Wood"), 26: ("Textiles and Leather", "Textiles"),
    27: ("other manufacturing", "NonSpecifiedIndustry"),
}
GDP_SUMS = [  # (check name, summed rows, reference row)
    ("manufacturing_subtotal", range(17, 28), 30), ("gdp_industry", [30, 13, 16], 31),
    ("construction_parts", [10, 11, 12], 13), ("mining_parts", [14, 15], 16),
    ("duplicate_construction", [28], 13), ("duplicate_mining", [29], 16),
]
GOODS_BLOCKS = {"Scenario1": (45, 80), "Scenario2a": (85, 114)}  # Sc1 starts at its year header row
CEMENT_TOTAL = "Cement production (50% imported clinker from 2040 on"
PRODUCTS = {  # source label -> (sector, product, source unit, output unit, divisor)
    "Iron & Steel, primary": ("IronSteel", "PrimarySteel", "[MtSteel /a]", "Mt", 1),
    "Steel secondary (EAF)": ("IronSteel", "SecondarySteelEAF", "[Mtsteel /a]", "Mt", 1),
    "domestic produdtion": ("NonMetalicMinerals", "Cement", "[MtCement/a]", "Mt", 1),
    "Lime dom. Prod.": ("NonMetalicMinerals", "Lime", "[Mt]", "Mt", 1),
    "Glass dom. Prod.": ("NonMetalicMinerals", "Glass", "[Mt]", "Mt", 1),
    "Bricks dom. Prod.": ("NonMetalicMinerals", "Bricks", "[m³]", "m3", 1),
    "Soda Ash dom. Prod.": ("NonMetalicMinerals", "SodaAsh", "[Mt]", "Mt", 1),
    "Limestone & Dolomit dom.prod.": ("NonMetalicMinerals", "LimestoneDolomite", "[Mt]", "Mt", 1),
    "Ammonia dom. Prod.": ("Chemical", "Ammonia", "[ktAmmonia /a]", "Mt", 1000),
    "Nitric acid dom. Prod.": ("Chemical", "NitricAcid", "[ktNitric acid /a]", "Mt", 1000),
    "Methanol dom. Prod.": ("Chemical", "Methanol", "[ktMethanol /a]", "Mt", 1000),
    "Olefine domestic production": ("Chemical", "Olefines", "[ktOlefine /a]", "Mt", 1000),
    "Pulp prod. Dom.": ("PulpPaper", "Pulp", "[Mtpaper /a]", "Mt", 1),
    "Al dom. Secondary prod.": ("NonFerrousMetals", "SecondaryAluminium", "[ktAL/a]", "Mt", 1000),
}
DROPPED_GOODS = {  # source label -> reason
    "of which imported as HB-DRI": "dropped: subtracted from PrimarySteel (imported iron, empty = 0)",
    CEMENT_TOTAL: "dropped: total incl. cement from imported clinker (used for check)",
    "of which imported clinker": "dropped: import, not domestic production (used for check)",
    "Methanol DEMAND": "dropped: demand, not domestic production (used for check)",
    "Methanol imports": "dropped: import, not domestic production (used for check)",
    "of which from Methanol": "dropped: share, not an output",
    "Wood imports": "dropped: share, not an output",
    "H2 dom. Prod.": "dropped: share, not an output",
}


def read_rows(ws, r0, r1):
    """(row, label, unit, values) for every labelled row in r0..r1."""
    return [(r, str(ws.cell(r, 1).value).strip(), str(ws.cell(r, 2).value or "").strip(), vals(ws, r))
            for r in range(r0, r1 + 1) if ws.cell(r, 1).value is not None]


def sum_check(name, scen, parts, ref):
    """One economy_checks row per year: sum of parts vs. reference."""
    out = []
    for k, y in enumerate(YEARS):
        s = sum((p[k] or 0.0) for p in parts)
        out.append({"check": name, "scenario": scen, "year": y, "sum_parts": s, "reference": ref[k],
                    "diff": s - (ref[k] or 0.0), "ok": abs(s - (ref[k] or 0.0)) <= TOL})
    return out


def build_gdp(ws):
    """GDP formation of the 13 industry sectors, copied to every scenario."""
    if vals(ws, 4) != [float(y) for y in YEARS]:
        raise ValueError(f"{ECO}!C4:M4: unexpected year header")
    recs, chks = [], []
    for r, lab, unit, v in read_rows(ws, GDP_FIRST, GDP_LAST):
        if unit != "10^9 EUR":
            raise ValueError(f"unexpected unit {unit!r} at {ECO}!B{r}")
        if r not in GDP_ROWS:
            log.append(("all", "", f"{ECO}!A{r}", lab, "dropped: subtotal, duplicate or non-industry GDP"))
            continue
        exp, sector = GDP_ROWS[r]
        if lab != exp or any(x is None for x in v):
            raise ValueError(f"{ECO}!A{r}: expected {exp!r} with 11 values, found {lab!r}")
        for scen in SCENARIOS:
            recs += [{"scenario": scen, "sector": sector, "variable": f"{GDP_VAR}|{sector}", "product": None,
                      "unit": "bn EUR", "year": y, "value": v[k]} for k, y in enumerate(YEARS)]
    for name, rows, ref in GDP_SUMS:
        chks += sum_check(name, "all", [vals(ws, r) for r in rows], vals(ws, ref))
    return sorted(recs, key=lambda x: (SCENARIOS.index(x["scenario"]), SECTORS.index(x["sector"]))), chks


def read_goods(ws, scen):
    """Kept product rows {label: (row, values)} and all rows by label for checks."""
    r0, r1 = GOODS_BLOCKS[scen]
    kept, raw = {}, {}
    for r, lab, unit, v in read_rows(ws, r0, r1):
        if lab in ("Sc. 1", "Sc. 2a"):
            continue
        raw[lab] = v
        if lab in DROPPED_GOODS:
            log.append((scen, "", f"{ECO}!A{r}", lab, DROPPED_GOODS[lab]))
        elif lab in PRODUCTS:
            if unit != PRODUCTS[lab][2] or any(x is None for x in v):
                raise ValueError(f"{ECO}!A{r} {lab!r}: unit {unit!r} or empty values")
            kept[lab] = (r, v)
        else:
            raise ValueError(f"unhandled label {lab!r} at {ECO}!A{r}")
    return kept, raw


def build_material(ws, scen):
    """Material output per sector/product in Mt (Bricks in m3); empty rows for sectors without data."""
    kept, raw = read_goods(ws, scen)
    hb = [x or 0.0 for x in raw.get("of which imported as HB-DRI", [None] * len(YEARS))]
    recs = []
    for lab, (_, v) in kept.items():
        sector, product, _, unit, div = PRODUCTS[lab]
        if product == "PrimarySteel":
            v = [a - b for a, b in zip(v, hb)]
        recs += [{"scenario": scen, "sector": sector, "variable": f"{MAT_VAR}|{sector}|{product}",
                  "product": product, "unit": unit, "year": y, "value": v[k] / div} for k, y in enumerate(YEARS)]
    for sector in set(SECTORS) - {x["sector"] for x in recs}:
        recs += [{"scenario": scen, "sector": sector, "variable": f"{MAT_VAR}|{sector}", "product": None,
                  "unit": "Mt", "year": y, "value": None} for y in YEARS]
    chks = sum_check("cement_total", scen, [raw["domestic produdtion"], raw["of which imported clinker"]],
                     raw[CEMENT_TOTAL])
    if "Methanol DEMAND" in raw:
        chks += sum_check("methanol_demand", scen, [raw["Methanol dom. Prod."], raw["Methanol imports"]],
                          raw["Methanol DEMAND"])
    return sorted(recs, key=lambda x: SECTORS.index(x["sector"])), chks


if vals(wb[ECO], GOODS_BLOCKS["Scenario1"][0]) != [float(y) for y in YEARS]:
    raise ValueError(f"{ECO}!C45:M45: unexpected year header")
eco_recs, eco_checks = build_gdp(wb[ECO])
for scen in SCENARIOS:
    r, c = build_material(wb[ECO], scen)
    eco_recs, eco_checks = eco_recs + r, eco_checks + c
eco = pd.DataFrame(eco_recs, columns=["scenario", "sector", "variable", "product", "unit", "year", "value"])
eco = eco.sort_values("scenario", key=lambda s: s.map(SCENARIOS.index), kind="stable")
eck = pd.DataFrame(eco_checks)
if (eco["value"] < 0).any():
    raise ValueError(f"negative economy values:\n{eco[eco['value'] < 0]}")

lg = pd.DataFrame(log, columns=["scenario", "sector", "source_cell", "source_label", "action"])

with pd.ExcelWriter(f"{OUT}/NEFI_v3_energy_by_carrier_long.xlsx", engine="openpyxl") as xw:
    df.to_excel(xw, sheet_name="data", index=False)
    ck.to_excel(xw, sheet_name="checks", index=False)
    eco.to_excel(xw, sheet_name="economy", index=False)
    eck.to_excel(xw, sheet_name="economy_checks", index=False)
    lg.to_excel(xw, sheet_name="dropped_rows_log", index=False)

print(df.shape)
print("negatives:\n", df[df["value"] < 0])
print("total checks failing:\n", ck[~ck.total_ok][["scenario", "sector", "year", "diff_total"]])
print("gas checks failing:\n", ck[~ck.gas_ok][["scenario", "sector", "year", "GasGridMix_built", "gas_aggregate_in_source", "diff_gas"]])
print(lg[lg.action.str.contains("DIFFERS")])
with open(f"{OUT}/summary.json", "w") as fh:
    json.dump({"n": len(df)}, fh)
