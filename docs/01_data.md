# Step 1 — Download and build the weekly data

```bash
python code/data_import.py                 # download + build ILI and ARI
python code/data_import.py --no-download   # rebuild from target-data/raw/
```
The notebook `notebooks/data_preprocessing.ipynb` runs the same functions step by step, with tables and figures.

## Sources (`code/tsfm_europe/download.py`)
| file | source |
|---|---|
| `target-data/raw/erviss/{ili,ari}_total.csv`, `*_coverage.csv`, `positivity.csv`, `detections.csv` | ERVISS through [pyerviss](https://github.com/ngozzi/pyerviss), latest version (revisions included) |
| `target-data/raw/who/fluid_epi.csv` | WHO FluMart API, FluID: only the rows of Switzerland and the UK (2 MB) |
| `target-data/raw/who/metadata.csv` | WHO data dictionary |
| `.sources/who/fluid_epi.csv`, `flunet.csv` | full FluID (all countries, ~75 MB) and FluNet; local cache, not in git |

As in TSFM-ensemble-influcast (`.influcast/`), the large source files are not kept in git: only what is used.

## Processing (`code/tsfm_europe/preprocess.py`, function `build`)
1. **WHO FluID → ERVISS format**: Switzerland and the four UK regions, all ages, weeks with cases and covered
   population; incidence per 100,000; the Sunday of the ISO week (as ERVISS).
2. **GB** = sum of the cases and covered population of the four regions, only weeks where all four reported.
3. **Regular grid**: every location × every Sunday from 2014-W40; weeks not reported are NaN.
4. **Season**: `season`, `season_week` (W40 = 1), `covid_week` (2020-W10 to W20).
5. **`season_info`**: one row per location and season: reported weeks, `valid` (> 50% reported), `finished`,
   `covid`. Counts only weeks really reported.
6. **Cleaning** → `value_clean`, flags `spike_capped`, `dip_raised`, `imputed`.
7. **Positivity** (ERVISS), without the EU aggregate.
8. **Six checks** (`run_checks`): if one fails, nothing is saved.

## Output: `target-data/processed/`
| file | content |
|---|---|
| `<target>.csv` | location, country, source, indicator, age, unit, season, season_week, year_week, date, covid_week, value, value_clean, spike_capped, dip_raised, imputed |
| `<target>_season_info.csv` | location, season, reported_weeks, season_length, share_reported, valid, finished, covid |
| `positivity.csv` | the same for ILI and ARI |

These files are read by the EWS repository (`scripts/fetch_inputs.py` there): keep their names and columns.
