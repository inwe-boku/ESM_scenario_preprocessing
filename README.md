![Python](https://img.shields.io/badge/python-3.14-blue)  [![license](https://img.shields.io/badge/License-MIT-blue)](https://github.com/maxnutz/pypsa_validation_processing/blob/master/LICENSE) [![pyam](https://img.shields.io/badge/pyam-iamc-blue)](https://github.com/IAMconsortium/pyam)

# ESM_scenario_preprocessing

Preprocesses scenario inputs from the NetZero 2040 project to serve as input for PyPSA-AT.

## Quick start from Zero
1. install pixi on your machine/laptop ([Complete Guide](https://pixi.prefix.dev/latest/installation/))
  ```bash
  curl -fsSL https://pixi.sh/install.sh | sh
  ```
2. restart your terminal
3. go to the project folder (there `pixi.toml` lives)
4. start the marimo notebook with
  ```bash
  pixi run marimo edit
  ```
5. a browser window will open, showing all available notebooks. If you are working on a server, you may have to open the browser-window by yourself, by copy-pasting the link displayed in the terminal. 

## Github collaboration
- You can't directly push on branch "main", as it is protected
- If you work on code, you want to push, create a branch (`git checkout -b <your branch name>`), add files, commit and push with `git push`.
- For merging into main, open a pull request online (Tab "Pull requests"). Sourcery will review your pull request automatically
## Requirements

- Python 3.10+
- pixi (recommended for environment management)

Core dependencies:

- pandas
- pyam-iamc
- marimo

## Installation of the package

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

- `pyproject.toml`: pip-installable package configuration and pixi environment/dependency configuration (`[tool.pixi.*]`)
- `src/esm_scenario_preprocessing/`: Python package source
- `resources/`: local input data folder (ignored by git)
- `sector-inputs/`: collection of marimo notebooks processing scenario input data 
