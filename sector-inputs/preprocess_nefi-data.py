import marimo

__generated_with = "0.23.16"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    import pandas as pd
    import numpy as np
    import plotly.express as px
    import plotly.graph_objects as go

    return go, mo, np, pd, px


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Estimate energy input per industry output
    This notebook uses JRC-IDEES - data for Austria showing the relationship between Added Value and Physical output from historical data. Using this data source, regression estimates are shown.

    The idea would be to give an estimate on the physical output for the PyPSA-AT workflow from the value added reported in the NEFI scenarios.
    """)
    return


@app.cell
def _():
    # input file for industry output in t for pypsa-at comes from JRC IDEE
    # the file also holds data on value added of industry output
    fp = "/home/maxnutz/Documents/infra-enshure/scenario-inputs/industry_files/JRC-IDEES-2023/AT/JRC-IDEES-2023_Industry_AT.xlsx"
    return (fp,)


@app.cell
def _(mo):
    sheet_name_dict: dict[str, str] = {
        "Iron and steel": "ISI",
        "Non-ferrous metals": "NFM",
        "Chemical industry": "CHI",
        "Non-metallic mineral products": "NMM",
        "Pulp, paper and printing": "PPA",
        "Food, beverages and tobacco": "FBT",
        "Transport equipment": "TRE",
        "Machinery equipment": "MAE",
        "Textiles and leather": "TEL",
        "Wood and wood products": "WWP",
        "Other industrial sectors": "OIS"
                                      }
    fit_grade_dict : dict[str, float] = {
        "Iron and steel": 3,
        "Non-ferrous metals": 2,
        "Chemical industry": 0,
        "Non-metallic mineral products": 0,
        "Pulp, paper and printing": 0,
        "Food, beverages and tobacco": 4,
        "Transport equipment": 2,
        "Machinery equipment": 2,
        "Textiles and leather": 3,
        "Wood and wood products": 2,
        "Other industrial sectors": 4
    }
    dd = mo.ui.dropdown(options=list(sheet_name_dict.keys()),
                               value = list(sheet_name_dict.keys())[0])
    return dd, fit_grade_dict, sheet_name_dict


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### (1) Set the sector to evaluate. Not all sectors hold data for physical output.
    """)
    return


@app.cell
def _(dd, mo):
    mo.vstack([mo.hstack([dd, mo.md(f"Evaluating sector {dd.value}")])])
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### (2) There are predefined values for the regression grade. They can be adapted here.
    """)
    return


@app.cell
def _(dd, fit_grade_dict: dict[str, float], mo):
    if dd.value in ["Non-ferrous metals", "Chemical industry", "Non-metallic mineral products"]:
        raise Exception(f"DATA ERROR: no data of Physical output for sector {dd.value} available in JRC IDEE datasource.")
    else:
        fit_grade_slider = mo.ui.slider(
            start=0, stop=8, step=1,
            value=fit_grade_dict[dd.value],
            label="Grade for polynomial fit",
        )
    fit_grade_slider
    return (fit_grade_slider,)


@app.cell
def _(dd, fp, pd, sheet_name_dict: dict[str, str]):
    _df = pd.read_excel(fp, sheet_name=sheet_name_dict[dd.value], index_col=0, header=0)
    physical_output = next((x for x in _df.index if isinstance(x, str) and x.startswith("Physical output (")), None)
    df_filtered = _df.loc[["Value added (M€2023)", physical_output]]
    df_t = df_filtered.T
    return df_t, physical_output


@app.cell
def _(df_t, physical_output, px):
    px.scatter(df_t, x = "Value added (M€2023)", y = physical_output, title = "Comparison of Value added to Physical output")
    return


@app.cell
def _(df_t, fit_grade_slider, np, pd, physical_output):
    # perform regression on the data, grade set by fit_grade_slider
    _data = df_t[["Value added (M€2023)", physical_output]]
    _data = _data.apply(pd.to_numeric, errors = "coerce").dropna()
    _x = _data["Value added (M€2023)"]
    _y = _data[physical_output]
    coeffs = np.polyfit(_x, _y, deg=fit_grade_slider.value)
    poly = np.poly1d(coeffs)
    poly
    return (poly,)


@app.cell
def _(df_t, fit_grade_slider, go, np, pd, physical_output, poly, px):
    _x = df_t["Value added (M€2023)"].apply(pd.to_numeric, errors = "coerce").dropna()
    _x_line = np.linspace(_x.min(), _x.max(), 200)
    _y_line = poly(_x_line)

    _fig = px.scatter(df_t, x="Value added (M€2023)", y=physical_output, title="Comparison of value added to physical output with regression")
    _fig.add_trace(go.Scatter(x=_x_line, y=_y_line, mode="lines", name=f"Fit of grade {fit_grade_slider.value}"))
    _fig
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
