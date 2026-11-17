"""
Observed data and 4-week forecasts (median, 50% and 90% intervals) at 5 forecast dates per country and season.
Rows = models, columns = forecast dates.

Without --events the dates go from 8 weeks before to 8 weeks after the highest week of the season. With the
season_events.csv of the EWS repo (onset B, peak A, end A) they go from 3 weeks before the onset to the end.

    python code/plot_forecasts.py --seasons 2017/18 2024/25
    python code/plot_forecasts.py --seasons 2017/18 --events ../CODE/results/preprocessing/ili/season_events.csv
"""
import argparse

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from tsfm_europe.common import ROOT
MODELS = ["Chronos", "TimesFM"]
N_DATES = 5
WEEK = pd.Timedelta(weeks=1)


def load_forecasts(target, model, version):
    folder = ROOT / "model-output" / target.lower() / f"{model}_{version}"
    files = sorted(folder.glob(f"*-{model}_{version}.csv"))
    if not files:
        raise FileNotFoundError(f"no forecasts in {folder}")
    return pd.concat((pd.read_csv(f, parse_dates=["reference_date", "target_end_date"]) for f in files),
                     ignore_index=True)


def peaks_from_data(data):
    """Highest week of every location and season (COVID weeks excluded), when no events file is given."""
    d = data.dropna(subset=["season", "value_clean"])
    d = d[~d["covid_week"]]
    peaks = d.loc[d.groupby(["location", "season"])["value_clean"].idxmax(), ["location", "season", "date"]]
    return peaks.rename(columns={"date": "date_peak_A"}).assign(date_onset_B=pd.NaT, date_end_A=pd.NaT)


def wanted_dates(ev, n=N_DATES):
    # without an onset or an end, start 8 weeks before / stop 8 weeks after the peak
    peak = ev["date_peak_A"]
    if pd.isna(peak):
        return []
    first = ev["date_onset_B"] - 3 * WEEK if pd.notna(ev["date_onset_B"]) else peak - 8 * WEEK
    last = ev["date_end_A"] if pd.notna(ev["date_end_A"]) else peak + 8 * WEEK
    span = (last - first) // WEEK
    return [first + round(i * span / (n - 1)) * WEEK for i in range(n)]


def pick_origins(available, wanted):
    available = sorted(available)
    chosen = []
    for w in wanted:
        free = [d for d in available if d not in chosen] or available
        chosen.append(min(free, key=lambda d: abs(d - w)))
    return sorted(chosen)


def plot_panel(ax, obs, fc, origin, title):
    q = fc.pivot(index="target_end_date", columns="output_type_id", values="value").sort_index()
    last = obs.loc[obs["date"] == origin, "value_clean"]
    if len(last) and pd.notna(last.iloc[0]):
        q.loc[origin] = last.iloc[0]
        q = q.sort_index()
    ax.fill_between(q.index, q[0.05], q[0.95], color="#FDD9B5", lw=0, label="90% interval")
    ax.fill_between(q.index, q[0.25], q[0.75], color="#F4A261", lw=0, label="50% interval")
    ax.plot(q.index, q[0.5], color="#9C2A00", lw=1.3, label="median forecast")
    ax.plot(obs["date"], obs["value_clean"], color="#4A5568", lw=1.6, label="observed (value_clean)")
    ax.axvline(origin, color="black", ls="--", lw=1)
    ax.set_title(title, fontsize=9)
    ax.tick_params(axis="x", rotation=30, labelsize=7)
    ax.tick_params(axis="y", labelsize=7)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--target", default="ILI")
    p.add_argument("--version", default="itpF")
    p.add_argument("--seasons", nargs="+", default=["2017/18", "2024/25"])
    p.add_argument("--models", nargs="+", default=MODELS, help="e.g. Chronos TimesFM TabPFN-TS")
    p.add_argument("--locations", nargs="*", help="only these locations (default: all)")
    p.add_argument("--events", help="season_events.csv of the EWS repo (default: the highest week of each season)")
    args = p.parse_args()
    models = args.models
    default_models = models == MODELS
    t = args.target.lower()

    data = pd.read_csv(ROOT / "target-data" / "processed" / f"{t}.csv", parse_dates=["date"])
    events = (pd.read_csv(args.events, parse_dates=["date_onset_B", "date_peak_A", "date_end_A"]) if args.events
              else peaks_from_data(data))
    fcs = {m: load_forecasts(args.target, m, "itpT" if m == "TabPFN-TS" else args.version) for m in models}   # TabPFN-TS: itpT only

    chosen = []
    for season in args.seasons:
        y = int(season[:4])
        start = pd.Timestamp.fromisocalendar(y, 36, 7)
        end = pd.Timestamp.fromisocalendar(y + 1, 23, 7)
        out_dir = ROOT / "figures" / "forecasts" / t / season.replace("/", "-")
        out_dir.mkdir(parents=True, exist_ok=True)
        for _, ev in events[events["season"] == season].iterrows():
            loc = ev["location"]
            if args.locations and loc not in args.locations:
                continue
            wanted = wanted_dates(ev)
            avail = set.intersection(*[set(f.loc[(f["location"] == loc) & f["reference_date"].between(start, end),
                                                 "reference_date"]) for f in fcs.values()])
            if not wanted or not avail:
                continue
            origins = pick_origins(avail, wanted)
            obs = data[(data["location"] == loc) & data["date"].between(start, end)]

            fig, axes = plt.subplots(len(models), N_DATES, figsize=(4.6 * N_DATES, 3.5 * len(models)), sharey=True)
            for i, m in enumerate(models):
                f = fcs[m][fcs[m]["location"] == loc]
                for j, o in enumerate(origins):
                    plot_panel(axes[i, j], obs, f[f["reference_date"] == o], o,
                               f"{m} (forecast date {o.date()})")
                    axes[i, j].set_xlim(start, end)
                axes[i, 0].set_ylabel(f"{args.target} incidence")
            chosen += [{"season": season, "location": loc, "date_nr": j + 1, "wanted": w.date(), "origin": o.date()}
                       for j, (w, o) in enumerate(zip(wanted, origins))]
            fig.suptitle(f"{loc} {season} ({args.target})", fontsize=11)
            axes[0, 0].legend(fontsize=7, loc="upper left")
            fig.tight_layout()
            fig.savefig(out_dir / (f"{loc}.png" if default_models else f"{loc}_{'_'.join(models)}.png"), dpi=90)
            plt.close(fig)
        print(season, "->", out_dir)

    if default_models and not args.locations:
        pd.DataFrame(chosen).to_csv(ROOT / "figures" / "forecasts" / t / "plotted_dates.csv", index=False)


if __name__ == "__main__":
    main()
