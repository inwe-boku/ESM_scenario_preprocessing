import marimo

__generated_with = "0.23.16"
app = marimo.App(width="medium")


@app.cell
def _():
    import pandas as pd

    pd.options.plotting.backend = "plotly"
    import numpy as np
    import pyam
    import math
    import marimo as mo

    return math, mo, np, pd, pyam


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


@app.cell
def _(pyam):
    pdf = pyam.IamDataFrame("resources/netzero2040-times-pyam.xlsx")
    return (pdf,)


@app.cell
def _(mo):
    # Dropdown for Scenarios:
    dropdown_dict = {
        "High demand": [
            "NetZero2040 high-import/high-demand base",
            "NetZero2040 low-import/high-demand base",
        ],
        "Low demand": [
            "NetZero2040 high-import/low-demand base",
            "NetZero2040 low-import/low-demand base",
        ],
    }

    scenario_dropdown = mo.ui.dropdown(
        options=dropdown_dict, value="High demand", label="Demand scenario"
    )
    scenario_dropdown
    return (scenario_dropdown,)


@app.cell
def _(pdf, scenario_dropdown):
    cars_absolute = pdf.filter(
        scenario=scenario_dropdown.value,
        variable=[
            "Stock|Cars|Passenger|Combustion",
            "Stock|Cars|Passenger|Electric",
            "Stock|Cars|Passenger|Fuel Cell",
        ],
        region="Austria",
    ).pivot_table(index="variable", columns="year", values="value", aggfunc="mean")
    return (cars_absolute,)


@app.cell
def _(cars_absolute, math, pd):
    cars_absolute_numeric = cars_absolute.apply(pd.to_numeric, errors="coerce")
    common_basis = cars_absolute_numeric.sum(axis=0, skipna=True).loc[2023]
    # technology_shares = cars_absolute_numeric.div(cars_absolute_numeric.sum(axis=0, skipna=True), axis=1)
    if math.isclose(common_basis, 0):
        raise Exception("Comparison-variable 'common_basis' is near zero. ")
    technology_shares = cars_absolute_numeric.div(common_basis, axis=1)
    technology_shares.index = [
        f"{variable} Share" for variable in technology_shares.index
    ]
    cars_absolute_with_shares = pd.concat([cars_absolute_numeric, technology_shares])
    return (cars_absolute_with_shares,)


@app.cell
def _(cars_absolute_with_shares):
    cars_absolute_with_shares[2025] = cars_absolute_with_shares[[2021, 2030]].mean(
        axis=1
    )
    cars_absolute_with_shares.filter(like="Share", axis=0)[[2025, 2030, 2040]]
    return


@app.cell
def _(cars_absolute_with_shares):
    demand_factor = cars_absolute_with_shares.filter(like="Share", axis=0)[
        [2021, 2023, 2025, 2030, 2040]
    ].sum(axis=0)
    return (demand_factor,)


@app.cell
def _(demand_factor):
    demand_factor
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Extrapolating `demand_factor` to 2050
    - fit polynomial regressions of degree 1, 2 and 3 to the known `demand_factor` values (2021-2040)
    - pick the degree with the lowest leave-one-out cross-validation (LOOCV) error
    - evaluate the selected polynomial at year 2050 to obtain the estimate
    - Allocating the 2050 demand factor across technologies keeps the 2040 technology mix unchanged
    """)
    return


@app.cell
def _(demand_factor, np):
    def loocv_mse(years, values, degree: int) -> float:
        squared_errors = []
        for i in range(len(years)):
            train_years = np.delete(years, i)
            train_values = np.delete(values, i)
            coeffs = np.polyfit(train_years, train_values, degree)
            prediction = np.polyval(coeffs, years[i])
            squared_errors.append((prediction - values[i]) ** 2)
        return float(np.mean(squared_errors))

    demand_factor_years = demand_factor.index.to_numpy(dtype=float)
    demand_factor_values = demand_factor.to_numpy(dtype=float)

    demand_factor_cv_errors = {
        degree: loocv_mse(demand_factor_years, demand_factor_values, degree)
        for degree in (1, 2, 3)
    }
    demand_factor_best_degree = min(
        demand_factor_cv_errors, key=demand_factor_cv_errors.get
    )
    demand_factor_coeffs = np.polyfit(
        demand_factor_years, demand_factor_values, demand_factor_best_degree
    )
    demand_factor_2050 = float(np.polyval(demand_factor_coeffs, 2050))
    return (
        demand_factor_2050,
        demand_factor_best_degree,
        demand_factor_cv_errors,
    )


@app.cell
def _(demand_factor_2050, demand_factor_best_degree, demand_factor_cv_errors):
    print(f"LOOCV MSE per degree: {demand_factor_cv_errors}")
    print(f"Selected regression degree: {demand_factor_best_degree}")
    print(f"Estimated demand_factor for 2050: {demand_factor_2050:.4f}")
    return


@app.cell
def _(demand_factor, demand_factor_2050, pd):
    demand_factor_with_2050 = pd.concat(
        [demand_factor, pd.Series({2050: demand_factor_2050})]
    )
    return (demand_factor_with_2050,)


@app.cell
def _(cars_absolute_with_shares, demand_factor_with_2050):
    technology_shares_2040 = cars_absolute_with_shares.filter(like="Share", axis=0)[
        2040
    ]
    technology_fractions_2040 = technology_shares_2040 / technology_shares_2040.sum()
    cars_absolute_with_shares.loc[technology_fractions_2040.index, 2050] = (
        technology_fractions_2040 * demand_factor_with_2050[2050]
    )
    road_transport_scenario = cars_absolute_with_shares.filter(like="Share", axis=0)[
        [2025, 2030, 2040, 2050]
    ]
    return (road_transport_scenario,)


@app.cell
def _(road_transport_scenario, scenario_dropdown):
    road_transport_scenario.T.plot.area(
        stacked=True,
        title=f"Transport scenario for {scenario_dropdown.selected_key}",
        subtitle=f"Demand scenarios: {scenario_dropdown.value}",
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ---
    ### Funtion `get_transport_sector_technology_shares` holds the processing steps from that notebook
    """)
    return


@app.cell
def _():
    from esm_scenario_preprocessing.input_preprocessing import (
        get_transport_sector_technology_shares,
    )

    return (get_transport_sector_technology_shares,)


@app.cell
def _(get_transport_sector_technology_shares):
    low_demand = get_transport_sector_technology_shares(
        file_path="resources/netzero2040-times-pyam.xlsx", scenario="Low Demand"
    )
    high_demand = get_transport_sector_technology_shares(
        file_path="resources/netzero2040-times-pyam.xlsx", scenario="High Demand"
    )
    return high_demand, low_demand


@app.cell
def _(low_demand):
    low_demand.T.plot.area()
    return


@app.cell
def _(high_demand):
    high_demand.T.plot.area()
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
