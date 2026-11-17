"""Settings and helpers shared by all forecasting models (hub output format, as in epi-tsfm), configuration."""
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[2]

HORIZON = 4
FREQ = "W-SUN"
QUANTILES = np.array([0.01, 0.025, 0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5,
                      0.55, 0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95, 0.975, 0.99])
OUTPUT_COLUMNS = ["reference_date", "target", "horizon", "target_end_date", "location",
                  "output_type", "output_type_id", "value"]


def check_input(df, allow_nan=True):
    missing = {"truth_date", "location", "target", "value"} - set(df.columns)
    if missing:
        raise ValueError(f"input is missing columns {missing}")
    if df["target"].nunique() != 1:
        raise ValueError("input must contain exactly one target")
    dates = pd.to_datetime(df["truth_date"])
    if (dates.dt.dayofweek != 6).any():
        raise ValueError("truth_date must be Sundays")
    last = dates.groupby(df["location"]).max()
    if last.nunique() != 1:
        raise ValueError(f"all locations must end on the same date, got {sorted(last.unique())}")
    # TabPFN-TS infers the frequency from the dates, so the grid must be regular
    for loc, d in dates.groupby(df["location"]):
        if d.duplicated().any() or (d.sort_values().diff().dropna() != pd.Timedelta(weeks=1)).any():
            raise ValueError(f"{loc}: dates are not a regular weekly grid")
    if not allow_nan and df["value"].isna().any():
        raise ValueError("this model does not accept NaN, use the itpT input")


def clean_quantiles(pred):
    """Clip at 0 and sort the quantiles of every forecast. Only for scoring; saved forecasts are left as they are."""
    pred = pred.sort_values(["reference_date", "location", "horizon", "output_type_id"]).copy()
    keys = [pred["reference_date"], pred["location"], pred["horizon"]]
    values = pred["value"].astype(float).clip(lower=0)
    pred["value"] = values.groupby(keys).transform(lambda v: np.sort(v.to_numpy()))
    return pred.reset_index(drop=True)


def finalize(pred, df):
    pred = pred.copy()
    pred.insert(0, "reference_date", pd.to_datetime(df["truth_date"]).max())
    pred.insert(1, "target", df["target"].iloc[0])
    pred["target_end_date"] = pd.to_datetime(pred["target_end_date"])
    pred["output_type_id"] = np.round(pred["output_type_id"].astype(float), 3)
    pred["value"] = np.round(pred["value"].astype(float), 3)
    pred = pred[OUTPUT_COLUMNS].sort_values(["location", "horizon", "output_type_id"])
    return pred.reset_index(drop=True)


def load_config(path=None):
    with open(path or ROOT / "config.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)
