#!/usr/bin/env python3
"""Generate synthetic Arbitrum approval/transfer data for offline reputation pipeline."""

from __future__ import annotations

import random
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import load_config, load_json, save_json  # noqa: E402


def main() -> int:
    config = load_config()
    random.seed(42)
    rep = config["reputation"]
    rep_paths = rep["paths"]

    rankings_path = Path(config["paths"]["wallet_rankings"])
    if not rankings_path.exists():
        print(f"Missing {rankings_path}; run generate_synthetic_rankings.py first.")
        return 1

    wallets = pd.read_parquet(rankings_path)["wallet"].astype(str).str.lower().tolist()
    n = len(wallets)
    print(f"Generating reputation data for {n} wallets")

    tokens = [
        "0xaf88d065e77c8cc2239327c5edb3a432268e5831",  # USDC Arbitrum
        "0x82af49447d8a07e3bd95bd0d56f35241523fbab1",  # WETH Arbitrum
    ]
    spenders = [
        config["gmx_arbitrum"]["exchange_router"].lower(),
        config["gmx_arbitrum"]["event_emitter"].lower(),
        "0x1111111111111111111111111111111111111111",
    ]

    base_ts = datetime(2026, 1, 1, tzinfo=timezone.utc)
    approval_rows: list[dict] = []
    transfer_rows: list[dict] = []

    for wi, owner in enumerate(wallets):
        for ti, token in enumerate(tokens):
            spender = spenders[(wi + ti) % len(spenders)]
            ts = base_ts + timedelta(days=wi % 120, hours=ti * 3)
            approval_rows.append(
                {
                    "block_timestamp": ts,
                    "block_number": 200_000_000 + wi * 10 + ti,
                    "transaction_hash": f"0x{'a' * 62}{wi:02x}",
                    "log_index": ti,
                    "token_address": token,
                    "owner": owner,
                    "spender": spender,
                    "value": random.randint(1_000, 500_000) * (10**6),
                }
            )

        for j in range(random.randint(2, 6)):
            src = wallets[(wi + j) % n]
            dst = wallets[(wi + j + 3) % n]
            ts = base_ts + timedelta(days=30 + wi % 90, hours=j * 5)
            transfer_rows.append(
                {
                    "block_timestamp": ts,
                    "block_number": 210_000_000 + wi * 20 + j,
                    "transaction_hash": f"0x{'b' * 62}{wi:02x}{j:x}",
                    "log_index": j,
                    "token_address": tokens[j % len(tokens)],
                    "from_address": src,
                    "to_address": dst,
                    "value": float(random.randint(100, 50_000) * (10**12)),
                }
            )

    approvals_dir = Path(rep_paths["raw_approvals_dir"])
    transfers_dir = Path(rep_paths["raw_transfers_dir"])
    approvals_dir.mkdir(parents=True, exist_ok=True)
    transfers_dir.mkdir(parents=True, exist_ok=True)

    app_path = approvals_dir / "approvals_synthetic.parquet"
    tx_path = transfers_dir / "transfers_synthetic.parquet"
    pd.DataFrame(approval_rows).to_parquet(app_path, index=False)
    pd.DataFrame(transfer_rows).to_parquet(tx_path, index=False)

    manifest_path = Path(config["paths"]["manifest"])
    manifest = load_json(manifest_path)
    manifest["reputation_synthetic"] = {
        "at": datetime.now(timezone.utc).isoformat(),
        "approval_rows": len(approval_rows),
        "transfer_rows": len(transfer_rows),
        "wallets": n,
    }
    save_json(manifest_path, manifest)
    print(f"Synthetic approvals: {len(approval_rows)} -> {app_path}")
    print(f"Synthetic transfers: {len(transfer_rows)} -> {tx_path}")

    scripts_dir = Path(__file__).resolve().parent
    steps = [
        [sys.executable, str(scripts_dir / "preprocess_arbitrum_allowances.py")],
        [sys.executable, str(scripts_dir / "preprocess_arbitrum_transfers.py")],
        [sys.executable, str(scripts_dir / "compute_reputation_ranks.py")],
    ]
    for cmd in steps:
        print(f"Running: {' '.join(cmd)}")
        rc = subprocess.call(cmd)
        if rc != 0:
            return rc

    print("Reputation pipeline complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
