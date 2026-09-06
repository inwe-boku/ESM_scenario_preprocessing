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
    **This notebook gives an idea of how to estimate the energy input per industry output using different sources:**

    **(a)** using JRC-IDEES - data for Austria showing the relationship between Added Value and Physical output from historical data. Using this data source, regression estimates are shown.

    **(b)** using the reported products output of the NEFI-update from 2026-08-30
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Energy input per industry output using JRC-IDEES - data for Austria
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
    # map the NEFI sectors (keys) to the sheet name of the corresponding JRC sectors
    sheet_name_dict: dict[str, str] = {
        "IronSteel": "ISI",  # "Iron and steel"
        "NonFerrousMetals": "NFM",  # "Non-ferrous metals"
        "Chemical": "CHI",  # "Chemical industry"
        "NonMetalicMinerals": "NMM",  # "Non-metallic mineral products"
        "PulpPaper": "PPA",  # "Pulp, paper and printing"
        "FoodAndBeverages": "FBT",  # "Food, beverages and tobacco"
        "Transport equipment": "TRE",
        "Machinery": "MAE",  # "Machinery equipment"
        "Textiles": "TEL",  # "Textiles and leather"
        "Wood": "WWP",  # "Wood and wood products"
        "NonSpecifiedIndustry": "OIS",  # "Other industrial sectors"
        "Construction": "ISI",  # "Iron and steel"
        "Mining": "OIS",  # "Other industrial sectors"
    }
    # map the regression grade to the corresponding NEFI sectors
    fit_grade_dict: dict[str, float] = {
        "IronSteel": 3,
        "NonFerrousMetals": 2,
        "Chemical": 0,
        "NonMetalicMinerals": 0,
        "PulpPaper": 0,
        "FoodAndBeverages": 4,
        "Transport equipment": 2,
        "Machinery": 2,
        "Textiles": 3,
        "Wood": 2,
        "NonSpecifiedIndustry": 4,
        "Construction": 3,
        "Mining": 4,
    }

    # original mapping of JRC sectors to their JRC-IDEES sheet name
    jrc_sector_to_sheet_name_dict: dict[str, str] = {
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
        "Other industrial sectors": "OIS",
    }

    # map the NEFI sectors to their corresponding JRC sector
    nefi_sector_to_jrc_sector_dict: dict[str, str] = {
        "IronSteel": "Iron and steel",
        "NonFerrousMetals": "Non-ferrous metals",
        "Chemical": "Chemical industry",
        "NonMetalicMinerals": "Non-metallic mineral products",
        "PulpPaper": "Pulp, paper and printing",
        "FoodAndBeverages": "Food, beverages and tobacco",
        "Transport equipment": "Transport equipment",
        "Machinery": "Machinery equipment",
        "Textiles": "Textiles and leather",
        "Wood": "Wood and wood products",
        "NonSpecifiedIndustry": "Other industrial sectors",
        "Construction": "Iron and steel",
        "Mining": "Other industrial sectors",
    }

    dd = mo.ui.dropdown(
        options=list(sheet_name_dict.keys()), value=list(sheet_name_dict.keys())[0]
    )
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
    if dd.value in [
        "Non-ferrous metals",
        "Chemical industry",
        "Non-metallic mineral products",
    ]:
        raise Exception(
            f"DATA ERROR: no data of Physical output for sector {dd.value} available in JRC IDEE datasource."
        )
    else:
        fit_grade_slider = mo.ui.slider(
            start=0,
            stop=8,
            step=1,
            value=fit_grade_dict[dd.value],
            label="Grade for polynomial fit",
        )
    fit_grade_slider
    return (fit_grade_slider,)


@app.cell
def _(dd, fp, pd, sheet_name_dict: dict[str, str]):
    _df = pd.read_excel(fp, sheet_name=sheet_name_dict[dd.value], index_col=0, header=0)
    physical_output = next(
        (
            x
            for x in _df.index
            if isinstance(x, str) and x.startswith("Physical output (")
        ),
        None,
    )
    df_filtered = _df.loc[["Value added (M€2023)", physical_output]]
    df_t = df_filtered.T
    return df_t, physical_output


