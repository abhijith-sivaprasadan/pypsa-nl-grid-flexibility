from __future__ import annotations

from pathlib import Path
from urllib.request import urlretrieve


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
OUTPUT_FILE = RAW_DIR / "opsd_time_series_60min_singleindex.csv"
OPSD_URL = (
    "https://data.open-power-system-data.org/time_series/2020-10-06/"
    "time_series_60min_singleindex.csv"
)


def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Downloading OPSD hourly time-series data to {OUTPUT_FILE}")
    print("Source:", OPSD_URL)
    urlretrieve(OPSD_URL, OUTPUT_FILE)
    print("Done.")
    print(
        "To use this file, set model.profile_source: 'opsd' "
        "in config/model_config.yaml."
    )


if __name__ == "__main__":
    main()
