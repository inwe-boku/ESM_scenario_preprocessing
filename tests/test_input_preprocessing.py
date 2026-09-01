import pandas as pd
import pyam
import pytest

from esm_scenario_preprocessing.input_preprocessing import (
    TRANSPORT_SCENARIO_DEMAND_DICT,
    _extrapolate_to_year,
    _interpolate_technology_fractions,
    get_transport_sector_technology_shares,
)


def test_extrapolate_to_year_extrapolates_linear_trend():
    demand_factor = pd.Series({2020: 1.0, 2030: 2.0, 2040: 3.0})

    assert _extrapolate_to_year(demand_factor, 2050) == pytest.approx(4.0)


def test_extrapolate_to_year_interpolates_within_known_range():
    demand_factor = pd.Series({2020: 1.0, 2030: 2.0, 2040: 3.0})

    assert _extrapolate_to_year(demand_factor, 2035) == pytest.approx(2.5)


def test_interpolate_technology_fractions_midpoint():
    fractions_start = pd.Series({"a": 0.6, "b": 0.4})
    fractions_end = pd.Series({"a": 0.4, "b": 0.6})

    result = _interpolate_technology_fractions(
        fractions_start, fractions_end, 2030, 2040, 2035
    )

    pd.testing.assert_series_equal(result, pd.Series({"a": 0.5, "b": 0.5}))


def test_interpolate_technology_fractions_at_start_year_matches_start():
    fractions_start = pd.Series({"a": 0.6, "b": 0.4})
    fractions_end = pd.Series({"a": 0.4, "b": 0.6})

    result = _interpolate_technology_fractions(
        fractions_start, fractions_end, 2030, 2040, 2030
    )

    pd.testing.assert_series_equal(result, fractions_start)


@pytest.fixture
def transport_iam_df() -> pyam.IamDataFrame:
    scenarios = TRANSPORT_SCENARIO_DEMAND_DICT["High Demand"]
    variables = {
        "Stock|Cars|Passenger|Combustion": {2021: 3.0, 2023: 2.8, 2030: 2.0, 2040: 1.0},
        "Stock|Cars|Passenger|Electric": {2021: 0.1, 2023: 0.3, 2030: 1.0, 2040: 2.0},
        "Stock|Cars|Passenger|Fuel Cell": {2021: 0.0, 2023: 0.0, 2030: 0.05, 2040: 0.1},
    }
    rows = [
        {
            "model": "m",
            "scenario": scenario,
            "region": "Austria",
            "variable": variable,
            "unit": "million",
            "year": year,
            "value": value,
        }
        for scenario in scenarios
        for variable, year_values in variables.items()
        for year, value in year_values.items()
    ]
    return pyam.IamDataFrame(pd.DataFrame(rows))


def test_get_transport_sector_technology_shares_returns_5_year_steps(
    tmp_path, transport_iam_df
):
    file_path = tmp_path / "scenario.xlsx"
    transport_iam_df.to_excel(str(file_path))

    result = get_transport_sector_technology_shares(str(file_path), "High Demand")

    assert list(result.columns) == [2025, 2030, 2035, 2040, 2045, 2050]


def test_get_transport_sector_technology_shares_rejects_unknown_scenario(
    tmp_path, transport_iam_df
):
    file_path = tmp_path / "scenario.xlsx"
    transport_iam_df.to_excel(str(file_path))

    with pytest.raises(ValueError, match="Unknown scenario"):
        get_transport_sector_technology_shares(str(file_path), "Medium Demand")


def test_get_transport_sector_technology_shares_treats_missing_values_as_zero(
    tmp_path,
):
    # Fuel Cell has no data point in 2040 (i.e. zero stock), not unknown data.
    scenarios = TRANSPORT_SCENARIO_DEMAND_DICT["High Demand"]
    variables = {
        "Stock|Cars|Passenger|Combustion": {2021: 3.0, 2023: 2.8, 2030: 2.0, 2040: 1.0},
        "Stock|Cars|Passenger|Electric": {2021: 0.1, 2023: 0.3, 2030: 1.0, 2040: 2.0},
        "Stock|Cars|Passenger|Fuel Cell": {2021: 0.0, 2023: 0.0, 2030: 0.05},
    }
    rows = [
        {
            "model": "m",
            "scenario": scenario,
            "region": "Austria",
            "variable": variable,
            "unit": "million",
            "year": year,
            "value": value,
        }
        for scenario in scenarios
        for variable, year_values in variables.items()
        for year, value in year_values.items()
    ]
    file_path = tmp_path / "scenario.xlsx"
    pyam.IamDataFrame(pd.DataFrame(rows)).to_excel(str(file_path))

    result = get_transport_sector_technology_shares(str(file_path), "High Demand")

    assert not result.loc["Stock|Cars|Passenger|Fuel Cell"].isna().any()
    assert not result.loc["Stock|Cars|Passenger|Combustion"].isna().any()