@app.cell
def _(df_t, physical_output, px):
    px.scatter(
        df_t,
        x="Value added (M€2023)",
        y=physical_output,
        title="Comparison of Value added to Physical output",
    )
    return


@app.cell
def _(df_t, fit_grade_slider, np, pd, physical_output):
    # perform regression on the data, grade set by fit_grade_slider
    _data = df_t[["Value added (M€2023)", physical_output]]
    _data = _data.apply(pd.to_numeric, errors="coerce").dropna()
    _x = _data["Value added (M€2023)"]
    _y = _data[physical_output]
    coeffs = np.polyfit(_x, _y, deg=fit_grade_slider.value)
    poly = np.poly1d(coeffs)
    poly
    return (poly,)


@app.cell
def _(df_t, fit_grade_slider, go, np, pd, physical_output, poly, px):
    _x = df_t["Value added (M€2023)"].apply(pd.to_numeric, errors="coerce").dropna()
    _x_line = np.linspace(_x.min(), _x.max(), 200)
    _y_line = poly(_x_line)

    _fig = px.scatter(
        df_t,
        x="Value added (M€2023)",
        y=physical_output,
        title="Comparison of value added to physical output with regression",
    )
    _fig.add_trace(
        go.Scatter(
            x=_x_line,
            y=_y_line,
            mode="lines",
            name=f"Fit of grade {fit_grade_slider.value}",
        )
    )
    _fig
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ---
    ## Energy input per industry output using NEFI industry outputs
    """)
    return


@app.cell
def _(pd):
    ind_output = pd.read_excel(
        "resources/v3-ProducedGoods_harmonized.xlsx", sheet_name="Scenario1"
    )
    ind_output = ind_output.set_index("Product")
    return (ind_output,)


@app.cell
def _():
    # Products from ind_output["Product"] not attached to any sector above (kept
    # here for reference, not fed into energy-input-per-output calc):
    # - "of which imported as HB-DRI": import-share breakdown of "Iron & Steel, primary"
    # - "domestic production" / "of which imported clinker": breakdown rows of
    #   "Cement production (50% imported clinker from 2040 on)"
    # - "of which from Methanol": feedstock-share breakdown of "Olefine domestic production"
    # - "Methanol DEMAND" / "Methanol imports": demand/import figures, not domestic production
    # - "Wood imports": import figure, not domestic production
    # - "H2 dom. Prod.": hydrogen production has no matching sector in this list
    product_to_sector_dict: dict[str, list[str]] = {
        "IronSteel": ["Iron & Steel, primary", "Steel secondary (EAF)"],  # Mtsteel/a
        "Chemical": [
            "Ammonia dom. Prod.",
            "Nitric acid dom. Prod.",
            "Methanol dom. Prod.",
            "Olefine domestic production",
            "Soda Ash dom. Prod.",
        ],
        "PulpPaper": ["Pulp prod. Dom."],
        "NonMetalicMinerals": [
            "Cement production (50% imported clinker from 2040 on)",
            "Lime dom. Prod.",
            "Glass dom. Prod.",
            "Bricks dom. Prod.",
            "Limestone & Dolomit dom.prod.",
        ],
        "Machinery": [],
        "TransportEquipment": [],
        "NonFerrousMetals": ["Al dom. Secondary prod."],
        "FoodAndBeverages": [],
        "Wood": [],
        "Textiles": [],
        "NonSpecifiedIndustry": [],
        "Construction": [],
        "Mining": [],
    }
    return (product_to_sector_dict,)


@app.cell
def _(ind_output, product_to_sector_dict: dict[str, list[str]]):
    ind_output_t = ind_output.select_dtypes(include="number").T
    for sector, products in product_to_sector_dict.items():
        ind_output_t[sector] = ind_output_t[products].sum(axis=1)

    return (ind_output_t,)


@app.cell
def _(ind_output_t, product_to_sector_dict: dict[str, list[str]]):
    # units need to be checked, so that only parts of the same unit are summed together.
    ind_output_t[list(product_to_sector_dict.keys())].T
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
