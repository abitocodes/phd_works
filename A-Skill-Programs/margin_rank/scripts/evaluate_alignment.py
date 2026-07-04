"""Spearman rho and Kendall tau alignment between reputation scores and proxies."""



from __future__ import annotations



from typing import Any



import pandas as pd

from scipy.stats import kendalltau, spearmanr



TRANSFER_PROXIES = ("in_degree", "in_value")

ALLOWANCE_PROXIES = ("in_approve_degree", "in_approve_value")

LIQUIDATION_PROXIES = (

    "liquidation_free_rate",

    "zero_liquidation_flag",

    "liquidation_free_closes",

)

INVERSE_RISK_PROXIES = (

    "loss_avoidance",

    "non_loss_close_rate",

    "worst_close_pnl_score",

)

SYBIL_PROXIES = (

    "inbound_counterparty_ratio",

    "transfer_tenure_days",

    "active_months",

)

GMX_PROXIES = ("close_success_count", "realized_gain_proxy", "close_success_rate")



PROXY_FAMILIES: dict[str, tuple[str, ...]] = {

    "transfer": TRANSFER_PROXIES,

    "allowance": ALLOWANCE_PROXIES,

    "liquidation": LIQUIDATION_PROXIES,

    "inverse_risk": INVERSE_RISK_PROXIES,

    "sybil_stability": SYBIL_PROXIES,

    "gmx_success": GMX_PROXIES,

}



ALL_PROXIES = tuple(p for proxies in PROXY_FAMILIES.values() for p in proxies)



DISSERTATION_METHODS: dict[str, str] = {

    "endorserank": "endorserank_score",

    "awp": "awp_score",

    "gf_pr": "gf_pr_score",

}



METHODS: dict[str, str] = {

    "awp": "awp_score",

    "endorserank": "endorserank_score",

    "gf_pr": "gf_pr_score",

    "lp_pr": "lp_pr_score",

    "cw_awp": "cw_awp_score",

    "lf_pr": "lf_pr_score",

    "riskprop_pr": "riskprop_pr_score",

}



METHOD_LABELS: dict[str, str] = {

    "awp": "AWP",

    "endorserank": "EndorseRank",

    "gf_pr": "GF-PR",

    "lp_pr": "LP-PR",

    "cw_awp": "CW-AWP",

    "lf_pr": "LF-PR",

    "riskprop_pr": "RiskProp",

}


SIX_AAVE_METHODS: dict[str, str] = {

    "awp": "awp_score",

    "endorserank": "endorserank_score",

    "liq_pr": "liq_pr_score",

    "borrow_pr": "borrow_pr_score",

    "repay_pr": "repay_pr_score",

    "delegation_pr": "delegation_pr_score",

}


SIX_AAVE_DIAGNOSTIC_METHODS: dict[str, str] = {

    "borrow_pr_pool": "borrow_pr_pool_score",

    "repay_pr_pool": "repay_pr_pool_score",

}


SIX_AAVE_LABELS: dict[str, str] = {

    "awp": "AWP",

    "endorserank": "EndorseRank",

    "liq_pr": "LiqCall-PR",

    "borrow_pr": "Borrow-PR",

    "repay_pr": "Repay-PR",

    "delegation_pr": "Delegation-PR",

}





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

    if score_col not in df.columns:

        return out

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





def _cross_proxy_means(method_results: dict[str, dict[str, Any]]) -> dict[str, float | None]:

    return {

        f"{family}_mean_tau": mean_tau(method_results, proxies)

        for family, proxies in PROXY_FAMILIES.items()

    }





def _method_comparison(

    er_cross: dict[str, float | None],

    awp_cross: dict[str, float | None],

) -> dict[str, dict[str, Any]]:

    out: dict[str, dict[str, Any]] = {}

    for family in PROXY_FAMILIES:

        key = f"{family}_mean_tau"

        er_tau = er_cross.get(key)

        awp_tau = awp_cross.get(key)

        diff = None

        winner = None

        if er_tau is not None and awp_tau is not None:

            diff = float(er_tau - awp_tau)

            if abs(diff) < 1e-9:

                winner = "tie"

            elif diff > 0:

                winner = "EndorseRank"

            else:

                winner = "AWP"

        out[family] = {

            "endorserank_mean_tau": er_tau,

            "awp_mean_tau": awp_tau,

            "delta_er_minus_awp": diff,

            "higher_alignment": winner,

        }

    return out





