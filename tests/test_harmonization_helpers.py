import pandas as pd
import pytest

from esm_scenario_preprocessing.harmonization_helpers import (
    energy_inputs_harmonization,
    nefi_energy_by_pypsa_carrier,
    nefi_to_pypsa_inputs_dict,
)


@pytest.fixture
def nefi_df() -> pd.DataFrame:
    """Minimal NEFI input df: one row per raw NEFI material, one column per year."""
    index = [
        "Electricity",
        "Electricity for HPs",
        "Coal",
        "Biofuels",
        "Gas",
        "Biogas",
        "Synth-CH4",
        "Hydrogen, H2",
        "District Heating",
        "Solar thermal",
        "Oil",
    ]
    data = {2020: range(len(index)), 2030: range(10, 10 + len(index))}
    return pd.DataFrame(data, index=index)


def test_energy_inputs_harmonization_sums_grouped_materials(nefi_df):
    result = energy_inputs_harmonization(nefi_df)

    expected_elec = nefi_df.loc["Electricity"] + nefi_df.loc["Electricity for HPs"]
    expected_heat = nefi_df.loc["District Heating"] + nefi_df.loc["Solar thermal"]

    pd.testing.assert_series_equal(
        result.loc["elec"], expected_elec, check_names=False, check_dtype=False
    )
    pd.testing.assert_series_equal(
        result.loc["heat"], expected_heat, check_names=False, check_dtype=False
    )


def test_energy_inputs_harmonization_passes_through_single_source_materials(nefi_df):
    result = energy_inputs_harmonization(nefi_df)

    pd.testing.assert_series_equal(
        result.loc["coal and coke"],
        nefi_df.loc["Coal"],
        check_names=False,
        check_dtype=False,
    )
    pd.testing.assert_series_equal(
        result.loc["biomass"],
        nefi_df.loc["Biofuels"],
        check_names=False,
        check_dtype=False,
    )
    pd.testing.assert_series_equal(
        result.loc["naphtha"], nefi_df.loc["Oil"], check_names=False, check_dtype=False
    )


def test_energy_inputs_harmonization_zero_for_materials_without_nefi_source(nefi_df):
    result = energy_inputs_harmonization(nefi_df)

    assert (result.loc["ammonia"] == 0).all()
    assert (result.loc["methanol"] == 0).all()


def test_energy_inputs_harmonization_output_index_matches_pypsa_materials(nefi_df):
    result = energy_inputs_harmonization(nefi_df)

    assert sorted(result.index) == sorted(nefi_to_pypsa_inputs_dict.keys())


def test_energy_inputs_harmonization_does_not_mutate_input(nefi_df):
    original = nefi_df.copy(deep=True)

    energy_inputs_harmonization(nefi_df)

    pd.testing.assert_frame_equal(nefi_df, original)


@pytest.fixture
def nefi_long_df() -> pd.DataFrame:
    """Minimal long-format NEFI `data` sheet: 2 scenarios x 2 sectors x 4 carriers."""
    rows = []
    for scenario_offset, scenario in enumerate(["Scenario1", "Scenario2a"]):
        for sector_offset, sector in enumerate(["IronSteel", "Chemical"]):
            for carrier in ["Electricity", "ElectricityHP", "GasGridMix", "Hydrogen"]:
                for year in (2025, 2050):
                    value = 1.0 + 10 * sector_offset + 100 * scenario_offset
                    rows.append((scenario, sector, carrier, "TWh", year, value))
    return pd.DataFrame(
        rows, columns=["scenario", "sector", "carrier", "unit", "year", "value"]
    )


def test_nefi_energy_by_pypsa_carrier_single_sector(nefi_long_df):
    result = nefi_energy_by_pypsa_carrier(nefi_long_df, "Scenario1", ["Chemical"])

    assert list(result.columns) == [2025, 2050]
    assert (result.loc["elec"] == 22.0).all()  # Electricity + ElectricityHP
    assert (result.loc["methane"] == 11.0).all()
    assert (result.loc["hydrogen"] == 11.0).all()
    assert (result.loc["coal and coke"] == 0).all()


def test_nefi_energy_by_pypsa_carrier_sums_all_sectors_by_default(nefi_long_df):
    result = nefi_energy_by_pypsa_carrier(nefi_long_df, "Scenario2a")

    assert (result.loc["hydrogen"] == 101.0 + 111.0).all()


def test_nefi_energy_by_pypsa_carrier_drops_non_carrier_rows(nefi_long_df):
    result = nefi_energy_by_pypsa_carrier(nefi_long_df, "Scenario1")

    assert "Total" not in result.index
    assert "losses" not in result.index


@pytest.mark.parametrize(
    "scenario, sectors", [("Scenario3", None), ("Scenario1", ["AllManuf"])]
)
def test_nefi_energy_by_pypsa_carrier_rejects_unknown_selection(
    nefi_long_df, scenario, sectors
):
    with pytest.raises(ValueError, match="Unknown"):
        nefi_energy_by_pypsa_carrier(nefi_long_df, scenario, sectors)
