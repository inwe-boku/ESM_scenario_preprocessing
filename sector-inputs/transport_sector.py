import marimo

__generated_with = "0.23.16"
app = marimo.App(width="medium")


@app.cell
def _():
    import pandas as pd
    import numpy as np
    import pyam
    import nomenclature
    import matplotlib.pyplot as plt
    import marimo as mo

    return mo, pd, pyam


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Share of cars in transport sector
    - **scenarios** all demand and imports, base-scenarios
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
def _(pdf):
    cars_absolute = pdf.filter(scenario = ["NetZero2040 high-import/high-demand base",
                           "NetZero2040 high-import/low-demand base",
                           "NetZero2040 low-import/high-demand base",
                           "NetZero2040 low-import/low-demand base"],
               variable = ["Stock|Cars|Passenger|Combustion", "Stock|Cars|Passenger|Electric", "Stock|Cars|Passenger|Fuel Cell"],
               region = "Austria").pivot_table(index = "variable", columns =  "year", values = "value", aggfunc = "mean")
    return (cars_absolute,)


@app.cell
def _(cars_absolute, pd):
    cars_absolute_numeric = cars_absolute.apply(pd.to_numeric, errors="coerce")
    common_basis = cars_absolute_numeric.sum(axis = 0, skipna = True).loc[2023]
    #technology_shares = cars_absolute_numeric.div(cars_absolute_numeric.sum(axis=0, skipna=True), axis=1)
    technology_shares = cars_absolute_numeric.div(common_basis, axis = 1)
    technology_shares.index = [f"{variable} Share" for variable in technology_shares.index]
    cars_absolute_with_shares = pd.concat([cars_absolute_numeric, technology_shares])
    return (cars_absolute_with_shares,)


@app.cell
def _(cars_absolute_with_shares):
    cars_absolute_with_shares[2025] = cars_absolute_with_shares[[2021,2030]].mean(axis=1)
    cars_absolute_with_shares.filter(like = "Share", axis = 0)[[2025,2030,2040]]
    return


if __name__ == "__main__":
    app.run()
