"""
Weekly ILI / ARI data of all locations from the raw ERVISS and WHO FluID files (target-data/raw/).

- WHO FluID (Switzerland, UK regions) in the ERVISS format; GB = sum of the four regions
- regular weekly grid (every location x every Sunday from first_season-W40); missing weeks are NaN
- season, season_week, covid_week; season_info (one row per location and season)
- value_clean: spikes capped, dips raised, short gaps interpolated (the original values stay in `value`)
- positivity (ERVISS)
"""
import numpy as np
import pandas as pd

COLUMNS = ["location", "country", "source", "indicator", "age", "unit", "season", "season_week", "year_week",
           "date", "covid_week", "value", "value_clean", "spike_capped", "dip_raised", "imputed"]


def iso_sunday(year_week):
    """'2014-W40' (str or Series) -> Sunday of that ISO week."""
    return pd.to_datetime(year_week + "-7", format="%G-W%V-%u")


def load_raw(raw_dir, target):
    erviss = pd.read_csv(raw_dir / f"erviss/{target.lower()}_total.csv", parse_dates=["date"])
    who = pd.read_csv(raw_dir / "who/fluid_epi.csv", low_memory=False)
    pos = pd.read_csv(raw_dir / "erviss/positivity.csv", parse_dates=["date"])
    return erviss, who, pos


def fluid_regions(who, target, cfg):
    """WHO FluID rows of the chosen locations: all ages, weeks with both cases and covered population."""
    case_col, pop_col = f"{target}_CASE", f"{target}_POP_COV"
    countries = cfg["fluid_countries"]
    fluid = who[who["COUNTRY_AREA_TERRITORY"].isin(countries)
                & (who["AGEGROUP_CODE"].str.upper() == "ALL")].copy()
    fluid["country"] = fluid["COUNTRY_AREA_TERRITORY"]
    fluid["country_code"] = fluid["COUNTRY_AREA_TERRITORY"].map(countries)
    fluid["year_week"] = fluid["ISO_YEAR"].astype(str) + "-W" + fluid["ISO_WEEK"].astype(str).str.zfill(2)
    fluid = fluid[["country", "country_code", "year_week", case_col, pop_col]].dropna()
    return fluid[fluid[pop_col] > 0]


def add_gb(fluid, target, cfg):
    """GB as a whole: sum of the cases and of the covered population of the four regions, only weeks where all four reported."""
    case_col, pop_col = f"{target}_CASE", f"{target}_POP_COV"
    regions = cfg["gb_regions"]
    gb = (fluid[fluid["country_code"].isin(regions)].groupby("year_week")
          .agg(n_regions=("country_code", "nunique"), cases=(case_col, "sum"), population=(pop_col, "sum"))
          .reset_index())
    complete = gb["n_regions"] == len(regions)
    gb = gb[complete].rename(columns={"cases": case_col, "population": pop_col})
    gb["country"] = "United Kingdom (sum of regions)"
    gb["country_code"] = "GB"
    return pd.concat([fluid, gb[fluid.columns]], ignore_index=True), int(complete.sum()), int((~complete).sum())


def fluid_to_erviss(fluid, target, columns, first_date):
    """Incidence per 100,000 and the Sunday of the ISO week, as in ERVISS."""
    case_col, pop_col = f"{target}_CASE", f"{target}_POP_COV"
    fluid = fluid.copy()
    fluid["value"] = (fluid[case_col] / fluid[pop_col] * 100000).round(1)
    fluid["date"] = iso_sunday(fluid["year_week"])
    fluid["indicator"] = target.lower()
    fluid["age"] = "total"
    fluid["unit"] = "per 100,000 population"
    fluid = fluid[columns]
    return fluid[fluid["date"] >= first_date].reset_index(drop=True)


def combine(erviss, fluid):
    """One table for all locations (indicator and age are kept to tell ILI/ARI and age groups apart)."""
    erviss, fluid = erviss.copy(), fluid.copy()
    erviss["source"] = "ERVISS"
    fluid["source"] = "FluID"
    return (pd.concat([erviss, fluid], ignore_index=True)
            .rename(columns={"country_code": "location"})
            [["location", "country", "source", "indicator", "age", "unit", "year_week", "date", "value"]]
            .sort_values(["location", "date"])
            .reset_index(drop=True))


