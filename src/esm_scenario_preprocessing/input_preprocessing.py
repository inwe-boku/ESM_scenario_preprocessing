"""Reusable preprocessing functions for scenario sector inputs."""

import math
from typing import Literal

import numpy as np
import pandas as pd
import pyam

TRANSPORT_SCENARIO_DEMAND_DICT: dict[str, list[str]] = {
    "High Demand": [
        "NetZero2040 high-import/high-demand base",
        "NetZero2040 low-import/high-demand base",
    ],
    "Low Demand": [
        "NetZero2040 high-import/low-demand base",
        "NetZero2040 low-import/low-demand base",
    ],
}

TRANSPORT_CAR_VARIABLES: list[str] = [
    "Stock|Cars|Passenger|Combustion",
    "Stock|Cars|Passenger|Electric",
    "Stock|Cars|Passenger|Fuel Cell",
]


def _loocv_mse(years: np.ndarray, values: np.ndarray, degree: int) -> float:
    """Leave-one-out cross-validation MSE for a polynomial fit of the given degree."""
    squared_errors = []
    for i in range(len(years)):
        train_years = np.delete(years, i)
        train_values = np.delete(values, i)
        coeffs = np.polyfit(train_years, train_values, degree)
        prediction = np.polyval(coeffs, years[i])
        squared_errors.append((prediction - values[i]) ** 2)
    return float(np.mean(squared_errors))


def _extrapolate_to_year(demand_factor: pd.Series, target_year: int) -> float:
    """Fit polynomials (degree 1-3) to `demand_factor`, pick the best by LOOCV, evaluate at `target_year`.

    Works for interpolation (`target_year` within the fitted range) as well as
    extrapolation (`target_year` beyond it).
    """
    years = demand_factor.index.to_numpy(dtype=float)
    values = demand_factor.to_numpy(dtype=float)
    cv_errors = {degree: _loocv_mse(years, values, degree) for degree in (1, 2, 3)}
    best_degree = min(cv_errors, key=cv_errors.get)
    coeffs = np.polyfit(years, values, best_degree)
    return float(np.polyval(coeffs, target_year))


def _interpolate_technology_fractions(
    fractions_start: pd.Series,
    fractions_end: pd.Series,
    year_start: int,
    year_end: int,
    target_year: int,
) -> pd.Series:
    """Linearly interpolate technology composition fractions between two known years."""
    weight = (target_year - year_start) / (year_end - year_start)
    return fractions_start * (1 - weight) + fractions_end * weight


def get_transport_sector_technology_shares(
    file_path: str, scenario: Literal["High Demand", "Low Demand"]
) -> pd.DataFrame:
    """Compute technology shares of the passenger car stock for a demand scenario.

    Filters passenger car stock (combustion/electric/fuel cell) for Austria from a
    pyam-valid IAMC scenario file, normalizes it against a fixed base year (2023) to
    get shares, and fits a polynomial (degree chosen by leave-one-out cross-validation)
    to the combined demand factor to interpolate 2035/2045 and extrapolate 2050. These
    technology shares then also include changes in demand factor if not summing up to 1.0.

    Inputs:
    ------
    file_path: str
        path to a pyam-valid IAMC-format scenario file.
    scenario: str
        demand scenario, one of "High Demand", "Low Demand".

    Returns:
    ------
    df_out: pd.DataFrame
        technology share of the passenger car stock for years 2025, 2030, 2035, 2040,
        2045, 2050 (5-year steps, as needed by PyPSA-AT), indexed by technology.

    Note:
    ----
    The returned technology shares will not sum up to 1.0 for a specific year, if the
    transport demand is not constant over time, relative to the base year (2003).
    Changes in transport demand are reflected in the total technology shares.
    """
    if scenario not in TRANSPORT_SCENARIO_DEMAND_DICT:
        raise ValueError(
            f"Unknown scenario {scenario!r}. Expected one of "
            f"{list(TRANSPORT_SCENARIO_DEMAND_DICT)}."
        )

    pdf = pyam.IamDataFrame(file_path)
    cars_absolute = pdf.filter(
        scenario=TRANSPORT_SCENARIO_DEMAND_DICT[scenario],
        variable=TRANSPORT_CAR_VARIABLES,
        region="Austria",
    ).pivot_table(index="variable", columns="year", values="value", aggfunc="mean")

    # Missing values mean the technology has zero stock in that year, not unknown data.
    cars_absolute_numeric = cars_absolute.apply(pd.to_numeric, errors="coerce").fillna(
        0
    )
    common_basis = cars_absolute_numeric.sum(axis=0, skipna=True).loc[2023]
    if math.isclose(common_basis, 0):
        raise ValueError("Comparison-variable 'common_basis' is near zero.")

    technology_shares = cars_absolute_numeric.div(common_basis, axis=1)
    technology_shares.index = [
        f"{variable} Share" for variable in technology_shares.index
    ]
    cars_absolute_with_shares = pd.concat([cars_absolute_numeric, technology_shares])

    demand_factor = cars_absolute_with_shares.filter(like="Share", axis=0)[
        [2021, 2023, 2030, 2040]
    ].sum(axis=0)
    demand_factor_at_new_years = {
        year: _extrapolate_to_year(demand_factor, year)
        for year in (2025, 2035, 2045, 2050)
    }

    technology_shares_by_year = cars_absolute_with_shares.filter(like="Share", axis=0)
    technology_fractions_2021 = (
        technology_shares_by_year[2021] / technology_shares_by_year[2021].sum()
    )
    technology_fractions_2030 = (
        technology_shares_by_year[2030] / technology_shares_by_year[2030].sum()
    )
    technology_fractions_2040 = (
        technology_shares_by_year[2040] / technology_shares_by_year[2040].sum()
    )
    # Composition beyond the last known year (2040) is assumed unchanged.
    technology_fractions_2050 = technology_fractions_2040

    technology_fractions_2025 = _interpolate_technology_fractions(
        technology_fractions_2021, technology_fractions_2030, 2021, 2030, 2025
    )
    technology_fractions_2035 = _interpolate_technology_fractions(
        technology_fractions_2030, technology_fractions_2040, 2030, 2040, 2035
    )
    technology_fractions_2045 = _interpolate_technology_fractions(
        technology_fractions_2040, technology_fractions_2050, 2040, 2050, 2045
    )

    for year, technology_fractions in (
        (2025, technology_fractions_2025),
        (2035, technology_fractions_2035),
        (2045, technology_fractions_2045),
        (2050, technology_fractions_2050),
    ):
        cars_absolute_with_shares.loc[technology_fractions.index, year] = (
            technology_fractions * demand_factor_at_new_years[year]
        )

    road_transport_scenario = cars_absolute_with_shares.filter(like="Share", axis=0)[
        [2025, 2030, 2035, 2040, 2045, 2050]
    ]
    road_transport_scenario.index = [
        name.removesuffix(" Share") for name in road_transport_scenario.index
    ]
    return road_transport_scenario
