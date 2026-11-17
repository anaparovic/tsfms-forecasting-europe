"""
Download the raw data to target-data/raw/ (in git) and the full WHO files to .sources/ (not in git).

As .influcast/ in TSFM-ensemble-influcast: the full WHO FluID (all countries, ~75 MB) and FluNet stay in the
local cache .sources/who/; target-data/raw/who/fluid_epi.csv keeps only the rows of Switzerland and the UK
(the only FluID locations used). ERVISS files are small and are kept whole.
"""
from datetime import date
from pathlib import Path

import pandas as pd

WHO = {
    "fluid_epi": "https://xmart-api-public.who.int/FLUMART/VIW_FID_EPI?$format=csv",
    "flunet":    "https://xmart-api-public.who.int/FLUMART/VIW_FNT?$format=csv",
    "metadata":  "https://xmart-api-public.who.int/FLUMART/VIW_FLU_METADATA?$format=csv",
}
# FluID rows kept in target-data/raw/: Switzerland, the four UK regions and the whole UK (all age groups)
FLUID_KEEP = "Switzerland|United Kingdom"


def extract_fluid(full_csv, out_csv):
    """Rows of FLUID_KEEP from the full FluID file (all columns, unchanged)."""
    who = pd.read_csv(full_csv, low_memory=False)
    keep = who[who["COUNTRY_AREA_TERRITORY"].str.contains(FLUID_KEEP, na=False)]
    keep.to_csv(out_csv, index=False)
    return keep


def download_raw(raw_dir, sources_dir):
    import pyerviss as pv   # only needed for the download

    raw_dir, sources_dir = Path(raw_dir), Path(sources_dir)
    for d in [raw_dir / "erviss", raw_dir / "who", sources_dir / "who"]:
        d.mkdir(parents=True, exist_ok=True)

    # latest ERVISS data (no as_of: later revisions of past weeks are included)
    pv.update_data()
    for name, get in [("ili", pv.get_ili), ("ari", pv.get_ari)]:
        df = get(age_groups="total")
        df.to_csv(raw_dir / f"erviss/{name}_total.csv", index=False)
        pv.coverage(name).to_csv(raw_dir / f"erviss/{name}_coverage.csv", index=False)
        print(f"ERVISS {name}: {len(df)} rows, {df['country_code'].nunique()} countries")

    pos = pv.get_positivity()
    pos.to_csv(raw_dir / "erviss/positivity.csv", index=False)
    print(f"ERVISS positivity: {len(pos)} rows")

    det = pv.get_detections()
    det.to_csv(raw_dir / "erviss/detections.csv", index=False)
    print(f"ERVISS detections: {len(det)} rows")

    # full WHO files -> .sources/who/
    for name, url in WHO.items():
        df = pd.read_csv(url, low_memory=False)
        df.to_csv(sources_dir / f"who/{name}.csv", index=False)
        print(f"WHO {name}: {df.shape[0]} rows, {df.shape[1]} columns (full, in {sources_dir.name}/)")

    # what is used -> target-data/raw/who/
    keep = extract_fluid(sources_dir / "who/fluid_epi.csv", raw_dir / "who/fluid_epi.csv")
    print(f"WHO FluID kept: {len(keep)} rows ({FLUID_KEEP})")
    (raw_dir / "who/metadata.csv").write_bytes((sources_dir / "who/metadata.csv").read_bytes())

    (raw_dir / "SOURCES.md").write_text(
        f"Downloaded on {date.today().isoformat()}\n\n"
        "- erviss/: pyerviss (https://github.com/ngozzi/pyerviss), ILI and ARI, total age group\n"
        "- who/fluid_epi.csv: WHO FluID (VIW_FID_EPI), only the rows of Switzerland and the United Kingdom\n"
        "- who/metadata.csv: WHO data dictionary (VIW_FLU_METADATA)\n"
        "- the full FluID and FluNet (VIW_FNT) files are in .sources/who/ (local only, not in git)\n",
        encoding="utf-8",
    )
