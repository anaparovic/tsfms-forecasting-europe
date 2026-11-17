# Step 3 — Retrospective forecasts and plots

```bash
python code/backtest.py --model Chronos --target ILI                  # itpF by default
python code/backtest.py --model TabPFN-TS --target ILI --version itpT
python code/backtest.py --model TimesFM --target ARI --seasons 2024/25 --locations BE NL
python code/plot_forecasts.py --seasons 2017/18 2024/25 [--models Chronos TimesFM TabPFN-TS]
```

- **Seasons**: finished, non-COVID seasons from `first_forecast_season` (2017/18): 2017/18, 2018/19, 2019/20,
  2022/23, 2023/24, 2024/25, 2025/26.
- **Forecast dates**: every Sunday from W36 (4 weeks before the season, so an onset in W40 can be forecast) to W19
  (horizon 1 is then W20); 36 per season, 252 in all (`model-output/<target>/origins.csv`).
- **Output**: `model-output/<target>/<Model>_<version>/<date>-<Model>_<version>.csv`. Dates that already have a
  file are skipped, so a stopped run can be restarted.
- **Data**: the latest version for every date (revisions not taken into account). Snapshots per week are to do.
- **Plots**: 5 forecast dates per country and season, from 8 weeks before to 8 weeks after the highest week; with
  `--events <season_events.csv>` of the EWS repository, from 3 weeks before onset B to end A.

`model-output/ili_raw_value/` (local only, not in git) holds the first forecasts, made on the raw `value`
instead of `value_clean`.
