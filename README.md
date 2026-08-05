# ESM_scenario_preprocessing

Preprocesses scenario inputs from the NetZero 2040 project to serve as input for PyPSA-AT.

## Requirements

- Python 3.10+
- pixi (recommended for environment management)

Core dependencies:

- pandas
- pyam-iamc
- marimo

## Installation

### With pip

```bash
python -m pip install -e .
```

### With pixi

```bash
pixi install
pixi shell
```

## Project structure

- `pyproject.toml`: pip-installable package configuration
- `pixi.toml`: pixi environment/dependency configuration
- `src/esm_scenario_preprocessing/`: Python package source
- `resources/`: local input data folder (ignored by git)
