"""Download the M5 dataset from Kaggle into data/raw/m5/.

Requires the Kaggle CLI (``pip install kaggle``), Kaggle credentials
(kaggle.json or KAGGLE_USERNAME/KAGGLE_KEY), and acceptance of the competition
rules at https://www.kaggle.com/competitions/m5-forecasting-accuracy.

Usage:
    python scripts/download_m5.py [--dest data/raw/m5]
"""

import argparse
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

COMPETITION = "m5-forecasting-accuracy"
REQUIRED = ("calendar.csv", "sell_prices.csv", "sales_train_evaluation.csv")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dest", type=Path, default=Path("data/raw/m5"))
    dest: Path = parser.parse_args().dest

    if all((dest / name).is_file() for name in REQUIRED):
        print(f"M5 files already present in {dest}; nothing to do.")
        return 0

    if shutil.which("kaggle") is None:
        print(
            "The 'kaggle' CLI is not installed. Install it with `pip install kaggle`,\n"
            "configure credentials (https://www.kaggle.com/docs/api), accept the\n"
            f"competition rules for '{COMPETITION}', then re-run this script.",
            file=sys.stderr,
        )
        return 1

    dest.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        ["kaggle", "competitions", "download", "-c", COMPETITION, "-p", str(dest)],
        check=False,
    )
    if result.returncode != 0:
        print(
            "Kaggle download failed. Check your credentials and that you have\n"
            f"accepted the rules at https://www.kaggle.com/competitions/{COMPETITION}",
            file=sys.stderr,
        )
        return result.returncode

    archive = dest / f"{COMPETITION}.zip"
    if archive.is_file():
        print(f"Extracting {archive} ...")
        with zipfile.ZipFile(archive) as zf:
            zf.extractall(dest)
        archive.unlink()

    missing = [name for name in REQUIRED if not (dest / name).is_file()]
    if missing:
        print(f"Extraction finished but files are missing: {missing}", file=sys.stderr)
        return 1
    print(f"M5 dataset ready in {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