def build_method_proxy_matrix(

    method_cross: dict[str, dict[str, float | None]],

    methods: dict[str, str] | None = None,

) -> dict[str, dict[str, float | None]]:

    """method_id -> family -> mean_tau."""

    method_ids = methods if methods is not None else METHODS

    matrix: dict[str, dict[str, float | None]] = {}

    for method_id in method_ids:

        cross = method_cross.get(method_id, {})

        matrix[method_id] = {

            family: cross.get(f"{family}_mean_tau") for family in PROXY_FAMILIES

        }

    return matrix





def build_family_winners(

    matrix: dict[str, dict[str, float | None]],

    methods: dict[str, str] | None = None,

) -> dict[str, str | None]:

    method_ids = methods if methods is not None else METHODS

    winners: dict[str, str | None] = {}

    for family in PROXY_FAMILIES:

        best_method: str | None = None

        best_tau: float | None = None

        for method_id in method_ids:

            row = matrix.get(method_id, {})

            tau = row.get(family)

            if tau is None:

                continue

            if best_tau is None or tau > best_tau:

                best_tau = tau

                best_method = method_id

        winners[family] = best_method

    return winners





def _build_method_cross(

    merged: pd.DataFrame,

    methods: dict[str, str],

) -> tuple[dict[str, dict[str, dict[str, Any]]], dict[str, dict[str, float | None]]]:

    method_results: dict[str, dict[str, dict[str, Any]]] = {}

    method_cross: dict[str, dict[str, float | None]] = {}

    for method_id, score_col in methods.items():

        if score_col not in merged.columns:

            continue

        res = evaluate_method(merged, score_col, ALL_PROXIES)

        method_results[method_id] = res

        method_cross[method_id] = _cross_proxy_means(res)

    return method_results, method_cross





def build_alignment_report(

    merged: pd.DataFrame,

    methods: dict[str, str] | None = None,

) -> dict[str, Any]:

    """Full alignment report for methods across six proxy families."""

    methods_dict = methods if methods is not None else METHODS

    method_results, method_cross = _build_method_cross(merged, methods_dict)



    matrix = build_method_proxy_matrix(method_cross, methods_dict)

    family_winners = build_family_winners(matrix, methods_dict)



    er = method_results.get("endorserank", {})

    awp_res = method_results.get("awp", {})

    er_cross = method_cross.get("endorserank", _cross_proxy_means(er))

    awp_cross = method_cross.get("awp", _cross_proxy_means(awp_res))



    inter_method: dict[str, Any] = {}

    if "endorserank_score" in merged.columns and "awp_score" in merged.columns:

        inter_method = _correlate(merged["endorserank_score"], merged["awp_score"])



    return {

        "methods": method_results,

        "method_cross_proxy": method_cross,

        "method_proxy_matrix": matrix,

        "family_winners": family_winners,

        "endorserank": er,

        "awp": awp_res,

        "endorserank_cross_proxy": er_cross,

        "awp_cross_proxy": awp_cross,

        "method_comparison": _method_comparison(er_cross, awp_cross),

        "inter_method": inter_method,

        "n_wallets": len(merged),

        "awp_cross_proxy_legacy": {

            "transfer_family_mean_tau": awp_cross.get("transfer_mean_tau"),

            "gmx_family_mean_tau": awp_cross.get("gmx_success_mean_tau"),

        },

        "endorserank_cross_proxy_legacy": {

            "transfer_family_mean_tau": er_cross.get("transfer_mean_tau"),

            "gmx_family_mean_tau": er_cross.get("gmx_success_mean_tau"),

        },

    }





def build_six_aave_alignment_report(merged: pd.DataFrame) -> dict[str, Any]:

    """Six-Aave preset alignment (EndorseRank, AWP, four Aave W↔W methods)."""

    all_methods = {**SIX_AAVE_METHODS, **SIX_AAVE_DIAGNOSTIC_METHODS}

    method_results, method_cross = _build_method_cross(merged, all_methods)

    matrix = build_method_proxy_matrix(method_cross, SIX_AAVE_METHODS)

    family_winners = build_family_winners(matrix, SIX_AAVE_METHODS)

    er_cross = method_cross.get("endorserank", {})

    awp_cross = method_cross.get("awp", {})

    return {

        "methods": {k: method_results[k] for k in SIX_AAVE_METHODS if k in method_results},

        "method_cross_proxy": {k: method_cross[k] for k in SIX_AAVE_METHODS if k in method_cross},

        "method_proxy_matrix": matrix,

        "family_winners": family_winners,

        "method_comparison": _method_comparison(er_cross, awp_cross),

        "diagnostic_methods": {

            k: method_cross.get(k, {}) for k in SIX_AAVE_DIAGNOSTIC_METHODS

        },

        "diagnostic_matrix": build_method_proxy_matrix(method_cross, SIX_AAVE_DIAGNOSTIC_METHODS),

        "n_wallets": len(merged),

    }

