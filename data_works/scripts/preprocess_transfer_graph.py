#!/usr/bin/env python3
"""Aggregate token transfers into directed edges for AWP baseline graph."""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import PROCESSED_DIR, RAW_DIR, load_json, normalize_address, save_json


def main() -> None:
    transfer_dir = RAW_DIR / "token_transfers"
    paths = sorted(transfer_dir.glob("transfers_*.parquet"))
    if not paths:
        raise FileNotFoundError(f"No transfer parquet files in {transfer_dir}")

    frames = [pd.read_parquet(p) for p in paths]
    df = pd.concat(frames, ignore_index=True)

    for col in ("from_address", "to_address", "token_address"):
        if col in df.columns:
            df[col] = df[col].map(lambda x: normalize_address(str(x)) if pd.notna(x) else None)

    df["value"] = pd.to_numeric(df["value"], errors="coerce").fillna(0)

    edges = (
        df.groupby(["from_address", "to_address"], as_index=False)["value"]
        .sum()
        .rename(columns={"from_address": "from_wallet", "to_address": "to_wallet", "value": "total_value"})
    )

    out = PROCESSED_DIR / "transfer_edges.parquet"
    edges.to_parquet(out, index=False)

    manifest = load_json(PROCESSED_DIR / "extraction_manifest.json")
    manifest["preprocess_transfer_graph"] = {
        "at": datetime.now(timezone.utc).isoformat(),
        "input_files": len(paths),
        "input_rows": len(df),
        "output_edges": len(edges),
        "output_path": str(out),
    }
    save_json(PROCESSED_DIR / "extraction_manifest.json", manifest)

    print(f"transfer_edges: {len(edges)} edges -> {out}")


if __name__ == "__main__":
    main()
