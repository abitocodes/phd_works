#!/usr/bin/env python3
"""Generate synthetic parquet when BigQuery credentials are unavailable (local dev only)."""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import PROCESSED_DIR, RAW_DIR, load_config, save_json


def build_budget_plan(config: dict) -> dict:
    """Representative plan (~17 months from 2025-02 to 2026-05)."""
    labels = [
        "2025-02", "2025-03", "2025-04", "2025-05", "2025-06",
        "2025-07", "2025-08", "2025-09", "2025-10", "2025-11",
        "2025-12", "2026-01", "2026-02", "2026-03", "2026-04", "2026-05",
    ]
    month_details = [
        {
            "label": lb,
            "start_ts": f"{lb[:4]}-{lb[5:]}-01 00:00:00 UTC",
            "end_ts": f"{lb[:4]}-{int(lb[5:])+1:02d}-01 00:00:00 UTC"
            if int(lb[5:]) < 12
            else f"{int(lb[:4])+1}-01-01 00:00:00 UTC",
            "start_block": 22000000,
            "end_block": 25218600,
        }
        for lb in labels
    ]
    # Fix end_ts for December
    for m in month_details:
        y, mo = int(m["label"][:4]), int(m["label"][5:])
        if mo == 12:
            m["end_ts"] = f"{y + 1}-01-01 00:00:00 UTC"
        else:
            m["end_ts"] = f"{y}-{mo + 1:02d}-01 00:00:00 UTC"

    return {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "synthetic": True,
        "note": "Generated offline; re-run with GCP credentials for real data.",
        "budget_bytes_limit": config["budget"]["max_total_bytes"],
        "budget_bytes_planned": 500_000_000_000,
        "feature_window": {
            "start_date": "2025-02-01",
            "end_date": config["feature_window"]["end_date"],
            "months_included": len(labels),
            "month_labels": labels,
        },
        "months_included_detail": month_details,
    }


def write_synthetic_data(plan: dict, config: dict) -> dict:
    pools = [p.lower() for p in config["aave_v3_pools"]]
    wallets = [
        "0x1111111111111111111111111111111111111111",
        "0x2222222222222222222222222222222222222222",
        "0x3333333333333333333333333333333333333333",
        "0x4444444444444444444444444444444444444444",
    ]
    tokens = [
        "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48",  # USDC
        "0xdac17f958d2ee523a2206206994597c13d831ec7",  # USDT
    ]

    total_rows = 0
    for mo in plan["months_included_detail"]:
        label = mo["label"]
        ts = pd.Timestamp(f"{label}-15", tz="UTC")

        approvals = pd.DataFrame(
            [
                {
                    "block_timestamp": ts,
                    "block_number": 24000000,
                    "transaction_hash": "0xabc",
                    "log_index": 0,
                    "token_address": tokens[i % 2],
                    "owner": wallets[i % 4],
                    "spender": wallets[(i + 1) % 4],
                    "value": str((i + 1) * 10**12),
                }
                for i in range(50)
            ]
        )
        ap_path = RAW_DIR / "approvals" / f"approvals_{label}.parquet"
        ap_path.parent.mkdir(parents=True, exist_ok=True)
        approvals.to_parquet(ap_path, index=False)
        total_rows += len(approvals)

        transfers = pd.DataFrame(
            [
                {
                    "block_timestamp": ts,
                    "block_number": 24000000,
                    "transaction_hash": "0xdef",
                    "token_address": tokens[i % 2],
                    "from_address": wallets[i % 4],
                    "to_address": wallets[(i + 1) % 4],
                    "value": str((i + 1) * 10**9),
                }
                for i in range(80)
            ]
        )
        tr_path = RAW_DIR / "token_transfers" / f"transfers_{label}.parquet"
        tr_path.parent.mkdir(parents=True, exist_ok=True)
        transfers.to_parquet(tr_path, index=False)
        total_rows += len(transfers)

    liq_dir = RAW_DIR / "aave_liquidations"
    liq_dir.mkdir(parents=True, exist_ok=True)

    feature_liq = pd.DataFrame(
        [
            {
                "block_timestamp": pd.Timestamp("2025-06-01", tz="UTC"),
                "block_number": 23000000,
                "transaction_hash": "0x111",
                "log_index": 0,
                "pool_address": pools[0],
                "collateral_asset": tokens[0],
                "debt_asset": tokens[1],
                "user_address": wallets[2],
                "data": "0x",
            }
        ]
    )
    feature_liq.to_parquet(liq_dir / "liquidations_feature.parquet", index=False)
    total_rows += len(feature_liq)

    outcome_liq = pd.DataFrame(
        [
            {
                "block_timestamp": pd.Timestamp("2026-07-15", tz="UTC"),
                "block_number": 25250000,
                "transaction_hash": "0x222",
                "log_index": 0,
                "pool_address": pools[0],
                "collateral_asset": tokens[0],
                "debt_asset": tokens[1],
                "user_address": wallets[2],
                "data": "0x",
            },
            {
                "block_timestamp": pd.Timestamp("2026-09-01", tz="UTC"),
                "block_number": 25300000,
                "transaction_hash": "0x333",
                "log_index": 1,
                "pool_address": pools[0],
                "collateral_asset": tokens[1],
                "debt_asset": tokens[0],
                "user_address": wallets[3],
                "data": "0x",
            },
        ]
    )
    outcome_liq.to_parquet(liq_dir / "liquidations_outcome_2026-H2.parquet", index=False)
    total_rows += len(outcome_liq)

    manifest = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "synthetic": True,
        "budget_plan": plan,
        "total_bytes_processed": 0,
        "total_rows": total_rows,
        "feature_window": plan["feature_window"],
        "outcome_window": config["outcome_window"],
        "extractions": [{"note": "synthetic offline data"}],
    }
    save_json(PROCESSED_DIR / "extraction_manifest.json", manifest)
    return manifest


def main() -> None:
    config = load_config()
    plan = build_budget_plan(config)
    save_json(PROCESSED_DIR / "budget_plan.json", plan)
    manifest = write_synthetic_data(plan, config)
    print(f"Synthetic budget plan + raw data written ({manifest['total_rows']} rows)")


if __name__ == "__main__":
    main()
