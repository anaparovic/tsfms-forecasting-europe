"""
Step 1: download the raw data and build the weekly data of all locations.

    python code/data_import.py                  # download + ILI and ARI
    python code/data_import.py --no-download    # only rebuild target-data/processed/ from target-data/raw/

Writes target-data/processed/<target>.csv, <target>_season_info.csv and positivity.csv.
"""
import argparse

from tsfm_europe.common import ROOT, load_config
from tsfm_europe.preprocess import build

RAW = ROOT / "target-data" / "raw"
SOURCES = ROOT / ".sources"            # full WHO files, local cache, not in git
PROCESSED = ROOT / "target-data" / "processed"


def main():
    cfg = load_config()
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--targets", nargs="+", default=cfg["targets"], choices=["ILI", "ARI"])
    p.add_argument("--no-download", action="store_true", help="use the raw data already in target-data/raw/")
    args = p.parse_args()

    if not args.no_download:
        from tsfm_europe.download import download_raw
        download_raw(RAW, SOURCES)

    PROCESSED.mkdir(parents=True, exist_ok=True)
    for target in args.targets:
        out = build(RAW, target, cfg)
        files = {f"{target.lower()}.csv": out["data"], f"{target.lower()}_season_info.csv": out["season_info"],
                 "positivity.csv": out["positivity"]}    # positivity is the same for ILI and ARI
        for name, d in files.items():
            d.to_csv(PROCESSED / name, index=False)
            print(f"  saved {name:24} {d.shape[0]:7} rows, {d.shape[1]:2} columns")


if __name__ == "__main__":
    main()