def regular_grid(data, first_date):
    """Every location gets every week from first_date to the last week in the data; weeks not reported are NaN."""
    all_weeks = pd.date_range(first_date, data["date"].max(), freq="7D")
    info = data.groupby("location")[["country", "source", "indicator", "age", "unit"]].first()
    grid = pd.MultiIndex.from_product([info.index, all_weeks], names=["location", "date"])
    out = (data.set_index(["location", "date"])["value"]
           .reindex(grid)
           .reset_index()
           .merge(info, on="location"))
    iso = out["date"].dt.isocalendar()
    out["year_week"] = iso["year"].astype(str) + "-W" + iso["week"].astype(str).str.zfill(2)
    return out[["location", "country", "source", "indicator", "age", "unit", "year_week", "date", "value"]]


def add_season(d, cfg, date_col="date"):
    """`season` (e.g. "2024/25") and `season_week` (week 40 = 1); weeks outside the season get NaN."""
    start_week, end_week = cfg["season_start_week"], cfg["season_end_week"]
    d = d.copy()
    iso = d[date_col].dt.isocalendar()
    week, year = iso["week"].astype(int), iso["year"].astype(int)
    in_season = (week >= start_week) | (week <= end_week)
    start_year = year.where(week >= start_week, year - 1)
    season_start = pd.to_datetime(start_year.astype(str) + f"-W{start_week}-7", format="%G-W%V-%u")
    d["season"] = (start_year.astype(str) + "/" + (start_year + 1).astype(str).str[-2:]).where(in_season)
    d["season_week"] = ((d[date_col] - season_start).dt.days // 7 + 1).where(in_season).astype("Int64")
    return d


def add_covid_week(data, cfg):
    data = data.copy()
    data["covid_week"] = (data["season"] == "2019/20") & (data["date"] >= iso_sunday(cfg["covid_start"]))
    return data


def season_length(season, cfg):
    start = iso_sunday(f"{season[:4]}-W{cfg['season_start_week']}")
    end = iso_sunday(f"{int(season[:4]) + 1}-W{cfg['season_end_week']}")
    return (end - start).days // 7 + 1


def make_season_info(data, cfg):
    """One row per location and season: reported weeks, length, share reported, valid, finished, covid."""
    info = data.groupby(["location", "season"]).agg(reported_weeks=("value", "count")).reset_index()
    info["season_length"] = info["season"].map(lambda s: season_length(s, cfg))
    info["share_reported"] = (info["reported_weeks"] / info["season_length"]).round(2)
    info["valid"] = info["share_reported"] > cfg["valid_share"]
    info["finished"] = info["season"] != data["season"].dropna().max()
    info["covid"] = info["season"].isin(cfg["covid_seasons"])
    return info


def find_spikes(s, window, ratio, min_value):
    """A week more than `ratio` times higher than every week in the `window` weeks before and after (and above min_value)."""
    around = pd.concat([s.shift(k) for k in range(-window, window + 1) if k != 0], axis=1)
    cap = around.max(axis=1)
    has_neighbours = s.shift(1).notna() & s.shift(-1).notna()
    return (s > ratio * cap) & (s > min_value) & has_neighbours, cap


def find_dips(s, window, ratio, min_value):
    """The mirror rule: a week less than 1/ratio of every week around it (all above min_value)."""
    around = pd.concat([s.shift(k) for k in range(-window, window + 1) if k != 0], axis=1)
    floor = around.min(axis=1)
    has_neighbours = s.shift(1).notna() & s.shift(-1).notna()
    return (s < floor / ratio) & (floor > min_value) & has_neighbours, floor


def fill_short_gaps(s, max_gap):
    """Linear interpolation of gaps of at most `max_gap` weeks with data on both sides."""
    missing = s.isna()
    gap_id = (missing != missing.shift()).cumsum()
    gap_length = missing.groupby(gap_id).transform("sum")
    filled = s.interpolate(limit_area="inside")
    to_fill = missing & (gap_length <= max_gap) & filled.notna()
    return s.where(~to_fill, filled), to_fill


def clean(data, cfg):
    """value_clean: spikes capped at the highest neighbour, dips raised to the lowest, short gaps interpolated."""
    w, r, m = cfg["spike_window"], cfg["spike_ratio"], cfg["spike_min"]
    parts = []
    for _, g in data.groupby("location"):
        g = g.sort_values("date").copy()
        s = g.set_index("date")["value"]
        spikes, cap = find_spikes(s, w, r, m)
        dips, floor = find_dips(s, w, r, m)
        value_clean, imputed = fill_short_gaps(s.where(~spikes, cap).where(~dips, floor), cfg["max_interpolated_gap"])
        g["value_clean"] = value_clean.to_numpy()
        g["spike_capped"] = spikes.to_numpy()
        g["dip_raised"] = dips.to_numpy()
        g["imputed"] = imputed.to_numpy()
        parts.append(g)
    return pd.concat(parts, ignore_index=True)


def make_positivity(pos, first_date, cfg):
    """ERVISS test positivity (influenza, RSV, SARS-CoV-2; primary care and hospitals), without the EU aggregate."""
    p = (pos[(pos["date"] >= first_date) & (pos["country_code"] != "EU")]
         .rename(columns={"country_code": "location", "value": "positivity"}))
    p = add_season(p, cfg)
    return (p[["location", "country", "pathogen", "setting", "season", "season_week", "year_week", "date",
               "positivity", "tests", "detections"]]
            .sort_values(["location", "pathogen", "setting", "date"])
            .reset_index(drop=True))


def run_checks(data, raw):
    """
    1. one row per location and week; 2. the same number of weeks for every location;
    3. every reported value equals the raw data; 4. no reported value lost or added;
    5. value_clean equals value except capped spikes, raised dips and filled weeks;
    6. capped spikes are lower and raised dips higher than before.
    Raises AssertionError if one fails, so wrong data are never saved.
    """
    n_dup = data.duplicated(["location", "date"]).sum()
    weeks = data.groupby("location").size()
    compare = raw[["location", "date", "value"]].merge(
        data[["location", "date", "value"]], on=["location", "date"], how="left", suffixes=("_raw", "_processed"))
    n_diff = (~np.isclose(compare["value_raw"], compare["value_processed"])).sum()
    unchanged = ~data["spike_capped"] & ~data["dip_raised"] & ~data["imputed"]
    same = np.allclose(data.loc[unchanged, "value_clean"], data.loc[unchanged, "value"], equal_nan=True)
    lower = (data.loc[data["spike_capped"], "value_clean"] < data.loc[data["spike_capped"], "value"]).all()
    higher = (data.loc[data["dip_raised"], "value_clean"] > data.loc[data["dip_raised"], "value"]).all()
    checks = {
        "1. duplicated location + week": n_dup,
        "2. weeks per location (min, max)": (int(weeks.min()), int(weeks.max())),
        "3. values different from raw": n_diff,
        "4. reported weeks (raw, processed)": (len(raw), int(data["value"].notna().sum())),
        "5. value_clean = value outside the changed weeks": same,
        "6. capped spikes lower, raised dips higher": (lower, higher),
    }
    assert n_dup == 0
    assert weeks.min() == weeks.max()
    assert n_diff == 0
    assert len(raw) == data["value"].notna().sum()
    assert same and lower and higher
    return checks


def build(raw_dir, target, cfg, verbose=True):
    """All steps for one target. Returns data, season_info, positivity and the intermediate tables."""
    target = target.upper()
    first_date = iso_sunday(f"{cfg['first_season']}-W{cfg['season_start_week']}")
    erviss, who, pos = load_raw(raw_dir, target)

    fluid = fluid_regions(who, target, cfg)
    fluid, gb_weeks, gb_dropped = add_gb(fluid, target, cfg)
    fluid = fluid_to_erviss(fluid, target, erviss.columns, first_date)

    data = regular_grid(combine(erviss, fluid), first_date)
    data = add_covid_week(add_season(data, cfg), cfg)
    season_info = make_season_info(data, cfg)
    data = clean(data, cfg)[COLUMNS]
    positivity = make_positivity(pos, first_date, cfg)

    raw = pd.concat([erviss, fluid], ignore_index=True).rename(columns={"country_code": "location"})
    checks = run_checks(data, raw)
    if verbose:
        print(f"{target}: {data['location'].nunique()} locations x {data['date'].nunique()} weeks "
              f"({data['date'].min().date()} to {data['date'].max().date()}); GB: {gb_weeks} weeks with all "
              f"4 regions, {gb_dropped} dropped")
        print(f"  spikes capped {data['spike_capped'].sum()}, dips raised {data['dip_raised'].sum()}, "
              f"weeks interpolated {data['imputed'].sum()}; all checks passed")
    return {"data": data, "season_info": season_info, "positivity": positivity,
            "erviss": erviss, "who": who, "fluid": fluid, "checks": checks}
