# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Purpose

Preprocesses scenario inputs from the NetZero 2040 project (`pyam`/IAMC-formatted data) to serve as input for PyPSA-AT.

## Development

- Use `pixi run <command>` (per project convention). Environment/dependencies are declared in `pyproject.toml` under `[tool.pixi.*]` and `[project.dependencies]`.
- `pixi install` / `pixi shell` to set up and enter the environment (see README.md).
- Tests use `pytest` and live in `tests/`, mirroring `src/esm_scenario_preprocessing/`. Run them with `pixi run test` (or `pixi run pytest`).
- use `ruff` as python linter and code formatter.
- Put local input data in `resources/` (gitignored, except `.gitkeep`).

## Architecture

- `src/esm_scenario_preprocessing/` is a pip-installable package (`src/` layout, built via setuptools) but currently only contains a placeholder `__init__.py` — no processing logic lives here yet.
- The actual scenario-preprocessing logic lives in **marimo notebooks** (`.py` files using `marimo.App` / `@app.cell`), not in the package:
  - `nefi-inputs.py` (repo root) — currently a stub.
  - `sector-inputs/transport_sector.py` — computes technology shares (combustion/electric/fuel-cell) of the passenger car stock from a `pyam.IamDataFrame` loaded out of `resources/netzero2040-times-pyam.xlsx`. The pattern used here (filter scenarios/variables/region → pivot to a `variable` x `year` table → normalize against a fixed base year to get shares) is representative of how other sector notebooks are expected to work.
  - Run/edit notebooks with `pixi run marimo edit <path>.py` (or `marimo run <path>.py` to execute non-interactively).
- Input data is IAMC-format scenario data (`pyam`, `nomenclature-iamc`) — variables/scenarios/regions are filtered via `pyam.IamDataFrame.filter(...)`, and typically pivoted with pandas for year-over-year comparisons.
- `resources/pypsa_industry_files/` holds sector-specific CSV inputs (e.g. industry production and sector ratios per year) consumed by these notebooks; expect similar per-sector resource subfolders as more notebooks are added.
