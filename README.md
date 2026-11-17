# TSFM forecasts of ILI and ARI in Europe

Zero-shot 1–4 week forecasts of weekly ILI and ARI incidence for the European countries, made with three
time-series foundation models:
- **Chronos-2**
- **TimesFM 2.5**
- **TabPFN-TS**

The data are ERVISS (EU/EEA) and WHO FluID (Switzerland and the UK regions), from season 2014/15. The models
follow [epi-tsfm](https://github.com/ngozzi/epi-tsfm) (wrappers adapted under the MIT license).

This repository only makes the data and the forecasts. The early warning system (MEM thresholds, onset, peak
and end) lives in [tsfms-master-thesis](https://github.com/anaparovic/tsfms-master-thesis) and reads
`target-data/processed/` and `model-output/` from here.

## Flow
```
ERVISS (pyerviss) + WHO FluID ── 1 ──> target-data/raw/ ──> target-data/processed/{ili,ari}.csv, *_season_info.csv
                                                                     │
                                                    ── 2 ──> model-output/<target>/<Model>_<version>/<date>-<Model>_<version>.csv
                                                                     │
                                                    ── 3 ──> figures/forecasts/
```

| # | Step | Script | Doc |
|---|---|---|---|
| 1 | Download and build the weekly data | `python code/data_import.py` (`--no-download`: only rebuild) | [docs/01_data.md](docs/01_data.md) |
| 2 | Retrospective forecasts of one model | `python code/backtest.py --model Chronos --target ILI` | [docs/02_models.md](docs/02_models.md) |
| 3 | Plots of the forecasts | `python code/plot_forecasts.py --seasons 2017/18 2024/25` | [docs/03_backtest.md](docs/03_backtest.md) |

`notebooks/data_exploration.ipynb` describes the raw data, `notebooks/data_preprocessing.ipynb` explains every
step of 1 with tables and before/after figures (set `TARGET = "ILI"` or `"ARI"`).

## Main choices (all settings in [config.yaml](config.yaml))
- **Season**: week 40 to week 20 of the next year; weeks 21-39 belong to no season.
- **COVID**: seasons 2020/21 and 2021/22 and the weeks 2020-W10 to W20 stay in the data (`covid`, `covid_week`).
- **Cleaning** (`value_clean`): spikes (more than 2x every week in the 4 weeks before and after) are capped at the
  highest of those weeks, dips (the mirror rule) are raised to the lowest, gaps of at most 2 weeks are interpolated.
  The original values are kept in `value`.
- **Model input**: `value_clean` up to the forecast date (its cleaning looks at the 4 weeks after each week), latest
  version of the data. `itpT`: all gaps interpolated, each location from its first week; `itpF`: gaps left as NaN
  (as epi-tsfm). A location needs the forecast week and at least 52 reported weeks.
- **Forecasts**: horizons 1–4, 23 quantiles, hub format (as epi-tsfm); every Sunday from week 36 to week 19 of the
  finished, non-COVID seasons from 2017/18.

## Setup
```bash
pip install -r requirements.txt                       # data, notebooks, plots (Python >= 3.10)
# models: Python 3.11, CPU torch first
uv venv --python 3.11 <venv>
uv pip install --python <venv> --index-url https://download.pytorch.org/whl/cpu torch==2.15.0
uv pip install --python <venv> -r requirements-models.txt
```
TabPFN-TS uses the Prior Labs API (`TABPFN_ACCESS_TOKEN`) or runs on CPU (`tabpfn_mode: local`).

## Later: weekly pipeline
The layout follows a weekly pipeline (as in TSFM-ensemble-influcast): `code/check_new_data.py` (new ERVISS week?),
`code/run_forecasts.py --week YYYY_WW` (only the latest week), `code/run_weekly.py` and
`.github/workflows/weekly-pipeline.yml` are still to be written. See [docs/README.md](docs/README.md).

## Structure
```
config.yaml              all settings
code/tsfm_europe/        package: download, preprocess, model input (data), model wrappers, common
code/                    scripts of the steps
notebooks/               data exploration and preprocessing, step by step
target-data/             raw and processed data
model-output/            forecasts
figures/, results/       figures and tables of the notebooks and plots
docs/                    one page per step
```
