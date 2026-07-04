#!/usr/bin/env python3
"""Tier-3 robustness checks: damping sweep, top-token subgraph, sample-size sensitivity."""

from __future__ import annotations

import time
from typing import Any

import pandas as pd

from benchmark_runtime import benchmark_er_awp_pair, subsample_wallets_deterministic
from evaluate_alignment import (
    DISSERTATION_METHODS,
    PROXY_FAMILIES,
    _correlate,
    build_alignment_report,
)
from pagerank import (
    assign_dense_ranks,
    build_awp_edges,
    build_endorserank_edges,
    filter_subgraph_edges,
    weighted_pagerank,
)
from proxy_metrics import (
    compute_all_proxies,
    compute_gmx_success_proxies,
    compute_gmx_success_proxies_size_weighted,
)


def _top_token_addresses(transfers: pd.DataFrame, allowances: pd.DataFrame, top_n: int) -> list[str]:
    """Rank ERC-20 tokens by total transfer value in the cohort parquet."""
    volumes: dict[str, float] = {}
    if not transfers.empty and "token_address" in transfers.columns:
        t = transfers.copy()
        t["token_address"] = t["token_address"].astype(str).str.lower()
        t["value"] = pd.to_numeric(t["value"], errors="coerce").fillna(0.0)
        for tok, val in t.groupby("token_address")["value"].sum().items():
            volumes[str(tok).lower()] = volumes.get(str(tok).lower(), 0.0) + float(val)
    if not allowances.empty and "token_address" in allowances.columns:
        a = allowances.copy()
        a["token_address"] = a["token_address"].astype(str).str.lower()
        a["value"] = pd.to_numeric(a["value"], errors="coerce").fillna(0.0)
        for tok, val in a.groupby("token_address")["value"].sum().items():
            volumes[str(tok).lower()] = volumes.get(str(tok).lower(), 0.0) + float(val)
    ranked = sorted(volumes.items(), key=lambda x: x[1], reverse=True)
    return [tok for tok, _ in ranked[:top_n]]


def _filter_by_tokens(df: pd.DataFrame, tokens: set[str], token_col: str = "token_address") -> pd.DataFrame:
    if df.empty or token_col not in df.columns:
        return df.copy()
    work = df.copy()
    work[token_col] = work[token_col].astype(str).str.lower()
    return work[work[token_col].isin(tokens)].copy()


def _scores_for_damping(
    wallets: list[str],
    allowances: pd.DataFrame,
    transfers: pd.DataFrame,
    config: dict,
    damping: float,
) -> tuple[pd.Series, pd.Series]:
    """Recompute EndorseRank and AWP scores at a given damping factor."""
    rep = config["reputation"]
    seed = {w.lower() for w in wallets}
    observation_end = pd.Timestamp(rep["observation_end"], tz="UTC")
    er_edges = filter_subgraph_edges(build_endorserank_edges(allowances), seed)
    awp_edges = filter_subgraph_edges(
        build_awp_edges(
            transfers,
            observation_end=observation_end,
            k=float(rep["awp_decay_k"]),
            t0_days=float(rep["awp_decay_t0_days"]),
        ),
        seed,
    )
    tol = float(rep["pagerank_tolerance"])
    max_iter = int(rep["max_iterations"])

    er_scores = weighted_pagerank(er_edges, damping=damping, tol=tol, max_iter=max_iter)
    awp_scores = weighted_pagerank(awp_edges, damping=damping, tol=tol, max_iter=max_iter)

    er_df = assign_dense_ranks(wallets, er_scores)
    awp_df = assign_dense_ranks(wallets, awp_scores)
    er_series = er_df.set_index("wallet")["score"].reindex([w.lower() for w in wallets]).fillna(0.0)
    awp_series = awp_df.set_index("wallet")["score"].reindex([w.lower() for w in wallets]).fillna(0.0)
    return er_series, awp_series


