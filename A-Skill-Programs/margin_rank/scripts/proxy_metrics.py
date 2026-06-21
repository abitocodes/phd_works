"""Compute transfer and GMX validation proxy metrics per wallet."""

from __future__ import annotations

import pandas as pd


def compute_transfer_proxies(transfers: pd.DataFrame, wallets: list[str]) -> pd.DataFrame:
    """Do et al. (2023) style in-degree and in-value from inbound transfers."""
    work = transfers.copy()
    work["to_address"] = work["to_address"].astype(str).str.lower()
    work["from_address"] = work["from_address"].astype(str).str.lower()
    work["value"] = work["value"].astype(float)

    inbound = work[work["to_address"].isin(wallets)]
    agg = (
        inbound.groupby("to_address", as_index=False)
        .agg(
            in_degree=("from_address", "nunique"),
            in_value=("value", "sum"),
        )
        .rename(columns={"to_address": "wallet"})
    )

    base = pd.DataFrame({"wallet": wallets})
    return base.merge(agg, on="wallet", how="left").fillna({"in_degree": 0, "in_value": 0.0})


def compute_gmx_proxies(
    decoded: pd.DataFrame,
    rankings: pd.DataFrame,
    min_closes: int = 3,
) -> pd.DataFrame:
    """GMX margin-trading success proxies for matched wallets."""
    work = decoded.copy()
    work["wallet"] = work["account"].astype(str).str.lower()
    work["base_pnl_usd"] = pd.to_numeric(work["base_pnl_usd"], errors="coerce").fillna(0)

    def is_win(row: pd.Series) -> bool:
        if row.get("is_liquidation"):
            return False
        return float(row["base_pnl_usd"]) > 0

    work["win"] = work.apply(is_win, axis=1)
    work["realized_gain"] = work["base_pnl_usd"].clip(lower=0)

    agg = (
        work.groupby("wallet", as_index=False)
        .agg(
            close_success_count=("win", "sum"),
            realized_gain_proxy=("realized_gain", "sum"),
            total_closes=("win", "count"),
        )
    )
    agg["close_success_rate"] = agg["close_success_count"] / agg["total_closes"].clip(lower=1)
    agg = agg[agg["total_closes"] >= min_closes]

    ranked = rankings[["wallet", "success_rate", "wins", "total_closes"]].copy()
    ranked["wallet"] = ranked["wallet"].astype(str).str.lower()
    merged = ranked.merge(agg, on="wallet", how="inner", suffixes=("_rank", ""))
    return merged
