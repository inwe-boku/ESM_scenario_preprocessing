import marimo

__generated_with = "0.23.16"
app = marimo.App(width="medium")


@app.cell
def _():
    import pandas as pd

    pd.options.plotting.backend = "plotly"
    import marimo as mo

    return (mo,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Change in transport demand & share of cars in transport sector
    > Data source: Netzero2040 - Scenarios: Data repository [Dataset]. Zenodo. https://doi.org/10.5281/zenodo.14051038
    - **scenarios** base-scenarios – config choice between low-demand scenarios and high-demand scenarios
    - **variables:** "Stock|Cars|Passenger|Combustion", "Stock|Cars|Passenger|Electric", "Stock|Cars|Passenger|Fuel Cell"
    - stick to a common basis for calculating shares to account for changing demand in transport sector
    - could be adapted to get a relative share per year without accounting for transport demand change
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Projection to 2050
    - shares are normalized against the 2023 total stock (`demand_factor` = sum of shares per year)
    - fit polynomial regressions of degree 1, 2 and 3 to the known `demand_factor` values (2021-2040)
    - pick the degree with the lowest leave-one-out cross-validation (LOOCV) error
    - evaluate the selected polynomial at 2025, 2035, 2045 and 2050; negative values are cut at 0
    - technology mix is interpolated linearly between known years; the 2040 mix is kept for 2050

    Function `get_transport_sector_technology_shares` holds these processing steps.
    """)
    return


@app.cell
def _():
    from esm_scenario_preprocessing.input_preprocessing import (
        TRANSPORT_SCENARIO_DEMAND_DICT,
        get_transport_sector_technology_shares,
    )

    return TRANSPORT_SCENARIO_DEMAND_DICT, get_transport_sector_technology_shares


@app.cell
def _(TRANSPORT_SCENARIO_DEMAND_DICT, mo):
    scenario_dropdown = mo.ui.dropdown(
        options=list(TRANSPORT_SCENARIO_DEMAND_DICT),
        value="High Demand",
        label="Demand scenario",
    )
    scenario_dropdown
    return (scenario_dropdown,)


@app.cell
def _(get_transport_sector_technology_shares, scenario_dropdown):
    road_transport_scenario = get_transport_sector_technology_shares(
        file_path="resources/netzero2040-times-pyam.xlsx",
        scenario=scenario_dropdown.value,
    )
    road_transport_scenario
    return (road_transport_scenario,)


@app.cell
def _(TRANSPORT_SCENARIO_DEMAND_DICT, road_transport_scenario, scenario_dropdown):
    road_transport_scenario.T.plot.area(
        stacked=True,
        title=f"Transport scenario for {scenario_dropdown.value}",
        subtitle=f"Demand scenarios: {TRANSPORT_SCENARIO_DEMAND_DICT[scenario_dropdown.value]}",
    )
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
