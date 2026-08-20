import marimo

__generated_with = "0.23.16"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    import pypsa
    import pandas as pd 
    import plotly.express as px

    return mo, pd, px, pypsa


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Compare local potential data to basic ERA5 input
    """)
    return


@app.cell
def _(pypsa):
    base_folder = "resources/flos_potential/"
    local_potentials_folder = base_folder + "at_klien_potentials/networks/"
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
    combined["difference [local - general]"] = combined["local_p_nom_max"] - combined["general_p_nom_max"]
    return


@app.cell
def _(combined):
    combined["difference [local - general]"]
    return


@app.cell
def _(combined, px):
    import json

    with open("resources/flos_potential/regions_onshore_base_s_adm.geojson") as f:
        regions_geojson = json.load(f)

    fig = px.choropleth_map(
        combined.reset_index(),
        geojson=regions_geojson,
        locations="bus",
        featureidkey="properties.name",
        color="difference [local - general]",
        color_continuous_scale="RdBu",
        color_continuous_midpoint=0,
        map_style="outdoors",
        zoom=5.5,
        center={"lat": 47.5, "lon": 14.2},
        opacity=0.75,
    )
    fig.write_html("geographic_comparison_p_max_pu.html")
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
