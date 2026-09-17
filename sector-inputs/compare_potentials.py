import marimo

__generated_with = "0.24.0"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    import pypsa
    import pandas as pd 
    import plotly.express as px
    import json

    return json, mo, pd, px, pypsa


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Compare local potential data to basic ERA5 input
    """)
    return


@app.cell
def _(pypsa):
    base_folder = "resources/flos_potential/"
    local_potentials_folder = base_folder + "at_klien_technical_potentials/networks/"
    general_potentials_folder = base_folder + "at_general_potentials/networks/"

    filename = "base_s_adm__none_2050_final.nc"
    local_n = pypsa.Network(local_potentials_folder + filename)
    general_n = pypsa.Network(general_potentials_folder + filename)
    return general_n, local_n


@app.cell
def _(general_n, local_n, pd):
    combined = pd.concat(
        [
            local_n.generators.query("carrier == 'onwind' and bus.str.startswith('AT')").groupby("bus").p_nom_max.sum().rename("local_p_nom_max"),
            general_n.generators.query("carrier == 'onwind' and bus.str.startswith('AT')").groupby("bus").p_nom_max.sum().rename("general_p_nom_max")
        ],
        axis = 1
    )
    return (combined,)


@app.cell
def _(combined):
    combined["difference [((general - local) / local) * 100]"] = ((combined["general_p_nom_max"] - combined["local_p_nom_max"])  / combined["local_p_nom_max"]) * 100
    return


@app.cell
def _(combined):
    combined
    return


@app.cell
def _(combined):
    combined["difference [((general - local) / local) * 100]"].describe()
    return


@app.cell
def _(combined, json, px):
    with open("resources/flos_potential/regions_onshore_base_s_adm.geojson") as f:
        regions_geojson = json.load(f)

    diff_col = "difference [((general - local) / local) * 100]"
    max_abs_diff = combined[diff_col].abs().max()

    fig = px.choropleth_map(
        combined.reset_index(),
        geojson=regions_geojson,
        locations="bus",
        featureidkey="properties.name",
        color=diff_col,
        color_continuous_scale="RdBu",
        color_continuous_midpoint=0,
        range_color=(-max_abs_diff, max_abs_diff),
        map_style="outdoors",
        zoom=5.5,
        center={"lat": 47.5, "lon": 14.2},
        opacity=0.75,
        hover_name="bus",
        hover_data=[
            "local_p_nom_max",
            "general_p_nom_max",
            diff_col,
        ],
        title="Difference in p_nom_max (Technical potential)",
    )
    fig.write_html("geographic_comparison_technical_p_max_pu.html")
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
