from __future__ import annotations

from pathlib import Path

import pandas as pd


ADS_DIR = Path(__file__).resolve().parent
INPUT_DIR = ADS_DIR / "ads_output"
OUTPUT_DIR = ADS_DIR / "preview"


def main() -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)
    parquet_files = sorted(INPUT_DIR.glob("*.parquet"))
    for path in parquet_files:
        df = pd.read_parquet(path).head(20)
        target = OUTPUT_DIR / f"{path.stem}_preview.csv"
        df.to_csv(target, index=False, encoding="utf-8-sig")
        print(target.name, flush=True)


if __name__ == "__main__":
    main()
