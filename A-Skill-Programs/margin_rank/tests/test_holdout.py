"""Holdout cutoff and label tests (no BigQuery)."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from common import load_config  # noqa: E402
from holdout import (  # noqa: E402
    build_holdout_fixture_frames,
    future_approval_labels,
    holdout_bounds,
    latest_positive_as_of,
    t1_positive_pairs,
)
from run_holdout_eval import run_holdout  # noqa: E402


def test_latest_as_of_drops_post_cutoff_and_revokes() -> None:
    approvals = pd.DataFrame(
        [
            {
                "block_timestamp": "2026-02-01T00:00:00Z",
                "block_number": 1,
                "log_index": 0,
                "token_address": "0xaaa",
                "owner": "0x" + "1" * 40,
                "spender": "0x" + "2" * 40,
                "value": 100,
            },
            {
                "block_timestamp": "2026-04-01T00:00:00Z",
                "block_number": 2,
                "log_index": 0,
                "token_address": "0xaaa",
                "owner": "0x" + "1" * 40,
                "spender": "0x" + "2" * 40,
                "value": 999,
            },
            {
                "block_timestamp": "2026-02-10T00:00:00Z",
                "block_number": 3,
                "log_index": 0,
                "token_address": "0xaaa",
                "owner": "0x" + "3" * 40,
                "spender": "0x" + "2" * 40,
                "value": 0,
            },
        ]
    )
    latest = latest_positive_as_of(approvals, pd.Timestamp("2026-02-28 23:59:59", tz="UTC"))
    assert len(latest) == 1
    assert float(latest.iloc[0]["value"]) == 100


def test_future_new_and_revoke_labels() -> None:
    owner_t1 = "0x" + "a" * 40
    owner_new = "0x" + "b" * 40
    spender = "0x" + "c" * 40
    token = "0x" + "d" * 40
    approvals = pd.DataFrame(
        [
            {
                "block_timestamp": "2026-02-01T00:00:00Z",
                "block_number": 1,
                "log_index": 0,
                "token_address": token,
                "owner": owner_t1,
                "spender": spender,
                "value": 10,
            },
            {
                "block_timestamp": "2026-04-01T00:00:00Z",
                "block_number": 2,
                "log_index": 0,
                "token_address": token,
                "owner": owner_new,
                "spender": spender,
                "value": 5,
            },
            {
                "block_timestamp": "2026-04-02T00:00:00Z",
                "block_number": 3,
                "log_index": 0,
                "token_address": token,
                "owner": owner_t1,
                "spender": spender,
                "value": 0,
            },
        ]
    )
    latest = latest_positive_as_of(approvals, pd.Timestamp("2026-02-28 23:59:59", tz="UTC"))
    assert (owner_t1, spender) in t1_positive_pairs(latest)
    labels = future_approval_labels(
        approvals,
        latest,
        pd.Timestamp("2026-03-01", tz="UTC"),
        pd.Timestamp("2026-05-31", tz="UTC"),
        [spender],
    )
    row = labels.iloc[0]
    assert row["future_new_approvers"] == 1
    assert row["future_revoke_count"] == 1
    assert row["future_revoke_rate"] == 1.0


def test_run_holdout_fixtures_is_t1_vs_t2() -> None:
    config = load_config()
    frames = build_holdout_fixture_frames(n_wallets=24, seed=1)
    summary = run_holdout(
        config,
        frames["approvals"],
        frames["transfers"],
        frames["decoded"],
        frames["wallets"]["wallet"].tolist(),
    )
    assert summary["protocol"] == "t1_score_vs_t2_label"
    score_end, outcome_start, _ = holdout_bounds(config)
    assert pd.Timestamp(summary["score_end"]) == score_end
    assert pd.Timestamp(summary["outcome_start"]) == outcome_start
    assert "endorserank" in summary["methods"]
    assert "awp" in summary["methods"]
    er = summary["alignment"]["methods"]["endorserank"]["future_new_approvers"]
    assert er["n"] >= 5
    assert "kendall_tau" in er
