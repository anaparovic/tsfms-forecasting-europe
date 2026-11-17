"""TimesFM 2.5 forecasts, as in epi-tsfm (code/utils/timesfm_utils.py)."""
import numpy as np
import pandas as pd
import timesfm
import torch

from .common import HORIZON, QUANTILES, check_input, finalize

TIMESFM_Q = np.array([0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9])


class TimesFMForecaster:
    name = "TimesFM"

    def __init__(self, model_id="google/timesfm-2.5-200m-pytorch"):
        torch.set_float32_matmul_precision("high")
        self.model = timesfm.TimesFM_2p5_200M_torch.from_pretrained(model_id)
        self._compiled = None

    def _compile(self, max_context, horizon):
        if self._compiled != (max_context, horizon):
            self.model.compile(timesfm.ForecastConfig(
                max_context=max_context,
                max_horizon=horizon,
                normalize_inputs=True,
                use_continuous_quantile_head=True,
                fix_quantile_crossing=True,
            ))
            self._compiled = (max_context, horizon)

    def forecast(self, df, horizon=HORIZON, quantiles=QUANTILES):
        check_input(df)
        d = df.assign(truth_date=pd.to_datetime(df["truth_date"])).sort_values(["location", "truth_date"])
        locations = sorted(d["location"].unique())
        # NaN are interpolated by TimesFM itself, so itpF and itpT give the same forecasts
        series = [d.loc[d["location"] == loc, "value"].to_numpy(dtype=np.float32) for loc in locations]

        self._compile(d["truth_date"].nunique(), horizon)
        _, quant = self.model.forecast(horizon=horizon, inputs=series)   # (series, horizon, [mean, q0.1..q0.9])

        # only q0.1-q0.9 exist: np.interp keeps the lower/upper tails equal to q0.1/q0.9 (as in epi-tsfm)
        q_have = quant[:, :, 1:10].astype(np.float32)
        origin = d["truth_date"].max()
        rows = []
        for i, loc in enumerate(locations):
            for h in range(horizon):
                values = np.interp(quantiles, TIMESFM_Q, q_have[i, h])
                for q, v in zip(quantiles, values):
                    rows.append({"horizon": h + 1, "target_end_date": origin + pd.Timedelta(weeks=h + 1),
                                 "location": loc, "output_type": "quantile",
                                 "output_type_id": float(q), "value": float(v)})
        return finalize(pd.DataFrame(rows), df)
