# Step 2 — The models

| model | wrapper | input versions | notes |
|---|---|---|---|
| Chronos-2 | `code/tsfm_europe/chronos_model.py` | itpT, itpF | 23 quantiles directly; passes the `target` column |
| TimesFM 2.5 | `code/tsfm_europe/timesfm_model.py` | itpT, itpF | interpolates NaN itself, so itpF ≈ itpT |
| TabPFN-TS | `code/tsfm_europe/tabpfnts_model.py` | itpT only | no NaN allowed; API (`TABPFN_ACCESS_TOKEN`) or local CPU |

## Model input (`code/tsfm_europe/data.py`, `make_input`)
- `value_clean` up to the forecast date (Sunday), every location separately, with its whole history.
- `itpT`: gaps interpolated, each location from its first reported week. `itpF`: gaps NaN, all locations from the
  first week in the data (as epi-tsfm).
- A location is forecast only if it reported the forecast week and at least `min_weeks` (52) weeks.

## Output
Hub format, as epi-tsfm: `reference_date, target, horizon, target_end_date, location, output_type,
output_type_id, value`; horizons 1–4, 23 quantiles (0.01 … 0.99). Saved values are not clipped or sorted;
`common.clean_quantiles` does that for scoring.

## Environment
Python 3.11, CPU torch, `requirements-models.txt` (versions as in epi-tsfm, TimesFM pinned to a commit).