def _alignment_from_scores(
    wallets: list[str],
    er_scores: pd.Series,
    awp_scores: pd.Series,
    proxies: pd.DataFrame,
) -> dict[str, Any]:
    base = proxies.copy()
    base["wallet"] = base["wallet"].astype(str).str.lower()
    base["endorserank_score"] = base["wallet"].map(er_scores.to_dict())
    base["awp_score"] = base["wallet"].map(awp_scores.to_dict())
    return build_alignment_report(base, methods=DISSERTATION_METHODS)


def run_damping_sweep(
    wallets: list[str],
    allowances: pd.DataFrame,
    transfers: pd.DataFrame,
    decoded: pd.DataFrame,
    config: dict,
    min_closes: int,
    repeats: int = 3,
) -> dict[str, Any]:
    rob = config.get("robustness") or {}
    damping_values = [float(d) for d in rob.get("damping_values", [0.75, 0.85, 0.95])]
    proxies = compute_all_proxies(transfers, allowances, decoded, wallets, min_closes=min_closes)

    rows: list[dict[str, Any]] = []
    for damping in damping_values:
        t0 = time.perf_counter()
        er_scores, awp_scores = _scores_for_damping(wallets, allowances, transfers, config, damping)
        align = _alignment_from_scores(wallets, er_scores, awp_scores, proxies)
        bench = benchmark_er_awp_pair(
            wallets,
            allowances,
            transfers,
            {**config, "reputation": {**config["reputation"], "damping": damping}},
            repeats=repeats,
        )
        er_cross = align["method_cross_proxy"].get("endorserank", {})
        awp_cross = align["method_cross_proxy"].get("awp", {})
        row: dict[str, Any] = {
            "damping": damping,
            "elapsed_sec": round(time.perf_counter() - t0, 3),
            "endorserank_runtime_sec": bench["endorserank"]["runtime_sec_mean"],
            "awp_runtime_sec": bench["awp"]["runtime_sec_mean"],
        }
        for family in PROXY_FAMILIES:
            key = f"{family}_mean_tau"
            row[f"er_{family}_tau"] = er_cross.get(key)
            row[f"awp_{family}_tau"] = awp_cross.get(key)
        rows.append(row)

    return {"damping_values": damping_values, "rows": rows, "n_wallets": len(wallets)}


def run_top_token_sweep(
    wallets: list[str],
    allowances: pd.DataFrame,
    transfers: pd.DataFrame,
    decoded: pd.DataFrame,
    config: dict,
    min_closes: int,
) -> dict[str, Any]:
    rob = config.get("robustness") or {}
    top_n = int(rob.get("top_n_tokens", 20))
    tokens = _top_token_addresses(transfers, allowances, top_n)
    token_set = set(tokens)

    filt_allow = _filter_by_tokens(allowances, token_set)
    filt_trans = _filter_by_tokens(transfers, token_set)

    rep = config["reputation"]
    damping = float(rep["damping"])
    er_scores, awp_scores = _scores_for_damping(wallets, filt_allow, filt_trans, config, damping)
    proxies = compute_all_proxies(filt_trans, filt_allow, decoded, wallets, min_closes=min_closes)
    align = _alignment_from_scores(wallets, er_scores, awp_scores, proxies)

    return {
        "top_n_tokens": top_n,
        "token_count_used": len(tokens),
        "tokens_sample": tokens[:5],
        "n_wallets": len(wallets),
        "method_proxy_matrix": align["method_proxy_matrix"],
        "method_cross_proxy": align["method_cross_proxy"],
        "edge_counts": {
            "allowance_rows": len(filt_allow),
            "transfer_rows": len(filt_trans),
        },
    }


