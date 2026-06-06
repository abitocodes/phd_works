#!/usr/bin/env python3
"""Write 1000-row sample CSVs from parquet outputs for git-friendly inspection."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import PROCESSED_DIR, RAW_DIR, SAMPLES_DIR, load_json, save_json

SAMPLE_N = 1000


def sample_parquet(src: Path, dest: Path, n: int = SAMPLE_N) -> int:
    if not src.exists():
        print(f"Skip missing: {src}")
        return 0
    df = pd.read_parquet(src)
    sample = df.head(n)
    dest.parent.mkdir(parents=True, exist_ok=True)
    sample.to_csv(dest, index=False)
    return len(sample)


def main() -> None:
    SAMPLES_DIR.mkdir(parents=True, exist_ok=True)

    results: dict = {"samples": []}

    # Raw approvals — first available month
    approval_files = sorted((RAW_DIR / "approvals").glob("approvals_*.parquet"))
    if approval_files:
        dest = SAMPLES_DIR / "approvals_sample.csv"
        n = sample_parquet(approval_files[0], dest)
        results["samples"].append({"file": str(dest), "rows": n, "source": str(approval_files[0])})

    transfer_files = sorted((RAW_DIR / "token_transfers").glob("transfers_*.parquet"))
    if transfer_files:
        dest = SAMPLES_DIR / "transfers_sample.csv"
        n = sample_parquet(transfer_files[0], dest)
        results["samples"].append({"file": str(dest), "rows": n, "source": str(transfer_files[0])})

    liq_outcome = RAW_DIR / "aave_liquidations" / "liquidations_outcome_2026-H2.parquet"
    if liq_outcome.exists():
        dest = SAMPLES_DIR / "liquidations_sample.csv"
        n = sample_parquet(liq_outcome, dest)
        results["samples"].append({"file": str(dest), "rows": n, "source": str(liq_outcome)})

    for name in ("latest_allowances", "transfer_edges", "default_labels"):
        src = PROCESSED_DIR / f"{name}.parquet"
        if src.exists():
            dest = SAMPLES_DIR / f"{name}_sample.csv"
            n = sample_parquet(src, dest)
            results["samples"].append({"file": str(dest), "rows": n, "source": str(src)})

    manifest = load_json(PROCESSED_DIR / "extraction_manifest.json")
    manifest["samples"] = results
    save_json(PROCESSED_DIR / "extraction_manifest.json", manifest)

    print(f"Wrote {len(results['samples'])} sample CSV files to {SAMPLES_DIR}")


if __name__ == "__main__":
    main()
