"""Chronos-2 forecasts, as in epi-tsfm (code/utils/chronos_utils.py)."""
import pandas as pd
from chronos import BaseChronosPipeline

from .common import HORIZON, QUANTILES, check_input, finalize


class ChronosForecaster:
    name = "Chronos"

    def __init__(self, model_id="amazon/chronos-2", device="cpu", with_target_column=True):
        self.pipeline = BaseChronosPipeline.from_pretrained(model_id, device_map=device)
        # epi-tsfm also passes the constant text column `target`. Chronos-2 takes it as a covariate and
        # the forecasts change (~6% on the median), so it is kept to stay comparable with epi-tsfm.
        self.with_target_column = with_target_column

    def forecast(self, df, horizon=HORIZON, quantiles=QUANTILES):
        check_input(df)
        cols = ["location", "truth_date", "value"] + (["target"] if self.with_target_column else [])
        x = df[cols].copy()
        x["truth_date"] = pd.to_datetime(x["truth_date"])
        pred = self.pipeline.predict_df(
            x,
            prediction_length=horizon,
            quantile_levels=list(quantiles),
            id_column="location",
            timestamp_column="truth_date",
            target="value",
        )

        qcols = [c for c in pred.columns if c not in ("location", "truth_date", "target_name", "predictions")]
        long = pred.melt(id_vars=["location", "truth_date"], value_vars=qcols,
                         var_name="output_type_id", value_name="value")
        long = long.rename(columns={"truth_date": "target_end_date"})
        long["target_end_date"] = pd.to_datetime(long["target_end_date"])
        long["output_type"] = "quantile"
        long["output_type_id"] = long["output_type_id"].astype(float)
        origin = pd.to_datetime(df["truth_date"]).max()
        long["horizon"] = ((long["target_end_date"] - origin).dt.days // 7).astype(int)
        return finalize(long, df)
