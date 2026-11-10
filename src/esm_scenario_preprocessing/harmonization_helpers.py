"""Helpers to harmonize NEFI inputs with PyPSA-AT inputs."""

import pandas as pd
import pyam

nefi_to_pypsa_inputs_dict: dict[str, list[str]] = {
    "elec": [
        "Electricity",
        "Electricity for HPs",
        "El. for Heat Pumps",
        "El. for H2",
        "ElectricityHP",
    ],
    "coal and coke": ["Coal"],  # combines coal and coke in pypsa-at
    "biomass": ["Biofuels"],
    "methane": [
        "Gas",
        "Biogas",
        "Synth-CH4",
        "Gas grid mix",
        "Natural gas, Bio-CH4 and Syn-CH4",
        "Bio-CH4",
        "CH4",
        "Gas grid ix",
        "GasGridMix",
    ],
    "hydrogen": ["Hydrogen, H2", "Hydrogen", "H2"],
    "heat": ["District Heating", "Solar thermal", "DistrictHeating", "SolarThermal"],
    "naphtha": ["Oil", "Chem. Ind. Foss. Rohstoffe (ölbasiert)"],
    "ammonia": [],
    "methanol": [],
    "waste": ["Waste"],
    "losses": ["Transformation losses H2"],
    "Total": ["Total", "Total Energy", "Total energy", "actual total"],
}

nefi_sector_iamc_labels: dict[str, str] = {
    "IronSteel": "Iron and Steel",
    "Chemical": "Chemicals",
    "PulpPaper": "Pulp and Paper",
    "NonMetalicMinerals": "Non-Metallic Minerals",
    "Machinery": "Machinery",
    "NonFerrousMetals": "Non-Ferrous Metals",
    "TransportEquipment": "Transport Equipment",
    "FoodAndBeverages": "Food and Beverages",
    "Wood": "Wood",
    "Textiles": "Textiles",
    "NonSpecifiedIndustry": "Non-Specified",
    "Construction": "Construction",
    "Mining": "Mining",
}

pypsa_carrier_iamc_labels: dict[str, str] = {
    "elec": "Electricity",
    "coal and coke": "Coal and Coke",
    "biomass": "Biomass",
    "methane": "Methane",
    "hydrogen": "Hydrogen",
    "heat": "Heat",
    "naphtha": "Naphtha",
    "ammonia": "Ammonia",
    "methanol": "Methanol",
    "waste": "Waste",
}

pypsa_combinations_for_nefi_inputs_dict: dict[str, list[str]] = {
    "coal and coke": ["coal", "coke"]
}


def energy_inputs_harmonization(df_in: pd.DataFrame) -> pd.DataFrame:
    """Harmonizes NEFI - Energy inputs to the pypsa - Energy inputs.

    Inputs:
    ------
    df_in: pd.DataFrame
        pandas dataframe with NEFI inputs to be manipulated

    Returns:
    ------
    df_out: pd.DataFrame
        pandas dataframe with manipulated NEFI inputs.

    Note:
    ----
    only performs manipulation on NEFI dataframe df_in"""

    nefi_fe_t = df_in.T
    for _pypsa_material, _nefi_material in nefi_to_pypsa_inputs_dict.items():
        _available = [col for col in _nefi_material if col in nefi_fe_t.columns]
        nefi_fe_t[_pypsa_material] = nefi_fe_t[_available].sum(
            axis=1, numeric_only=False
        )
        nefi_fe_t = nefi_fe_t.drop(_available, axis=1)
    df_out = nefi_fe_t.T
    return df_out


def nefi_energy_by_pypsa_carrier(
    energy: pd.DataFrame, scenario: str, sectors: list[str] | None = None
) -> pd.DataFrame:
    """Select NEFI long-format energy data and harmonize it to PyPSA carriers.

    Inputs:
    ------
    energy: pd.DataFrame
        sheet `data` of `NEFI_v3_energy_by_carrier_long.xlsx` (columns `scenario`,
        `sector`, `carrier`, `year`, `value`; unit TWh).
    scenario: str
        NEFI scenario, e.g. "Scenario1" or "Scenario2a".
    sectors: list[str] | None
        sectors to sum up; None sums all sectors (all manufacturing industries).

    Returns:
    ------
    df_out: pd.DataFrame
        energy input in TWh, indexed by PyPSA carrier, one column per year.
        The non-carrier rows "Total" and "losses" are not included.
    """
    for column, requested in (("scenario", [scenario]), ("sector", sectors or [])):
        unknown = sorted(set(requested) - set(energy[column]))
        if unknown:
            raise ValueError(f"Unknown {column}(s) {unknown} in NEFI energy data.")

    selection = energy[energy["scenario"] == scenario]
    if sectors is not None:
        selection = selection[selection["sector"].isin(sectors)]
    wide = selection.pivot_table(
        index="carrier", columns="year", values="value", aggfunc="sum"
    )
    wide.columns.name = None
    df_out = energy_inputs_harmonization(wide)
    return df_out.drop(["Total", "losses"], axis=0)


def nefi_energy_to_iamc(
    energy: pd.DataFrame, model: str = "NEFI", region: str = "Austria"
) -> pyam.IamDataFrame:
    """Convert NEFI long-format energy data to IAMC format, harmonized to PyPSA carriers.

    Every scenario/sector is processed with `nefi_energy_by_pypsa_carrier`, so the
    result contains the same carrier mapping (e.g. Electricity + ElectricityHP summed
    to Electricity) as the evaluation notebook.

    Inputs:
    ------
    energy: pd.DataFrame
        sheet `data` of `NEFI_v3_energy_by_carrier_long.xlsx` (unit TWh).
    model: str
        IAMC model name.
    region: str
        IAMC region name.

    Returns:
    ------
    df_out: pyam.IamDataFrame
        one variable `Demand|Industry|<sector>|<carrier>` per sector and PyPSA
        carrier, unit TWh/yr. No sector or carrier totals.
    """
    unknown = sorted(set(energy["sector"]) - set(nefi_sector_iamc_labels))
    if unknown:
        raise ValueError(f"No IAMC label for NEFI sector(s) {unknown}.")

    frames = []
    for scenario in energy["scenario"].unique():
        for sector in energy["sector"].unique():
            wide = nefi_energy_by_pypsa_carrier(energy, scenario, [sector])
            long = wide.rename_axis("carrier").reset_index()
            long = long.melt(id_vars="carrier", var_name="year", value_name="value")
            long["scenario"] = scenario
            long["sector"] = sector
            frames.append(long)
    data = pd.concat(frames, ignore_index=True)

    carriers = data["carrier"].map(pypsa_carrier_iamc_labels)
    if carriers.isna().any():
        missing = sorted(data.loc[carriers.isna(), "carrier"].unique())
        raise ValueError(f"No IAMC label for PyPSA carrier(s) {missing}.")
    sectors = data["sector"].map(nefi_sector_iamc_labels)
    data["variable"] = "Demand|Industry|" + sectors + "|" + carriers
    data = data.assign(model=model, region=region, unit="TWh/yr")
    return pyam.IamDataFrame(
        data[["model", "scenario", "region", "variable", "unit", "year", "value"]]
    )
