import pandas as pd
import pytest

from esm_scenario_preprocessing.harmonization_helpers import (
    energy_inputs_harmonization,
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
