import marimo

__generated_with = "0.23.16"
app = marimo.App(
    width="medium",
    layout_file="layouts/analyze-nefi-inputs.slides.json",
)


@app.cell
def _():
    import marimo as mo
    import pandas as pd
    import plotly.graph_objects as go
    from esm_scenario_preprocessing.harmonization_helpers import (
        energy_inputs_harmonization,
        pypsa_combinations_for_nefi_inputs_dict,
    )

    return (
        energy_inputs_harmonization,
        go,
        mo,
        pd,
        pypsa_combinations_for_nefi_inputs_dict,
    )


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Preprocess NEFI-Input for Industry Scenarios

    needs 2 harmonization processes: Industrial Sectors and Energy inputs
    - **industrial sectors** have much higher resolution in PyPSA-AT – splitting NEFI-values for PyPSA-AT-input
    - **energy inputs** are comparable
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Industrial Sectors in PyPSA-AT
    > Pipeline inputfile for Industrial Production

    - input for _absolute values_ of output for Industrial Sectors
    - manipulation for coupling with GCE
    """)
    return


@app.cell
def _(mo):
    year = mo.ui.dropdown(options = ["2025", "2050"], label = "Year of evaluation")
    return (year,)


@app.cell
def _(mo, year):
    mo.vstack([mo.hstack([year, mo.md(f"Evaluates year {year.value}")])])
    return


@app.cell
def _(pd, year):
    # Import file and combine some sectors into one to be more consistent with NACE-Codes. - unit: Mt/a

    industrial_production = pd.read_csv(f"resources/pypsa_industry_files/industrial_production_per_country_tomorrow_{year.value}-modified.csv", index_col = 0) /1e3
    industrial_production.index.names = ["Mt/a"]

    pypsa_sectors_to_combine: dict = {
        "Pulp and Paper production": ["Pulp production", "Paper production"],
        "Non-metallic mineral products production": ["Cement", "Ceramics & other NMM", "Glass production"],
        "Iron and Steel": ["Electric arc", "Integrated steelworks", "DRI + Electric arc"],
        "Basic metals except Iron and Steel": ["Aluminium - primary production", "Aluminium - secondary production", "Other non-ferrous metals"],
        "HVC including recycling": ["HVC", "HVC (chemical recycling)", "HVC (mechanical recycling)"]
    }

    for combined_sector, sector_list in pypsa_sectors_to_combine.items():
        industrial_production[combined_sector] = industrial_production[sector_list].sum(axis = 1)
        industrial_production.drop(sector_list, axis = 1, inplace=True)
    return industrial_production, pypsa_sectors_to_combine


@app.cell
def _(industrial_production, year):
    # "Other industrial sectors" accounts for the biggest part. This comes from the raw data used in pypsa.
    industrial_production.filter(regex = "AT", axis = 0).T.plot.barh(title = f"Industrial output in Austria for {year.value} in PyPSA-AT")
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Energy input for Industrial Sectors in PyPSA-AT
    > Pipeline inputfile Industrial sector ratios
    - Defines an energy input for a certain output of Material (eg. MWh/t)
    - Fits well as independent input from industry output
    """)
    return


@app.cell(hide_code=True)
def _(pd, pypsa_sectors_to_combine: dict, year):
    # Import file and combine same sectors, take absolute mean of sub-sector values – unit: TWh/Mt = MWh/t
    industrial_sector_ratios = pd.read_csv(f"resources/pypsa_industry_files/industry_sector_ratios_{year.value}.csv", header = [0,1], index_col=0)
    industrial_sector_ratios.index.names = ["TWh/Mt"]
    # Combine the same sectors as in industrial_production, per country (level 0 of the columns).
    industrial_sector_ratios_combined = industrial_sector_ratios
    for _combined_sector, _sector_list in pypsa_sectors_to_combine.items():
        _cols_to_drop = industrial_sector_ratios_combined.columns[
            industrial_sector_ratios_combined.columns.get_level_values(1).isin(_sector_list)
        ]
        _combined = industrial_sector_ratios_combined[_cols_to_drop].T.groupby(level=0).mean().T
        _combined.columns = pd.MultiIndex.from_product([_combined.columns, [_combined_sector]])
        industrial_sector_ratios_combined = pd.concat(
            [industrial_sector_ratios_combined, _combined], axis=1
        ).drop(columns=_cols_to_drop)
    industrial_sector_ratios_combined = industrial_sector_ratios_combined.loc[
            ~industrial_sector_ratios_combined.index.str.contains("process emission", regex=True)
        ]
    return (industrial_sector_ratios_combined,)


