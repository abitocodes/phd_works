"""Spearman rho and Kendall tau alignment between reputation scores and proxies."""

from __future__ import annotations

from typing import Any

import pandas as pd
from scipy.stats import kendalltau, spearmanr


TRANSFER_PROXIES = ("in_degree", "in_value")
GMX_PROXIES = ("close_success_count", "realized_gain_proxy", "close_success_rate")


def _correlate(scores: pd.Series, proxy: pd.Series) -> dict[str, float | None]:
    mask = scores.notna() & proxy.notna()
    if mask.sum() < 5:
        return {"spearman_rho": None, "kendall_tau": None, "n": int(mask.sum())}
    x = scores[mask].astype(float)
    y = proxy[mask].astype(float)
    if x.nunique() < 2 or y.nunique() < 2:
        return {"spearman_rho": None, "kendall_tau": None, "n": int(mask.sum())}
    rho, _ = spearmanr(x, y)
    tau, _ = kendalltau(x, y)
    return {"spearman_rho": float(rho), "kendall_tau": float(tau), "n": int(mask.sum())}


def evaluate_method(
    df: pd.DataFrame,
    score_col: str,
    proxy_cols: tuple[str, ...],
) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    scores = df[score_col]
    for proxy in proxy_cols:
        if proxy not in df.columns:
            continue
        out[proxy] = _correlate(scores, df[proxy])
    return out


def mean_tau(results: dict[str, dict[str, Any]], proxies: tuple[str, ...]) -> float | None:
    vals = [
        results[p]["kendall_tau"]
        for p in proxies
        if p in results and results[p]["kendall_tau"] is not None
    ]
    return float(sum(vals) / len(vals)) if vals else None


def build_alignment_report(
    merged: pd.DataFrame,
) -> dict[str, Any]:
    """Full alignment report for EndorseRank and AWP."""
    er = evaluate_method(merged, "endorserank_score", TRANSFER_PROXIES + GMX_PROXIES)
    awp = evaluate_method(merged, "awp_score", TRANSFER_PROXIES + GMX_PROXIES)

    return {
        "endorserank": er,
        "awp": awp,
        "awp_cross_proxy": {
            "transfer_family_mean_tau": mean_tau(awp, TRANSFER_PROXIES),
            "gmx_family_mean_tau": mean_tau(awp, GMX_PROXIES),
        },
        "endorserank_cross_proxy": {
            "transfer_family_mean_tau": mean_tau(er, TRANSFER_PROXIES),
            "gmx_family_mean_tau": mean_tau(er, GMX_PROXIES),
        },
        "n_wallets": len(merged),
    }
