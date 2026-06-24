#!/usr/bin/env python3
"""Export 7×6 method-proxy matrix to CSV and LaTeX."""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import ROOT, load_config, load_json  # noqa: E402
from evaluate_alignment import METHOD_LABELS, METHODS, PROXY_FAMILIES  # noqa: E402

FAMILY_HEADERS = {
    "transfer": "Transfer",
    "allowance": "Allowance",
    "liquidation": "Liq.",
    "inverse_risk": "Inv.risk",
    "sybil_stability": "Sybil",
    "gmx_success": "GMX",
}


def _fmt(v: float | None, digits: int = 3) -> str:
    if v is None:
        return "---"
    return f"{v:.{digits}f}"


def _method_runtime_sec(summary: dict, method_id: str) -> float | None:
    bench = summary.get("benchmark", {})
    entry = bench.get(method_id)
    if not isinstance(entry, dict):
        return None
    val = entry.get("runtime_sec_mean")
    return float(val) if val is not None else None


def write_csv(matrix: dict, out: Path, summary: dict) -> None:
    families = list(PROXY_FAMILIES.keys())
    headers = ["method"] + families + ["runtime_sec"]
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        for method_id in METHODS:
            row = matrix.get(method_id, {})
            rt = _method_runtime_sec(summary, method_id)
            writer.writerow(
                [method_id]
                + [row.get(fam) if row.get(fam) is not None else "" for fam in families]
                + [rt if rt is not None else ""]
            )


def write_latex(summary: dict, out: Path) -> None:
    matrix = summary["alignment"]["method_proxy_matrix"]
    n = summary.get("n_wallets", "---")
    synthetic = summary.get("synthetic", False)
    if synthetic:
        hdr = r"""% Synthetic fixtures — regenerate with:
%   run_dissertation_eval.py --fixtures --export-latex
"""
    else:
        hdr = r"""% Real BigQuery data — regenerate with:
%   run_dissertation_eval.py --real --export-latex
"""

    families = list(PROXY_FAMILIES.keys())
    col_headers = " & ".join(FAMILY_HEADERS[f] for f in families)

    col_max: dict[str, float | None] = {}
    for fam in families:
        vals = [
            matrix.get(m, {}).get(fam)
            for m in METHODS
            if matrix.get(m, {}).get(fam) is not None
        ]
        col_max[fam] = max(vals) if vals else None

    rows = []
    for method_id in METHODS:
        label = METHOD_LABELS.get(method_id, method_id)
        cells = []
        row = matrix.get(method_id, {})
        for fam in families:
            tau = row.get(fam)
            cell = _fmt(tau)
            if tau is not None and col_max.get(fam) is not None and abs(tau - col_max[fam]) < 1e-9:
                cell = f"\\textbf{{{cell}}}"
            cells.append(cell)
        rt = _method_runtime_sec(summary, method_id)
        rt_cell = _fmt(rt, 3) if rt is not None else "---"
        rows.append(f"{label} & {' & '.join(cells)} & {rt_cell} \\\\")

    body = f"""{hdr}
\\begin{{table}}[htbp]
\\centering
\\caption{{Mean Kendall $\\tau$ by proxy family across seven PageRank methods ($n={n}$). Bold = column maximum. Runtime = mean PageRank wall time (s, 5 repeats).}}
\\label{{tab:alignment-seven-methods}}
\\begin{{tabular}}{{l{'c' * len(families)}r}}
\\toprule
Method & {col_headers} & Runtime (s) \\\\
\\midrule
{chr(10).join(rows)}
\\bottomrule
\\end{{tabular}}
\\end{{table}}
"""
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(body, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary", type=Path, help="eval_summary.json path")
    args = parser.parse_args()

    config = load_config()
    summary_path = args.summary or Path(config["paths"]["eval_summary"])
    if not summary_path.exists():
        print(f"Missing {summary_path}; run run_dissertation_eval.py first.")
        return 1

    summary = load_json(summary_path)
    alignment = summary.get("alignment", {})
    matrix = alignment.get("method_proxy_matrix")
    if not matrix:
        print("Missing method_proxy_matrix in eval summary.")
        return 1

    csv_path = ROOT / "data" / "processed" / "method_proxy_matrix.csv"
    write_csv(matrix, csv_path, summary)

    repo_root = ROOT.parents[1]
    tex_path = repo_root / "2-Dissertation-Draft" / "results" / "tables" / "alignment-seven-methods.tex"
    write_latex(summary, tex_path)

    print(f"CSV  -> {csv_path}")
    print(f"LaTeX -> {tex_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