def run_sample_size_sweep(
    wallet_pool: list[str],
    allowances: pd.DataFrame,
    transfers: pd.DataFrame,
    decoded: pd.DataFrame,
    config: dict,
    min_closes: int,
    repeats: int = 3,
) -> dict[str, Any]:
    rob = config.get("robustness") or {}
    bench = config.get("benchmark") or {}
    seed = str(bench.get("tier2_scaling_seed", "benchmark-tier2-v1"))
    requested = [int(s) for s in rob.get("sample_sizes", [50000, 200000])]
    tier2_stages = [int(s) for s in bench.get("stages", [10000, 50000, 100000])]
    pool_n = len(wallet_pool)
    stage_candidates = sorted(set(requested + tier2_stages))
    stages = sorted({s for s in stage_candidates if 0 < s <= pool_n})
    if pool_n not in stages and pool_n > 0:
        stages.append(pool_n)

    rep = config["reputation"]
    damping = float(rep["damping"])
    rows: list[dict[str, Any]] = []

    for n in stages:
        subset = subsample_wallets_deterministic(wallet_pool, n, seed=seed)
        proxies = compute_all_proxies(transfers, allowances, decoded, subset, min_closes=min_closes)
        er_scores, awp_scores = _scores_for_damping(subset, allowances, transfers, config, damping)
        align = _alignment_from_scores(subset, er_scores, awp_scores, proxies)
        bench_result = benchmark_er_awp_pair(
            subset, allowances, transfers, config, repeats=repeats
        )
        er_cross = align["method_cross_proxy"].get("endorserank", {})
        awp_cross = align["method_cross_proxy"].get("awp", {})
        rows.append(
            {
                "n_wallets": n,
                "scaling_seed": seed,
                "endorserank_runtime_sec": bench_result["endorserank"]["runtime_sec_mean"],
                "awp_runtime_sec": bench_result["awp"]["runtime_sec_mean"],
                "er_speedup_ratio": round(
                    bench_result["awp"]["runtime_sec_mean"]
                    / max(bench_result["endorserank"]["runtime_sec_mean"], 1e-9),
                    2,
                ),
                "er_allowance_tau": er_cross.get("allowance_mean_tau"),
                "awp_allowance_tau": awp_cross.get("allowance_mean_tau"),
                "er_transfer_tau": er_cross.get("transfer_mean_tau"),
                "awp_transfer_tau": awp_cross.get("transfer_mean_tau"),
            }
        )

    return {
        "scaling_seed": seed,
        "wallet_pool_size": pool_n,
        "requested_sizes": requested,
        "stages": stages,
        "rows": rows,
    }


def run_gmx_proxy_variant_check(
    wallets: list[str],
    decoded: pd.DataFrame,
    merged_scores: pd.DataFrame,
) -> dict[str, Any]:
    """Compare Kendall tau when GMX realized_gain_proxy uses raw sum vs size-weighted sum."""
    raw_proxies = compute_gmx_success_proxies(decoded, wallets)
    sized_proxies = compute_gmx_success_proxies_size_weighted(decoded, wallets)

    rows: list[dict[str, Any]] = []
    for method_id, score_col in DISSERTATION_METHODS.items():
        if score_col not in merged_scores.columns:
            continue
        scores = merged_scores.set_index("wallet")[score_col]
        for variant, frame in (
            ("raw_sum", raw_proxies),
            ("size_weighted", sized_proxies),
        ):
            proxy = frame.set_index("wallet")["realized_gain_proxy"]
            aligned = scores.reindex(proxy.index).astype(float)
            corr = _correlate(aligned, proxy.astype(float))
            rows.append(
                {
                    "method": method_id,
                    "variant": variant,
                    "realized_gain_kendall_tau": corr["kendall_tau"],
                    "realized_gain_spearman_rho": corr["spearman_rho"],
                    "n": corr["n"],
                }
            )

    return {"rows": rows}


def run_robustness_eval(
    wallets: list[str],
    wallet_pool: list[str],
    allowances: pd.DataFrame,
    transfers: pd.DataFrame,
    decoded: pd.DataFrame,
    merged_scores: pd.DataFrame,
    config: dict,
    min_closes: int,
    repeats: int = 3,
) -> dict[str, Any]:
    """Run all Tier-3 robustness checks."""
    return {
        "damping_sweep": run_damping_sweep(
            wallets, allowances, transfers, decoded, config, min_closes, repeats=repeats
        ),
        "top_token_subgraph": run_top_token_sweep(
            wallets, allowances, transfers, decoded, config, min_closes
        ),
        "sample_size_sweep": run_sample_size_sweep(
            wallet_pool, allowances, transfers, decoded, config, min_closes, repeats=repeats
        ),
        "gmx_proxy_variants": run_gmx_proxy_variant_check(wallets, decoded, merged_scores),
    }
