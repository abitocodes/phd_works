# Extended baselines (archived)

These tables were removed from the main dissertation draft when the narrative
focused on **three methods**: EndorseRank, AWP, and GF-PR.

## Contents

| File | Description |
|------|-------------|
| `tables/alignment-seven-methods.tex` | 7-method proxy-family matrix (LP-PR, CW-AWP, LF-PR, RiskProp, …) |
| `tables/alignment-six-aave-methods.tex` | 6-method Aave W↔W PageRank baselines |

CSV exports live under
`A-Skill-Programs/margin_rank/data/archive/extended-baselines/`.

## Regenerate (after `run_dissertation_eval.py --real`)

```powershell
cd A-Skill-Programs/margin_rank
python scripts/export_method_matrix.py --preset seven `
  --out-dir ../../2-Dissertation-Draft/archive/extended-baselines/tables `
  --csv-out-dir data/archive/extended-baselines
python scripts/export_method_matrix.py --preset six-aave `
  --out-dir ../../2-Dissertation-Draft/archive/extended-baselines/tables `
  --csv-out-dir data/archive/extended-baselines
```

Or run `python scripts/run_dissertation_eval.py --real --export-latex` — archive
presets are exported automatically alongside the dissertation tables.
