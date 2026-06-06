#!/usr/bin/env python3
"""Build binary default labels from outcome-window Aave V3 liquidations."""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import PROCESSED_DIR, RAW_DIR, load_json, normalize_address, save_json


def load_feature_wallets() -> set[str]:
    wallets: set[str] = set()

    allowance_path = PROCESSED_DIR / "latest_allowances.parquet"
    if allowance_path.exists():
        df = pd.read_parquet(allowance_path, columns=["owner", "spender"])
        for col in ("owner", "spender"):
            for v in df[col].dropna().unique():
                w = normalize_address(str(v))
                if w:
                    wallets.add(w)

    feature_liq = RAW_DIR / "aave_liquidations" / "liquidations_feature.parquet"
    if feature_liq.exists():
        df = pd.read_parquet(feature_liq, columns=["user_address"])
        for v in df["user_address"].dropna().unique():
            w = normalize_address(str(v))
            if w:
                wallets.add(w)

    return wallets


def parse_liquidation_users(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["wallet", "defaulted", "first_liquidation_ts"])

    df = df.copy()
    df["wallet"] = df["user_address"].map(lambda x: normalize_address(str(x)) if pd.notna(x) else None)
    df = df.dropna(subset=["wallet"])
    agg = (
        df.groupby("wallet", as_index=False)
        .agg(first_liquidation_ts=("block_timestamp", "min"), liquidation_count=("wallet", "count"))
    )
    agg["defaulted"] = 1
    return agg


def main() -> None:
    outcome_path = RAW_DIR / "aave_liquidations" / "liquidations_outcome_2026-H2.parquet"
    if not outcome_path.exists():
        raise FileNotFoundError(f"Missing {outcome_path}; run extract first.")

    outcome_df = pd.read_parquet(outcome_path)
    defaulted = parse_liquidation_users(outcome_df)

    feature_wallets = load_feature_wallets()
    if not feature_wallets:
        raise RuntimeError("No feature wallets found from allowances or feature liquidations.")

    rows = []
    defaulted_map = defaulted.set_index("wallet")["first_liquidation_ts"].to_dict()
    for w in sorted(feature_wallets):
        rows.append(
            {
                "wallet": w,
                "defaulted": 1 if w in defaulted_map else 0,
                "first_liquidation_ts": defaulted_map.get(w, pd.NaT),
            }
        )

    labels = pd.DataFrame(rows)
    out = PROCESSED_DIR / "default_labels.parquet"
    labels.to_parquet(out, index=False)

    manifest = load_json(PROCESSED_DIR / "extraction_manifest.json")
    manifest["preprocess_default_labels"] = {
        "at": datetime.now(timezone.utc).isoformat(),
        "feature_wallets": len(feature_wallets),
        "defaulted_wallets": int(labels["defaulted"].sum()),
        "outcome_liquidation_rows": len(outcome_df),
        "output_path": str(out),
    }
    save_json(PROCESSED_DIR / "extraction_manifest.json", manifest)

    print(
        f"default_labels: {len(labels)} wallets, "
        f"{int(labels['defaulted'].sum())} defaulted -> {out}"
    )


if __name__ == "__main__":
    main()
