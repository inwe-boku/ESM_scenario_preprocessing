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
lg = pd.DataFrame(log, columns=["scenario", "sector", "source_cell", "source_label", "action"])

with pd.ExcelWriter(f"{OUT}/NEFI_v3_energy_by_carrier_long.xlsx", engine="openpyxl") as xw:
    df.to_excel(xw, sheet_name="data", index=False)
    ck.to_excel(xw, sheet_name="checks", index=False)
    lg.to_excel(xw, sheet_name="dropped_rows_log", index=False)

print(df.shape)
print("negatives:\n", df[df["value"] < 0])
print("total checks failing:\n", ck[~ck.total_ok][["scenario", "sector", "year", "diff_total"]])
print("gas checks failing:\n", ck[~ck.gas_ok][["scenario", "sector", "year", "GasGridMix_built", "gas_aggregate_in_source", "diff_gas"]])
print(lg[lg.action.str.contains("DIFFERS")])
with open(f"{OUT}/summary.json", "w") as fh:
    json.dump({"n": len(df)}, fh)
