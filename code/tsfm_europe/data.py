"""Model input at a forecast date (origin), and the seasons and origins of the retrospective forecasts."""
import pandas as pd

from .common import FREQ, ROOT, check_input, load_config

_CFG = load_config()
MIN_WEEKS = _CFG["min_weeks"]
VERSIONS = ("itpT", "itpF")
FIRST_ORIGIN_WEEK = _CFG["first_origin_week"]   # 4 weeks before the season starts, so an onset in W40 can be forecast
LAST_ORIGIN_WEEK = _CFG["last_origin_week"]     # horizon 1 is then W20, the last week of the season


def load_data(target, root=ROOT):
    # `value_clean` (spikes capped, dips raised, gaps of at most 2 weeks filled), returned as `value`.
    # The cleaning looks at the 4 weeks before and after each week, so the last weeks before a past
    # origin can contain a little information from after it.
    d = pd.read_csv(f"{root}/target-data/processed/{target.lower()}.csv", parse_dates=["date"])
    return (d[["date", "location", "value_clean"]]
            .rename(columns={"value_clean": "value"})
            .sort_values(["location", "date"])
            .reset_index(drop=True))


def make_input(data, origin, target="ILI", version="itpT", min_weeks=MIN_WEEKS):
    """
    Weekly series of every location up to `origin`, in the format of epi-tsfm.
    itpT: gaps filled by linear interpolation, each location from its first reported week.
    itpF: gaps left as NaN, all locations from the first week in the data (as epi-tsfm).
    A location is used only if it reported the origin week and at least `min_weeks` weeks.
    """
    if version not in VERSIONS:
        raise ValueError(f"version must be one of {VERSIONS}")
    origin = pd.Timestamp(origin)
    if origin.dayofweek != 6:
        raise ValueError(f"origin {origin.date()} is not a Sunday")

    first_week = data["date"].min()
    parts = []
    for loc, g in data[data["date"] <= origin].groupby("location"):
        s = g.set_index("date")["value"].dropna()
        if origin not in s.index or len(s) < min_weeks:
            continue
        start = first_week if version == "itpF" else s.index.min()
        s = s.reindex(pd.date_range(start, origin, freq=FREQ))
        if version == "itpT":
            s = s.interpolate(method="linear", limit_area="inside")
        parts.append(pd.DataFrame({
            "truth_date": s.index,
            "location": loc,
            "target": f"{target.upper()}_incidence",
            "value": s.to_numpy(dtype=float),
        }))
    if not parts:
        raise ValueError(f"no location can be forecast at {origin.date()}")

    df = pd.concat(parts, ignore_index=True)
    check_input(df, allow_nan=(version == "itpF"))
    return df


def forecast_seasons(target, root=ROOT, first_season=_CFG["first_forecast_season"]):
    """Finished, non-COVID seasons from `first_season` on (the first seasons are history only)."""
    info = pd.read_csv(f"{root}/target-data/processed/{target.lower()}_season_info.csv")
    seasons = info.loc[info["finished"] & ~info["covid"], "season"]
    return sorted(s for s in set(seasons) if s >= first_season)


def forecast_origins(seasons, first_week=FIRST_ORIGIN_WEEK, last_week=LAST_ORIGIN_WEEK):
    """Every Sunday from ISO week `first_week` of year y to `last_week` of y+1, for each season 'y/yy'."""
    rows = []
    for season in seasons:
        y = int(season[:4])
        start = pd.Timestamp.fromisocalendar(y, first_week, 7)
        end = pd.Timestamp.fromisocalendar(y + 1, last_week, 7)
        for o in pd.date_range(start, end, freq=FREQ):
            iso = o.isocalendar()
            rows.append({"season": season, "origin": o, "year_week": f"{iso.year}-W{iso.week:02d}"})
    return pd.DataFrame(rows)