@app.cell
def _(industrial_sector_ratios_combined):
    industrial_sector_ratios_combined.filter(regex = "AT", axis=1).T.plot.bar(stacked = True, figsize = (15,5))
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Industrial energy demand in PyPSA-AT
    > Multiplication of existing pipeline inputs (production × sector ratios)
    - Energy needed for Industry sectors with certain amount of material output
    """)
    return


@app.cell(hide_code=True)
def _(industrial_production, industrial_sector_ratios_combined):
    # Combine Mt/a (index: country, columns: sector) with TWh/Mt (columns: country, sector)
    # to get TWh/a per energy carrier, country and sector.
    # `industrial_sector_ratios_combined` has a 2-level column index (country, sector), so
    # stacking `industrial_production` into a Series with a matching (country, sector)
    # MultiIndex lets `.mul(..., axis=1)` broadcast and align on those column pairs directly.
    prod_stacked = industrial_production.stack()
    prod_stacked.index.names = industrial_sector_ratios_combined.columns.names = ["country", "sector"]

    industrial_energy_demand = industrial_sector_ratios_combined.mul(prod_stacked, axis=1)
    industrial_energy_demand.index.names = ["TWh/a"]
    return (industrial_energy_demand,)


@app.cell
def _(industrial_energy_demand):
    industrial_energy_demand.filter(regex = "AT", axis = 1)
    return


@app.cell(hide_code=True)
def _(mo):
    render_sankey_switch = mo.ui.switch(label = "Render pypsa-at industry sankey")
    return (render_sankey_switch,)


@app.cell(hide_code=True)
def _(mo, render_sankey_switch):
    mo.hstack([render_sankey_switch, mo.md(f"Rendering: {render_sankey_switch.value}")])
    return


@app.cell(hide_code=True)
def _(go, industrial_energy_demand, render_sankey_switch, year):
    # Sankey: energy carriers (index) -> sectors (columns), restricted to Austria.
    _at_energy_demand = industrial_energy_demand.filter(regex="AT", axis=1)
    _at_energy_demand.columns = _at_energy_demand.columns.droplevel("country")

    _carriers = _at_energy_demand.index.tolist()
    _sectors = _at_energy_demand.columns.tolist()
    _node_labels = _carriers + _sectors

    # A few carrier/sector combinations are negative (e.g. hydrogen is a
    # by-product of chlorine production) - these represent an output rather
    # than an input and are out of scope for an input -> sector Sankey.
    _flows = _at_energy_demand.stack()
    _flows = _flows[_flows > 0]
    industrial_energy_sankey_at = go.Figure(
        go.Sankey(
            node={"label": _node_labels, "pad": 30, "thickness": 20},
            link={
                "source": [_carriers.index(carrier) for carrier, _sector in _flows.index],
                "target": [len(_carriers) + _sectors.index(sector) for _carrier, sector in _flows.index],
                "value": _flows.values,
            },
        )
    )
    industrial_energy_sankey_at.update_layout(
        title_text=f"Austria: industrial energy demand by carrier and sector in {year.value} (TWh/a)",
        font_size=10,
    )
    if render_sankey_switch.value:
        industrial_energy_sankey_at.write_html("industry_sankey_pypsa-at.html")
    industrial_energy_sankey_at
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ---
    ## Compare NEFI energy input against current implementation
    > Variable `Total energy Demand by Fuels, all Industry Sector` – `Final Energy [by Sector]|Industry`

    - NEFI comes as overall energy input per Industry Sector
    - Industry sector outputs are missing
    - Energy input harmonization with PyPSA-AT seems to be quite easy possible

    ### Energy inputs need to be harmonized with PyPSA-AT inputs
    | NEFI | PyPSA-AT | comment |
    |---|---| --- |
    | elec | Electricity, Electricity for HPs |
    | coal and coke | Coal | PyPSA-AT distinguishes between coal and coke |
    | biomass | Biofuels | NEFI has no Biomass as energy Input |
    | methane | Gas, Biogas, Synth-CH4 | PyPSA-AT can't really distinguish between "renewable" and fossil gas
    | hydrogen | Hydrogen, H2 |
    | heat | District Heating, Solar thermal |
    | naphtha | Oil | there is no direct "Oil" input for Industry in PyPSA-AT |
    | ammonia | — | maybe part of methane in NEFI? |
    | methanol | — |
    """)
    return


