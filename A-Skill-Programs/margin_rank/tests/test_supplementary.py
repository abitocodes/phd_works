"""Proxy orientation, isolated nodes, token selection and spender classes (no BigQuery)."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from check_spender_code import code_kind  # noqa: E402
from classify_spenders import classify  # noqa: E402
from pagerank import weighted_pagerank  # noqa: E402
from proxy_metrics import compute_inverse_risk_proxies  # noqa: E402
from run_robustness_eval import _top_token_addresses  # noqa: E402

SMALL = "0x" + "a" * 40
LARGE = "0x" + "b" * 40


def _closes(account: str, pnls: list[float]) -> list[dict]:
    return [{"account": account, "base_pnl_usd": str(p), "is_liquidation": False} for p in pnls]


def test_inverse_risk_ranks_smaller_losses_higher() -> None:
    decoded = pd.DataFrame(_closes(SMALL, [10, -5, 3]) + _closes(LARGE, [10, -50, 3]))
    out = compute_inverse_risk_proxies(decoded, [SMALL, LARGE]).set_index("wallet")
    assert out.loc[SMALL, "loss_avoidance"] > out.loc[LARGE, "loss_avoidance"]
    assert out.loc[SMALL, "worst_close_pnl_score"] > out.loc[LARGE, "worst_close_pnl_score"]
    assert out.loc[SMALL, "non_loss_close_rate"] == out.loc[LARGE, "non_loss_close_rate"]


def test_isolated_nodes_score_like_nodes_without_in_edges() -> None:
    edges = pd.DataFrame(
        {"from_node": ["a", "a", "b"], "to_node": ["b", "c", "c"], "weight": [1.0, 3.0, 2.0]}
    )
    plain = weighted_pagerank(edges, max_iter=300)
    with_isolated = weighted_pagerank(edges, max_iter=300, extra_nodes={"x", "y"})
    assert with_isolated["x"] == with_isolated["y"] == with_isolated["a"]
    ratios = [with_isolated[n] / plain[n] for n in ("a", "b", "c")]
    assert max(ratios) - min(ratios) < 1e-6


def test_top_tokens_by_value_and_by_count() -> None:
    transfers = pd.DataFrame({"token_address": ["A", "A", "B"], "value": [1.0, 1.0, 1e30]})
    allowances = pd.DataFrame({"token_address": ["C"], "value": [5.0]})
    assert _top_token_addresses(transfers, allowances, 1, rank_by="value") == ["b"]
    assert _top_token_addresses(transfers, allowances, 1, rank_by="count") == ["a"]


def test_spender_classes_from_activity() -> None:
    activity = pd.DataFrame(
        {
            "address": ["0x1", "0x2", "0x2", "0x4"],
            "activity": ["emitted_log", "sent_transaction", "emitted_log", "sent_transaction"],
        }
    )
    out = classify(activity, ["0x1", "0x2", "0x3", "0x4"]).set_index("wallet")["account_type"]
    assert out.to_dict() == {"0x1": "contract", "0x2": "both", "0x3": "inactive", "0x4": "eoa"}


def test_code_kind_separates_contracts_eoas_and_delegations() -> None:
    assert code_kind("0x") == "none"
    assert code_kind(None) == "none"
    assert code_kind("0x6080604052") == "contract"
    assert code_kind("0xef0100" + "ab" * 20) == "eip7702"
    assert code_kind("0xEF0100" + "AB" * 20) == "eip7702"
