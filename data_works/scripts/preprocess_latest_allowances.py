#!/usr/bin/env python3
"""Build latest allowance state per (token, owner, spender) from raw approvals."""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import PROCESSED_DIR, RAW_DIR, load_json, normalize_address, save_json


def main() -> None:
    approval_dir = RAW_DIR / "approvals"
    paths = sorted(approval_dir.glob("approvals_*.parquet"))
    if not paths:
        raise FileNotFoundError(f"No approval parquet files in {approval_dir}")

    frames = [pd.read_parquet(p) for p in paths]
    df = pd.concat(frames, ignore_index=True)

    for col in ("owner", "spender", "token_address"):
        if col in df.columns:
            df[col] = df[col].map(lambda x: normalize_address(str(x)) if pd.notna(x) else None)

    df["value"] = pd.to_numeric(df["value"], errors="coerce").fillna(0)
    df = df.sort_values(["block_number", "log_index"], ascending=True)

    latest = df.groupby(["token_address", "owner", "spender"], as_index=False).tail(1)
    latest = latest[latest["value"] > 0].copy()

    out = PROCESSED_DIR / "latest_allowances.parquet"
    out.parent.mkdir(parents=True, exist_ok=True)
    latest.to_parquet(out, index=False)

    manifest = load_json(PROCESSED_DIR / "extraction_manifest.json")
    manifest["preprocess_latest_allowances"] = {
        "at": datetime.now(timezone.utc).isoformat(),
        "input_files": len(paths),
        "input_rows": len(df),
        "output_rows": len(latest),
        "output_path": str(out),
    }
    save_json(PROCESSED_DIR / "extraction_manifest.json", manifest)

    print(f"latest_allowances: {len(latest)} rows -> {out}")


if __name__ == "__main__":
    main()
