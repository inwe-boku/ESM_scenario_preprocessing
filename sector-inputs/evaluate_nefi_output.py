import marimo

__generated_with = "0.23.16"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    import pandas as pd
    import plotly.express as px
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    return go, make_subplots, mo, pd, px


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    # Evaluation of the NEFI output file

    Evaluates `resources/NEFI_v3_energy_by_carrier_long.xlsx` (output of `repair_nefi` - python-AI-Pipeline).
    Choose the evaluation, scenario and industry sector below.

    - **(a) data**: total final energy input and energy input per carrier (TWh)
    - **(b) economy**: GDP formation (bn EUR) and material output per product (Mt, Bricks in m3)
    """)
    return


@app.cell
def _(mo, pd):
    nefi_file = (
        mo.notebook_dir().parent / "resources" / "NEFI_v3_energy_by_carrier_long.xlsx"
    )
    sheets = pd.read_excel(nefi_file, sheet_name=["data", "economy"])
    energy = sheets["data"]
    economy = sheets["economy"]
    return economy, energy


@app.cell(hide_code=True)
def _(energy, mo):
    evaluation = mo.ui.radio(
        options={"(a) data": "data", "(b) economy": "economy"},
        value="(a) data",
        label="Choose the Evaluation parameters",
    )
    scenario = mo.ui.dropdown(
        options=sorted(energy["scenario"].unique()),
        value=min(energy["scenario"].unique()),
        label="Scenario",
    )
    sector = mo.ui.dropdown(
        options=list(energy["sector"].unique()),
        value=energy["sector"].iloc[0],
        label="Sector",
    )
    mo.hstack([evaluation, scenario, sector], justify="start", gap=2)
    return evaluation, scenario, sector


@app.cell(hide_code=True)
def _(economy, energy, evaluation, scenario, sector):
    source = energy if evaluation.value == "data" else economy
    selection = source[
        (source["scenario"] == scenario.value) & (source["sector"] == sector.value)
    ]
    return (selection,)


@app.cell(hide_code=True)
def _(go, pd, px, scenario, sector):
    def plot_data(selection: pd.DataFrame) -> list[go.Figure]:
        """Total energy input (line) and energy input per carrier (stacked area)."""
        title = f"{sector.value} – {scenario.value}"
        total = selection.groupby("year", as_index=False)["value"].sum()
        fig_total = px.line(
            total,
            x="year",
            y="value",
            markers=True,
            title=f"Total final energy input: {title}",
            labels={"value": "TWh", "year": "Year"},
        )
        fig_carrier = px.area(
            selection.sort_values("year"),
            x="year",
            y="value",
            color="carrier",
            title=f"Final energy input per carrier: {title}",
            labels={"value": "TWh", "year": "Year", "carrier": "Carrier"},
        )
        return [fig_total, fig_carrier]

    return (plot_data,)


@app.cell(hide_code=True)
def _(go, make_subplots, pd, px, scenario, sector):
    def plot_economy(selection: pd.DataFrame) -> list[go.Figure]:
        """GDP formation (line) and material output per product (lines)."""
        title = f"{sector.value} – {scenario.value}"
        gdp = selection[selection["variable"].str.contains("GDP formation")]
        fig_gdp = px.line(
            gdp,
            x="year",
            y="value",
            markers=True,
            title=f"GDP formation: {title}",
            labels={"value": "bn EUR", "year": "Year"},
        )
        material = selection[
            selection["variable"].str.contains("Material Output")
        ].dropna(subset=["value"])
        if material.empty:
            return [fig_gdp]

        # products without a sub-product carry the sector name
        material = material.assign(
            product=material["product"].fillna(material["sector"])
        )
        # most frequent unit on the primary axis, a second one (Bricks: m3) on the right
        units = list(material["unit"].value_counts().index)
        fig_material = make_subplots(specs=[[{"secondary_y": len(units) > 1}]])
        for (product, unit), group in material.groupby(["product", "unit"]):
            fig_material.add_trace(
                go.Scatter(
                    x=group["year"],
                    y=group["value"],
                    mode="lines+markers",
                    name=f"{product} [{unit}]",
                ),
                secondary_y=len(units) > 1 and unit == units[1],
            )
        fig_material.update_layout(title=f"Material output: {title}")
        fig_material.update_xaxes(title_text="Year")
        fig_material.update_yaxes(title_text=units[0], secondary_y=False)
        if len(units) > 1:
            fig_material.update_yaxes(title_text=units[1], secondary_y=True)
        return [fig_gdp, fig_material]

    return (plot_economy,)


@app.cell
def _(evaluation, mo, plot_data, plot_economy, selection):
    if evaluation.value == "data":
        figures = plot_data(selection)
        note = None
    else:
        figures = plot_economy(selection)
        note = (
            mo.callout(
                mo.md("No produced goods (material output) for this sector."),
                kind="info",
            )
            if len(figures) == 1
            else None
        )
    mo.vstack(
        [*figures, *([note] if note else []), mo.ui.table(selection, selection=None)]
    )
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
