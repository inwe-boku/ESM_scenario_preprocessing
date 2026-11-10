"""Helpers to harmonize NEFI inputs with PyPSA-AT inputs."""

import pandas as pd

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
