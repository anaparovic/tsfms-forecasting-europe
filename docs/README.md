# Pipeline documentation

| # | Step | Doc | Script |
|---|---|---|---|
| 1 | Download and build the weekly data | [01_data.md](01_data.md) | `code/data_import.py` |
| 2 | Run the models | [02_models.md](02_models.md) | `code/backtest.py` |
| 3 | Retrospective forecasts and plots | [03_backtest.md](03_backtest.md) | `code/backtest.py`, `code/plot_forecasts.py` |

## Code layout
| File | Role |
|---|---|
| `config.yaml` | all settings: targets, models, versions, seasons, COVID, FluID locations, cleaning, forecast dates |
| `code/tsfm_europe/common.py` | horizons, quantiles, output format, input checks, `load_config` |
| `code/tsfm_europe/download.py` | ERVISS (pyerviss) and WHO downloads |
| `code/tsfm_europe/preprocess.py` | weekly data of all locations and `value_clean` |
| `code/tsfm_europe/data.py` | model input at a forecast date, seasons and forecast dates of the backtest |
| `code/tsfm_europe/{chronos,timesfm,tabpfnts}_model.py` | model wrappers (from epi-tsfm) |

## Still to do: weekly pipeline
1. `code/check_new_data.py`: is there a new ERVISS week that has no forecast yet?
2. `code/run_forecasts.py --week YYYY_WW`: forecasts of the latest week only; `code/run_weekly.py`: all steps.
3. Data snapshots per week (`target-data/processed/YYYY_WW_<target>.csv`): the data as known that week
   (revisions), for an honest backtest.
4. `.github/workflows/weekly-pipeline.yml`: schedule → data → 3 models in parallel → commit.
5. Cleaning at the end of the series: the last weeks have no 4 weeks after them, so the spike/dip rule only
   sees the past there. To check.

## Differences from TSFM-ensemble-influcast
The layout follows [TSFM-ensemble-influcast](https://github.com/sfiandrino/TSFM-ensemble-influcast), but the
method is different on purpose:

| | TSFM-ensemble-influcast | this repository |
|---|---|---|
| long gaps (summer) | filled with 0 | itpT: interpolated / itpF: NaN |
| data versions | A = ARI, B = ARI + historical ILI | itpT / itpF; ILI and ARI separately |
| cleaning | interpolation of gaps of at most 2 weeks | + spike/dip rule (4 weeks before and after) |
| location lagging behind | last value carried forward, at most 2 weeks | not forecast at that date |
| data | snapshot per week (`YYYY_WW`) | latest version (snapshots to do) |
| output | Influcast format | hub format (epi-tsfm) |
| ensemble | median of at least 2 models | none |
