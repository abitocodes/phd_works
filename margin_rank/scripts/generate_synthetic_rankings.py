#!/usr/bin/env python3
"""Generate synthetic GMX-like data for offline pipeline validation."""

from __future__ import annotations

import random
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import load_config, save_json  # noqa: E402
from compute_rankings import compute_rankings  # noqa: E402


def main() -> int:
    config = load_config()
    random.seed(42)

    wallets = [f"0x{'%040x' % i}" for i in range(1, 21)]
    gmx = config["gmx_arbitrum"]
    liq_handler = gmx["liquidation_handler"]
    liq_type = gmx["order_type_liquidation"]
    base_ts = datetime(2026, 5, 25, 12, 0, 0, tzinfo=timezone.utc)

    decoded_rows: list[dict] = []
    for wi, wallet in enumerate(wallets):
        n_closes = random.randint(3, 8)
        win_rate = random.uniform(0.2, 0.9)
        for ci in range(n_closes):
            is_liq = random.random() < 0.05
            if is_liq:
                pnl = -random.randint(100, 5000)
                order_type = liq_type
                msg_sender = liq_handler
            else:
                win = random.random() < win_rate
                pnl = random.randint(50, 3000) if win else -random.randint(50, 3000)
                order_type = 4
                msg_sender = gmx["exchange_router"]

            decoded_rows.append(
                {
                    "block_timestamp": base_ts,
                    "block_number": 300_000_000 + wi * 10 + ci,
                    "transaction_hash": f"0x{'%064x' % (wi * 100 + ci)}",
                    "log_index": ci,
                    "account": wallet,
                    "msg_sender": msg_sender.lower(),
                    "base_pnl_usd": pnl,
                    "order_type": order_type,
                    "is_liquidation": is_liq,
                    "size_delta_usd": 500_000_000_000,
                    "is_long": True,
                }
            )

    raw_path = Path(config["paths"]["raw_logs"])
    decoded_path = Path(config["paths"]["decoded_events"])
    rankings_path = Path(config["paths"]["wallet_rankings"])
    manifest_path = Path(config["paths"]["manifest"])

    # Minimal raw placeholder (real pipeline fills this via BigQuery)
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    decoded_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({"note": ["synthetic — see decoded_events"]}).to_parquet(raw_path, index=False)

    decoded_df = pd.DataFrame(decoded_rows)
    decoded_df.to_parquet(decoded_path, index=False)

    rankings = compute_rankings(decoded_df, config)
    rankings.to_parquet(rankings_path, index=False)

    save_json(
        manifest_path,
        {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "synthetic": True,
            "period": config["period"],
            "protocol": config["protocol"],
            "note": "Offline synthetic data; re-run extract_margin_week.py for real BQ data.",
            "decoded_rows": len(decoded_df),
            "wallets_ranked": len(rankings),
        },
    )
    print(f"Synthetic: {len(decoded_df)} closes -> {len(rankings)} ranked wallets")
    print(f"  rankings: {rankings_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
