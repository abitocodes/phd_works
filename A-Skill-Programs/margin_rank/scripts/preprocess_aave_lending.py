#!/usr/bin/env python3
"""Decode Aave V3 lending logs into user-pool events for LF-PR."""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import load_config, load_json, normalize_address, parse_token_amount, save_json  # noqa: E402


def _topic_addr(topic: str | None) -> str | None:
    return normalize_address(topic)


def _data_word(data: str | None, index: int) -> str:
    if data is None or (isinstance(data, float) and pd.isna(data)):
        return "0"
    s = str(data).strip()
    if s.startswith("0x"):
        s = s[2:]
    start = index * 64
    chunk = s[start : start + 64]
    if not chunk:
        return "0"
    try:
        return str(int(chunk, 16))
    except ValueError:
        return "0"


def decode_row(row: pd.Series, topics: dict[str, str]) -> dict | None:
    topic0 = str(row.get("topic0", "")).lower()
    pool = normalize_address(row.get("pool_address"))

    if topic0 == topics["borrow"].lower():
        user = _topic_addr(row.get("topic2"))  # onBehalfOf
        amount = parse_token_amount(_data_word(row.get("event_data"), 1))
        return {"user": user, "pool": pool, "amount": amount, "event_type": "borrow"}

    if topic0 == topics["repay"].lower():
        user = _topic_addr(row.get("topic2"))
        amount = parse_token_amount(_data_word(row.get("event_data"), 0))
        return {"user": user, "pool": pool, "amount": amount, "event_type": "repay"}

    if topic0 == topics["liquidation_call"].lower():
        user = _topic_addr(row.get("topic3"))
        amount = parse_token_amount(_data_word(row.get("event_data"), 0))
        return {
            "user": user,
            "pool": pool,
            "amount": amount,
            "event_type": "liquidation_call",
        }

    return None


def load_raw_frames(raw_dir: Path) -> pd.DataFrame:
    combined = raw_dir / "aave_events_arbitrum.parquet"
    if combined.exists():
        return pd.read_parquet(combined)
    paths = sorted(raw_dir.glob("aave_events_*.parquet"))
    if not paths:
        raise FileNotFoundError(f"No Aave parquet files in {raw_dir}")
    return pd.concat([pd.read_parquet(p) for p in paths], ignore_index=True)


def main() -> int:
    config = load_config()
    raw_dir = Path(config["paths"]["raw_lending_dir"])
    out_path = Path(config["paths"]["aave_events"])
    topics = config["aave_arbitrum"]["event_topics"]

    df = load_raw_frames(raw_dir)
    rows: list[dict] = []
    for _, row in df.iterrows():
        decoded = decode_row(row, topics)
        if decoded and decoded["user"] and decoded["amount"] > 0:
            rows.append(
                {
                    **decoded,
                    "block_timestamp": row.get("block_timestamp"),
                    "block_number": row.get("block_number"),
                    "transaction_hash": row.get("transaction_hash"),
                    "log_index": row.get("log_index"),
                }
            )

    out = pd.DataFrame(rows)
    if not out.empty:
        out["user"] = out["user"].astype(str).str.lower()
        out["pool"] = out["pool"].astype(str).str.lower()
        out["block_timestamp"] = pd.to_datetime(out["block_timestamp"], utc=True)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_parquet(out_path, index=False)

    manifest_path = Path(config["paths"]["manifest"])
    manifest = load_json(manifest_path)
    manifest["preprocess_aave_lending"] = {
        "at": datetime.now(timezone.utc).isoformat(),
        "input_rows": len(df),
        "output_rows": len(out),
        "output_path": str(out_path),
    }
    save_json(manifest_path, manifest)
    print(f"aave_events: {len(out)} rows -> {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
