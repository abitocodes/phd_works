"""Generate dissertation figures from processed parquet and eval_summary.json."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
OUT = ROOT.parents[1] / "2-Dissertation-Draft" / "Figures" / "generated"


def _setup_style() -> None:
    plt.rcParams.update(
        {
            "font.family": "serif",
            "font.size": 10,
            "axes.labelsize": 11,
            "axes.titlesize": 11,
            "figure.dpi": 150,
            "savefig.dpi": 200,
            "savefig.bbox": "tight",
            "axes.grid": True,
            "grid.alpha": 0.3,
        }
    )


def _save(fig: plt.Figure, name: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / name
    fig.savefig(path)
    plt.close(fig)
    print(f"wrote {path}")


def fig_gmx_closes_hist(rankings: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(5.5, 3.6))
    closes = rankings["total_closes"].clip(upper=np.percentile(rankings["total_closes"], 99))
    ax.hist(closes, bins=40, color="#2c5f8a", edgecolor="white", linewidth=0.4)
    ax.set_xlabel("GMX closes per wallet (winsorized at 99th percentile)")
    ax.set_ylabel("Number of wallets")
    _save(fig, "gmx-closes-hist.pdf")


def fig_pnl_hist(gmx: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(5.5, 3.6))
    pnl = gmx["base_pnl_usd"].astype(float)
    pnl = pnl[(pnl > pnl.quantile(0.01)) & (pnl < pnl.quantile(0.99))]
    ax.hist(pnl, bins=50, color="#3d7a5a", edgecolor="white", linewidth=0.3)
    ax.axvline(0, color="black", linewidth=0.8, linestyle="--")
    ax.set_xlabel("Realized base PnL (USD, 1st--99th percentile)")
    ax.set_ylabel("Number of PositionDecrease events")
    _save(fig, "gmx-pnl-hist.pdf")


def fig_score_distributions(rankings: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.4))
    for ax, col, panel in (
        (axes[0], "endorserank_score", "EndorseRank"),
        (axes[1], "awp_score", "AWP"),
    ):
        s = rankings[col].astype(float)
        s = s[s > 0]
        ax.hist(np.log10(s), bins=40, color="#5a4a7a", edgecolor="white", linewidth=0.3)
        ax.set_xlabel(r"$\log_{10}$(score)")
        ax.set_ylabel("Wallets")
        ax.text(0.02, 0.95, panel, transform=ax.transAxes, va="top", fontsize=10)
    fig.tight_layout()
    _save(fig, "score-distributions.pdf")


def fig_rank_scatter(rankings: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(5.2, 5.0))
    x = rankings["endorserank_rank"].astype(float)
    y = rankings["awp_rank"].astype(float)
    rng = np.random.default_rng(42)
    idx = rng.choice(len(x), size=min(2000, len(x)), replace=False)
    ax.scatter(x.iloc[idx], y.iloc[idx], s=6, alpha=0.35, color="#2c5f8a", edgecolors="none")
    lim = max(x.max(), y.max())
    ax.plot([1, lim], [1, lim], "k--", linewidth=0.8, label="identity")
    tau, _ = stats.kendalltau(rankings["endorserank_score"], rankings["awp_score"])
    ax.set_xlabel("EndorseRank rank (1 = highest score)")
    ax.set_ylabel("AWP rank (1 = highest score)")
    ax.legend(loc="upper left", frameon=False, title=rf"Kendall $\tau$ = {tau:.3f}")
    ax.set_aspect("equal", adjustable="box")
    _save(fig, "rank-scatter.pdf")


def fig_alignment_heatmap(summary: dict) -> None:
    matrix = summary["alignment"]["method_proxy_matrix"]
    # Keys must match eval_summary.json method_proxy_matrix (gmx_success, not trading_success).
    families = [
        "transfer",
        "allowance",
        "inverse_risk",
        "sybil_stability",
        "gmx_success",
    ]
    labels = ["Transfer", "Allowance", "Inverse risk", "Sybil stability", "Trading success"]
    methods = ["endorserank", "awp", "gf_pr"]
    method_labels = ["EndorseRank", "AWP", "GF-PR"]
    data = np.array([[matrix[m].get(f, np.nan) for f in families] for m in methods], dtype=float)
    if np.isnan(data).any():
        raise ValueError(f"heatmap contains NaN; check family keys. data=\n{data}")

    fig, ax = plt.subplots(figsize=(7.0, 3.2))
    im = ax.imshow(data, cmap="RdYlBu_r", vmin=-0.1, vmax=0.6, aspect="auto")
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=25, ha="right")
    ax.set_yticks(range(len(method_labels)))
    ax.set_yticklabels(method_labels)
    for i in range(data.shape[0]):
        for j in range(data.shape[1]):
            ax.text(j, i, f"{data[i, j]:.3f}", ha="center", va="center", fontsize=9)
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04, label=r"Mean Kendall $\tau$")
    _save(fig, "alignment-heatmap.pdf")


def fig_runtime_scaling(summary: dict) -> None:
    tier2 = summary.get("benchmark_tier2") or {}
    rows = tier2.get("rows") or []
    incohort = summary.get("benchmark_scaling") or {}
    incohort_rows = incohort.get("rows") or []

    fig, ax = plt.subplots(figsize=(5.8, 3.8))
    all_n: list[int] = []
    if incohort_rows:
        n = [r["n_wallets"] for r in incohort_rows]
        er = [r["endorserank"]["runtime_sec_mean"] for r in incohort_rows]
        awp = [r["awp"]["runtime_sec_mean"] for r in incohort_rows]
        ax.plot(n, er, "o-", color="#2c5f8a", label="EndorseRank (in-cohort)")
        ax.plot(n, awp, "s-", color="#a03c3c", label="AWP (in-cohort)")
        all_n.extend(n)
    if rows:
        n2 = [r["n_wallets"] for r in rows]
        er2 = [r["endorserank"]["runtime_sec_mean"] for r in rows]
        awp2 = [r["awp"]["runtime_sec_mean"] for r in rows]
        ax.plot(n2, er2, "o--", color="#5a8ab8", label="EndorseRank (expanded pool)")
        ax.plot(n2, awp2, "s--", color="#c06060", label="AWP (expanded pool)")
        all_n.extend(n2)
    ax.set_xscale("log")
    if all_n:
        ticks = sorted(set(all_n))
        ax.set_xticks(ticks)
        ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{int(v):,}"))
        ax.set_xlim(min(all_n) * 0.9, max(all_n) * 1.1)
    ax.set_xlabel("Number of wallets $n$ (log scale)")
    ax.set_ylabel("PageRank wall time (s)")
    ax.legend(frameon=False, fontsize=8)
    _save(fig, "runtime-scaling.pdf")


def fig_damping_sensitivity(summary: dict) -> None:
    rob = summary.get("robustness") or {}
    sweep = rob.get("damping_sweep") or {}
    rows = sweep.get("rows") or []
    if not rows:
        return
    d = [r["damping"] for r in rows]
    fig, ax = plt.subplots(figsize=(5.5, 3.6))
    ax.plot(d, [r["er_allowance_tau"] for r in rows], "o-", color="#2c5f8a", label="ER allowance")
    ax.plot(d, [r["awp_allowance_tau"] for r in rows], "s-", color="#a03c3c", label="AWP allowance")
    ax.plot(d, [r["er_transfer_tau"] for r in rows], "o--", color="#5a8ab8", label="ER transfer")
    ax.plot(d, [r["awp_transfer_tau"] for r in rows], "s--", color="#c06060", label="AWP transfer")
    ax.set_xlabel("PageRank damping $d$")
    ax.set_ylabel(r"Mean Kendall $\tau$")
    ax.legend(frameon=False, fontsize=8)
    ax.set_xticks(d)
    _save(fig, "damping-sensitivity.pdf")


def fig_logistic_decay() -> None:
    """Illustrative logistic time-decay used by AWP (k=0.01, t0=180)."""
    k, t0 = 0.01, 180.0
    dt = np.linspace(0, 400, 400)
    sigma = 1.0 / (1.0 + np.exp(k * (dt - t0)))
    fig, ax = plt.subplots(figsize=(5.5, 3.4))
    ax.plot(dt, sigma, color="#2c5f8a", linewidth=2)
    ax.axvline(t0, color="gray", linestyle="--", linewidth=0.8)
    ax.text(t0 + 5, 0.55, r"$t_0=180$ days", fontsize=9)
    ax.set_xlabel(r"Age $\Delta t$ (days)")
    ax.set_ylabel(r"Decay weight $\sigma(\Delta t)$")
    ax.set_ylim(-0.02, 1.05)
    _save(fig, "logistic-decay.pdf")


def fig_success_rate_hist(rankings: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(5.5, 3.6))
    ax.hist(rankings["success_rate"].astype(float), bins=30, color="#7a5a2c", edgecolor="white")
    ax.set_xlabel("Close success rate")
    ax.set_ylabel("Number of wallets")
    _save(fig, "success-rate-hist.pdf")


def main() -> None:
    _setup_style()
    rankings = pd.read_parquet(PROCESSED / "wallet_rankings.parquet")
    gmx = pd.read_parquet(PROCESSED / "gmx_decoded_events.parquet")
    summary = json.loads((PROCESSED / "eval_summary.json").read_text(encoding="utf-8"))

    fig_gmx_closes_hist(rankings)
    fig_pnl_hist(gmx)
    fig_score_distributions(rankings)
    fig_rank_scatter(rankings)
    fig_alignment_heatmap(summary)
    fig_runtime_scaling(summary)
    fig_damping_sensitivity(summary)
    fig_logistic_decay()
    fig_success_rate_hist(rankings)
    print("done")


if __name__ == "__main__":
    main()
