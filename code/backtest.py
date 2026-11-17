"""
Retrospective forecasts of one model: one file per forecast date in model-output/<target>/<model>_<version>/,
for every Sunday from W36 to W19 of the finished, non-COVID seasons (config.yaml). The input is the latest
version of the data (revisions are not taken into account). Dates that already have a file are skipped, so a
stopped run can be restarted.

    python code/backtest.py --model Chronos --target ILI
"""
import argparse
import time

import pandas as pd

from tsfm_europe import MODELS, get_model
from tsfm_europe.common import ROOT, load_config
from tsfm_europe.data import VERSIONS, forecast_origins, forecast_seasons, load_data, make_input


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--model", required=True, choices=MODELS)
    p.add_argument("--target", required=True, choices=["ILI", "ARI"])
    p.add_argument("--version", default="itpF", choices=VERSIONS)
    p.add_argument("--seasons", nargs="*", help="e.g. 2023/24 (default: finished, non-COVID seasons from config.yaml)")
    p.add_argument("--locations", nargs="*", help="e.g. BE NL (default: all)")
    p.add_argument("--origins", nargs="*", help="e.g. 2024-12-15 (default: all)")
    p.add_argument("--tabpfn_mode", default=load_config()["tabpfn_mode"], choices=["client", "local"])
    args = p.parse_args()
    if args.model == "TabPFN-TS" and args.version != "itpT":
        p.error("TabPFN-TS does not accept NaN, use --version itpT")

    data = load_data(args.target, ROOT)
    seasons = args.seasons or forecast_seasons(args.target, ROOT)
    origins = forecast_origins(seasons)["origin"]
    origins = origins[origins <= data["date"].max()]
    if args.origins:
        origins = origins[origins.isin(pd.to_datetime(args.origins))]

    label = f"{args.model}_{args.version}"
    out_dir = ROOT / "model-output" / args.target.lower() / label
    out_dir.mkdir(parents=True, exist_ok=True)
    todo = [o for o in origins if not (out_dir / f"{o.date()}-{label}.csv").exists()]
    print(f"{label} {args.target}: {len(seasons)} seasons, {len(origins)} forecast dates, {len(todo)} to do")
    if not todo:
        return

    model = get_model(args.model, **({"mode": args.tabpfn_mode} if args.model == "TabPFN-TS" else {}))
    for i, origin in enumerate(todo, 1):
        start = time.time()
        x = make_input(data, origin, args.target, args.version)
        if args.locations:
            x = x[x["location"].isin(args.locations)]
            if x.empty:
                print(f"{origin.date()}: none of {args.locations} can be forecast")
                continue
        model.forecast(x).to_csv(out_dir / f"{origin.date()}-{label}.csv", index=False)
        print(f"[{i}/{len(todo)}] {origin.date()}: {x['location'].nunique()} locations, "
              f"{time.time() - start:.0f} s", flush=True)


if __name__ == "__main__":
    main()
