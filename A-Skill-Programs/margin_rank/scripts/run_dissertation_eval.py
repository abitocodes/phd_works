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

from evaluate_alignment import METHOD_LABELS, METHODS, PROXY_FAMILIES, build_alignment_report  # noqa: E402

from proxy_metrics import compute_all_proxies  # noqa: E402





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

    parser.add_argument(

        "--skip-aave",

        action="store_true",

        help="Do not require Aave lending parquet (LF-PR scores may be zero)",

    )

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

    aave_path = Path(config["paths"]["aave_events"])



    for p in (rankings_path, decoded_path, allowances_path, transfers_path):

        if not p.exists():

            print(f"Missing required file: {p}")

            return 1



    if not aave_path.exists() and not args.skip_aave:

        print(f"Note: {aave_path} missing — LF-PR will be zero.")

        print("  Run: extract_aave_lending.py --extract --yes && preprocess_aave_lending.py")

        print("  Or pass --skip-aave to suppress this notice.")



    rankings = pd.read_parquet(rankings_path)

    rankings["wallet"] = rankings["wallet"].astype(str).str.lower()

    wallets = rankings["wallet"].tolist()



    decoded = pd.read_parquet(decoded_path)

    allowances = pd.read_parquet(allowances_path)

    transfers = pd.read_parquet(transfers_path)

    aave_events = None
    if aave_path.exists():
        aave_events = pd.read_parquet(aave_path)

    min_closes = int(config["ranking"]["min_closes"])

    proxies = compute_all_proxies(transfers, allowances, decoded, wallets, min_closes=min_closes)



    merged = rankings.merge(proxies, on="wallet", how="inner")



    missing_methods = [

        col for col in METHODS.values() if col not in merged.columns

    ]

    if missing_methods:

        print(f"Missing score columns: {missing_methods}; run compute_reputation_ranks.py")

        return 1



    alignment = build_alignment_report(merged)

    benchmark = benchmark_reputation(
        wallets,
        allowances,
        transfers,
        config,
        repeats=args.benchmark_repeats,
        decoded=decoded,
        aave_events=aave_events,
    )



    note = (

        "Synthetic fixture evaluation; replace with --real after BigQuery extraction."

        if args.fixtures

        else "BigQuery-derived parquet evaluation (goog_blockchain_arbitrum_one_us + GMX EventEmitter)."

    )



    summary = {

        "generated_at": datetime.now(timezone.utc).isoformat(),

        "synthetic": args.fixtures,

        "n_wallets": len(merged),

        "note": note,

        "benchmark": benchmark,

        "alignment": alignment,

        "method_proxy_matrix": alignment["method_proxy_matrix"],

        "family_winners": alignment["family_winners"],

        "dataset": {

            "rankings_path": str(rankings_path),

            "decoded_events_path": str(decoded_path),

            "allowances_path": str(allowances_path),

            "transfers_path": str(transfers_path),

            "aave_events_path": str(aave_path) if aave_path.exists() else None,

        },

    }



    out_path = Path(config["paths"]["eval_summary"])

    save_json(out_path, summary)

    print(f"\nEval summary -> {out_path}")



    er_rt = benchmark["endorserank"]["runtime_sec_mean"]

    awp_rt = benchmark["awp"]["runtime_sec_mean"]

    print(f"  EndorseRank runtime: {er_rt:.3f}s | AWP: {awp_rt:.3f}s")

    print("  Mean Kendall tau by family (EndorseRank | AWP):")

    for family in PROXY_FAMILIES:

        key = f"{family}_mean_tau"

        er_tau = alignment["endorserank_cross_proxy"].get(key)

        awp_tau = alignment["awp_cross_proxy"].get(key)

        winner = alignment["method_comparison"][family].get("higher_alignment", "---")

        er_s = f"{er_tau:.3f}" if er_tau is not None else "---"

        awp_s = f"{awp_tau:.3f}" if awp_tau is not None else "---"

        print(f"    {family:16s} {er_s} | {awp_s}  ({winner})")



    print("\n  7-method mean tau matrix:")

    matrix = alignment["method_proxy_matrix"]

    header = f"    {'Method':14s} " + " ".join(f"{f[:6]:>7s}" for f in PROXY_FAMILIES)

    print(header)

    for method_id in METHODS:

        label = METHOD_LABELS.get(method_id, method_id)

        row = matrix.get(method_id, {})

        vals = " ".join(

            f"{row.get(f, float('nan')):7.3f}" if row.get(f) is not None else "    ---"

            for f in PROXY_FAMILIES

        )

        print(f"    {label:14s} {vals}")



    inter = alignment.get("inter_method", {})

    if inter.get("kendall_tau") is not None:

        print(f"\n  Inter-method tau (EndorseRank vs AWP scores): {inter['kendall_tau']:.3f}")



    if args.export_latex:

        rc = _run_script("export_latex_results.py")

        if rc != 0:

            return rc

        rc = _run_script("export_method_matrix.py")

        if rc != 0:

            return rc



    return 0





if __name__ == "__main__":

    raise SystemExit(main())

