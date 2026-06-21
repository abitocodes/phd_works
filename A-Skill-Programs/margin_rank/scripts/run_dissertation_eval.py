#!/usr/bin/env python3
"""
Master dissertation evaluation pipeline.

Offline (--fixtures): synthetic GMX + reputation data, no BigQuery.
Real (--real): assumes extract/preprocess scripts already ran.

Output: data/processed/eval_summary.json
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from benchmark_runtime import benchmark_reputation  # noqa: E402
from common import load_config, save_json  # noqa: E402
from evaluate_alignment import build_alignment_report  # noqa: E402
from proxy_metrics import compute_gmx_proxies, compute_transfer_proxies  # noqa: E402


def _run_script(name: str, extra: list[str] | None = None) -> int:
    scripts_dir = Path(__file__).resolve().parent
    cmd = [sys.executable, str(scripts_dir / name)] + (extra or [])
    print(f"\n>> {' '.join(cmd)}")
    return subprocess.call(cmd)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixtures", action="store_true", help="Generate synthetic data (no GCP)")
    parser.add_argument("--real", action="store_true", help="Use existing BigQuery-derived parquet")
    parser.add_argument("--n-wallets", type=int, default=571)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--benchmark-repeats", type=int, default=5)
    parser.add_argument("--export-latex", action="store_true", help="Run export_latex_results.py after eval")
    args = parser.parse_args()

    if not args.fixtures and not args.real:
        parser.error("Specify --fixtures (offline) or --real (post-BigQuery)")

    config = load_config()

    if args.fixtures:
        rc = _run_script("generate_synthetic_rankings.py", ["--n-wallets", str(args.n_wallets), "--seed", str(args.seed)])
        if rc != 0:
            return rc
        rc = _run_script("generate_synthetic_reputation.py", ["--seed", str(args.seed)])
        if rc != 0:
            return rc
    else:
        rc = _run_script("compute_rankings.py")
        if rc != 0:
            return rc
        rc = _run_script("compute_reputation_ranks.py")
        if rc != 0:
            return rc

    rankings_path = Path(config["paths"]["wallet_rankings"])
    decoded_path = Path(config["paths"]["decoded_events"])
    rep = config["reputation"]
    allowances_path = Path(rep["paths"]["latest_allowances"])
    transfers_path = Path(rep["paths"]["transfer_events"])

    for p in (rankings_path, decoded_path, allowances_path, transfers_path):
        if not p.exists():
            print(f"Missing required file: {p}")
            return 1

    rankings = pd.read_parquet(rankings_path)
    rankings["wallet"] = rankings["wallet"].astype(str).str.lower()
    wallets = rankings["wallet"].tolist()

    decoded = pd.read_parquet(decoded_path)
    allowances = pd.read_parquet(allowances_path)
    transfers = pd.read_parquet(transfers_path)

    transfer_px = compute_transfer_proxies(transfers, wallets)
    gmx_px = compute_gmx_proxies(decoded, rankings, min_closes=int(config["ranking"]["min_closes"]))

    merged = rankings.merge(transfer_px, on="wallet", how="inner")
    merged = merged.merge(
        gmx_px[
            [
                "wallet",
                "close_success_count",
                "realized_gain_proxy",
                "close_success_rate",
            ]
        ],
        on="wallet",
        how="inner",
    )

    if "endorserank_score" not in merged.columns or "awp_score" not in merged.columns:
        print("Missing endorserank_score or awp_score; run compute_reputation_ranks.py")
        return 1

    alignment = build_alignment_report(merged)
    benchmark = benchmark_reputation(wallets, allowances, transfers, config, repeats=args.benchmark_repeats)

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "synthetic": args.fixtures,
        "n_wallets": len(merged),
        "note": "DUMMY/SYNTHETIC until BigQuery pipeline replaces parquet inputs.",
        "benchmark": benchmark,
        "alignment": alignment,
        "dataset": {
            "rankings_path": str(rankings_path),
            "decoded_events_path": str(decoded_path),
            "allowances_path": str(allowances_path),
            "transfers_path": str(transfers_path),
        },
    }

    out_path = Path(config["paths"]["eval_summary"])
    save_json(out_path, summary)
    print(f"\nEval summary -> {out_path}")

    er_tau_gmx = alignment["endorserank_cross_proxy"]["gmx_family_mean_tau"]
    awp_tau_gmx = alignment["awp_cross_proxy"]["gmx_family_mean_tau"]
    er_rt = benchmark["endorserank"]["runtime_sec_mean"]
    awp_rt = benchmark["awp"]["runtime_sec_mean"]
    if er_tau_gmx is not None and awp_tau_gmx is not None:
        print(f"  EndorseRank GMX mean tau: {er_tau_gmx:.3f} | AWP: {awp_tau_gmx:.3f}")
    print(f"  EndorseRank runtime: {er_rt:.3f}s | AWP: {awp_rt:.3f}s")

    if args.export_latex:
        rc = _run_script("export_latex_results.py")
        if rc != 0:
            return rc

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
