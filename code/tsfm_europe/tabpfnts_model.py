"""TabPFN-TS forecasts, as in epi-tsfm (code/utils/tabpfnts_utils.py), through the Prior Labs API or locally."""
import os

import numpy as np
import pandas as pd
import torch
from tabpfn_time_series import FeatureTransformer, TabPFNMode, TabPFNTimeSeriesPredictor, TimeSeriesDataFrame
from tabpfn_time_series.data_preparation import generate_test_X
from tabpfn_time_series.features import AutoSeasonalFeature, CalendarFeature, RunningIndexFeature

from .common import FREQ, HORIZON, QUANTILES, check_input, finalize


class TabPFNTSForecaster:
    name = "TabPFN-TS"

    def __init__(self, mode="client"):
        if mode == "client":
            import tabpfn_client
            token = os.environ.get("TABPFN_TOKEN") or os.environ.get("TABPFN_ACCESS_TOKEN")
            if not token:
                raise RuntimeError("set the environment variable TABPFN_ACCESS_TOKEN, or use mode='local'")
            os.environ["TABPFN_TOKEN"] = token          # the worker processes read this variable
            tabpfn_client.set_access_token(token)
            self.predictor = TabPFNTimeSeriesPredictor(tabpfn_mode=TabPFNMode.CLIENT)
        elif mode == "local":
            if torch.cuda.is_available():
                self.predictor = TabPFNTimeSeriesPredictor(tabpfn_mode=TabPFNMode.LOCAL)
            else:
                # the package only supports a GPU in local mode, so the CPU worker is set by hand
                from tabpfn import TabPFNRegressor
                from tabpfn_time_series.predictor import TABPFN_TS_DEFAULT_CONFIG, TabPFNModelAdapter, TimeSeriesPredictor
                from tabpfn_time_series.worker.parallel_workers import CPUParallelWorker
                adapter = TabPFNModelAdapter(model_class=TabPFNRegressor, model_config=TABPFN_TS_DEFAULT_CONFIG,
                                             tabpfn_output_selection="median")
                self.predictor = TimeSeriesPredictor(model_adapter=adapter, worker_class=CPUParallelWorker)
        else:
            raise ValueError("mode must be 'client' or 'local'")

    def forecast(self, df, horizon=HORIZON, quantiles=QUANTILES):
        check_input(df, allow_nan=False)
        x = df[["location", "truth_date", "value"]].rename(
            columns={"location": "item_id", "truth_date": "timestamp", "value": "target"})
        x["timestamp"] = pd.to_datetime(x["timestamp"])
        x["target"] = x["target"].astype(float)

        train = TimeSeriesDataFrame(x.sort_values(["item_id", "timestamp"]))
        if train.freq != FREQ:
            raise ValueError(f"TabPFN-TS inferred frequency {train.freq}, expected {FREQ}")
        test = generate_test_X(train, horizon)
        train, test = FeatureTransformer(
            [RunningIndexFeature(), CalendarFeature(), AutoSeasonalFeature()]).transform(train, test)

        pred = pd.DataFrame(self.predictor.predict(train, test)).reset_index()
        pred.columns = [str(c) for c in pred.columns]

        # q0.1-q0.9 -> 23 quantiles with np.interp, tails clamped (as in epi-tsfm)
        have = sorted((float(c), c) for c in pred.columns if c not in ("item_id", "timestamp", "target"))
        q_have = np.array([q for q, _ in have])
        vals = pred[[c for _, c in have]].to_numpy(dtype=float)
        interp = np.array([np.interp(quantiles, q_have, v) for v in vals])

        long = pd.DataFrame(interp, columns=list(quantiles))
        long["location"] = pred["item_id"].to_numpy()
        long["target_end_date"] = pd.to_datetime(pred["timestamp"]).to_numpy()
        long = long.melt(id_vars=["location", "target_end_date"], var_name="output_type_id", value_name="value")
        long["output_type"] = "quantile"
        origin = pd.to_datetime(df["truth_date"]).max()
        long["horizon"] = ((long["target_end_date"] - origin).dt.days // 7).astype(int)
        return finalize(long, df)