@app.cell
def _(energy_inputs_harmonization, pd):
    # Import NEFi values, convert unit to TWh and harmonize with pypsa-energy inputs
    nefi_total_industry_fe = pd.read_excel("resources/v2-NEFI-Scenario2a.xlsx", sheet_name="Scenario2a-AllManuf", index_col=0, header = 0, decimal = ",")
    nefi_fe = nefi_total_industry_fe.select_dtypes(exclude=object) #.mul(8.760) # GWyr to TWh <-- new input is in TWh
    nefi_total_industry_fe_in_pypsa = energy_inputs_harmonization(nefi_fe)
    return (nefi_total_industry_fe_in_pypsa,)


@app.cell(hide_code=True)
def _(
    industrial_energy_demand,
    nefi_total_industry_fe_in_pypsa,
    pd,
    pypsa_combinations_for_nefi_inputs_dict,
    year,
):
    # combine sectors in pypsa-setting for consistency
    _industrial_energy_demand = industrial_energy_demand.T
    for _key, _list in pypsa_combinations_for_nefi_inputs_dict.items():
        _industrial_energy_demand[_key] = _industrial_energy_demand[_list].sum(axis = 1)
        _industrial_energy_demand.drop(_list, axis = 1, inplace = True)
    _industrial_energy_demand = _industrial_energy_demand.T
    _total_demand_pypsa_at = _industrial_energy_demand.filter(regex = "AT", axis = 1).sum(axis = 1)
    _total_demand_nefi = nefi_total_industry_fe_in_pypsa[int(year.value)]
    # combine total_demand_pypsa_at and total_demand_nefi to one dataset and create a bar-plot to compare the values of the two datasources.
    total_demand_comparison = pd.DataFrame({
        "PyPSA-AT": _total_demand_pypsa_at,
        "NEFI": _total_demand_nefi,
    }).reindex(_total_demand_pypsa_at.index)  # drop nefi rows with no pypsa carrier mapping (e.g. "Total")
    total_demand_comparison.plot.bar(
        figsize=(10, 5),
        title=f"Industrial energy demand by carrier in Austria, {year.value} (TWh/a): PyPSA-AT vs. NEFI",
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ---
    ## Analyze Industry Sectors in NEFI
    ⚠️ **the given sectors are only a subset and do not sum up to industry demand of all sectors**
    - single Sector inputs
    - System flows from energy input to sector output
    """)
    return


@app.cell
def _(mo):
    nefi_sector = mo.ui.dropdown(options = ["AllManuf","IronSteel", "Chemical", "PulpPaper", "NonMetalicMinerals", "Machinery", "NonFerrousMetals", "FoodAndBeverages", "Wood", "Textiles", "NonSpecifiedIndustry", "Construction", "Mining"], value= "AllManuf", label = "Industry Sector ")
    return (nefi_sector,)


@app.cell(hide_code=True)
def _(mo, nefi_sector):
    mo.vstack([mo.hstack([nefi_sector, mo.md(f"Evaluates sector {nefi_sector.value}")])])
    return


@app.cell
def _(energy_inputs_harmonization, nefi_sector, pd):
    nefis = pd.read_excel("resources/v2-NEFI-Scenario2a.xlsx", sheet_name="Scenario2a-"+nefi_sector.value, index_col=0, header=0)
    nefis = nefis.select_dtypes(exclude=object) #.mul(8.760) # GWyr to TWh <-- new intput is in TWh
    nefis = energy_inputs_harmonization(nefis)
    if "Total" in nefis.index: 
        nefis.drop("Total", axis = 0, inplace=True)
    if "losses" in nefis.index:
        nefis.drop("losses", axis = 0, inplace=True)
    return (nefis,)


@app.cell
def _(nefi_sector, nefis):
    nefis.T.plot.area(stacked = True, figsize = (15,5), title = f"Energy input for sector {nefi_sector.value} [TWh/a]") 
    return


@app.cell
def _(energy_inputs_harmonization, pd, year):
    sectors = ["IronSteel", "Chemical", "PulpPaper", "NonMetalicMinerals", "Machinery", "NonFerrousMetals", "FoodAndBeverages", "Wood", "Textiles", "NonSpecifiedIndustry", "Construction", "Mining"]
    dfs = []

    for sector in sectors:
        df = pd.read_excel(
            "resources/v2-NEFI-Scenario2a.xlsx",
            sheet_name="Scenario2a-"+sector,
            index_col=0,
            header=0,
        )
        df = df.select_dtypes(exclude=object) #.mul(8.760)  # GWyr to TWh <-- new input is in TWh
        df = df[[int(year.value)]]  # Filter to selected year
        df = energy_inputs_harmonization(df)  # Harmonize inputs
        df.columns = [sector]  # Rename column to sector name
        df.drop("Total", axis=0, inplace=True, errors="ignore")
        dfs.append(df)

    # Combine all sectors
    nefi_inputs_by_sector = pd.concat(dfs, axis=1)
    return (nefi_inputs_by_sector,)


@app.cell
def _(go, nefi_inputs_by_sector, year):
    # Create Sankey diagram
    _carriers = nefi_inputs_by_sector.index.tolist()
    _sectors = nefi_inputs_by_sector.columns.tolist()
    _node_labels = _carriers + _sectors

    _flows = nefi_inputs_by_sector.stack()
    _flows = _flows[_flows > 0]

    nefi_energy_sankey = go.Figure(
        go.Sankey(
            node={"label": _node_labels, "pad": 30, "thickness": 20},
            link={
                "source": [_carriers.index(carrier) for carrier, _ in _flows.index],
                "target": [
                    len(_carriers) + _sectors.index(sector)
                    for _, sector in _flows.index
                ],
                "value": _flows.values,
            },
        )
    )
    nefi_energy_sankey.update_layout(
        title_text=f"NEFI: energy input by carrier and sector in {year.value} (TWh/a)",
        font_size=10,
    )

    nefi_energy_sankey
    return


@app.cell(hide_code=True)
def _(energy_inputs_harmonization, pd, year):
    # Check, if dataset is consistent, or sectors are missing
    _sectors = ["IronSteel", "Minerals", "Chemical", "PulpPaper", "AllManuf"]
    _dfs = []

    for _sector in _sectors:
        _df = pd.read_excel(
            "resources/NEFI-Export_test-all_sectors.xlsx",
            sheet_name=_sector,
            index_col=0,
            header=0,
        )
        _df = _df.select_dtypes(exclude=object) #.mul(8.760)  # GWyr to TWh <-- new input is in TWh
        _df.drop("    Total", axis=0, inplace=True, errors="ignore")
        _df = _df[[year.value]]  # Filter to selected year
        _df = energy_inputs_harmonization(_df)  # Harmonize inputs
        _df.columns = [_sector]
        _dfs.append(_df)

    all_sectors_and_sum = pd.concat(_dfs, axis = 1)
    all_sectors_and_sum["manual sum"] = all_sectors_and_sum[["IronSteel", "Minerals", "Chemical", "PulpPaper"]].sum(axis = 1)
    all_sectors_and_sum[["manual sum", "AllManuf"]].plot.bar(figsize = (15,5),title = "Subsectors do not sum up to values of All Manifacturing [TWh/a] ")
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    This is the end.

    ---
    """)
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
