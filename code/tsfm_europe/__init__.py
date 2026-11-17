"""Zero-shot forecasting models (Chronos-2, TimesFM 2.5, TabPFN-TS), adapted from github.com/ngozzi/epi-tsfm."""
from .common import HORIZON, OUTPUT_COLUMNS, QUANTILES

MODELS = ["Chronos", "TimesFM", "TabPFN-TS"]


def get_model(name, **kwargs):
    # imported here, so only the package of the chosen model has to be installed
    if name == "Chronos":
        from .chronos_model import ChronosForecaster
        return ChronosForecaster(**kwargs)
    if name == "TimesFM":
        from .timesfm_model import TimesFMForecaster
        return TimesFMForecaster(**kwargs)
    if name == "TabPFN-TS":
        from .tabpfnts_model import TabPFNTSForecaster
        return TabPFNTSForecaster(**kwargs)
    raise ValueError(f"unknown model {name}, choose from {MODELS}")
