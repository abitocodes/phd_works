# Professor feedback DOCX

## Canonical file

```
1-Dissertation-Works/ERC20-Allowance-PageRank-Wallet-Reputation/proposal/sources/professor-feedback/dissertation-proposal-commented.docx
```

Professor comments (Word review) are preserved in this file. It was originally submitted as `28576810 Proposal_2.docx`.

## Workflow

| Role | Path | Use |
|------|------|-----|
| **Comment reference** | `1-Dissertation-Works/ERC20-Allowance-PageRank-Wallet-Reputation/proposal/sources/professor-feedback/dissertation-proposal-commented.docx` | Open in Word to read professor comment anchors and reply threads. Do not treat this as the editable master. |
| **Active manuscript** | `1-Dissertation-Works/ERC20-Allowance-PageRank-Wallet-Reputation/proposal/proposal/` (LaTeX) | All text edits, professor-feedback fixes, and builds go here. |
| **Build output** | `1-Dissertation-Works/ERC20-Allowance-PageRank-Wallet-Reputation/proposal/proposal/main.pdf` | Generated via `1-Dissertation-Works/ERC20-Allowance-PageRank-Wallet-Reputation/proposal/proposal/build.ps1`. |

When addressing a professor comment:

1. Locate the comment in Word (`dissertation-proposal-commented.docx`).
2. Apply the fix in the matching section under `1-Dissertation-Works/ERC20-Allowance-PageRank-Wallet-Reputation/proposal/proposal/` (e.g. `02-Content/Chapter-01.tex`).
3. Rebuild with `1-Dissertation-Works/ERC20-Allowance-PageRank-Wallet-Reputation/proposal/proposal/build.ps1` and verify in `main.pdf`.

## Merge script (optional)

`1-Dissertation-Works/ERC20-Allowance-PageRank-Wallet-Reputation/proposal/scripts/merge_proposal_docx.py` reads this DOCX when re-running the EndorseRank / GMX V2 research-direction merge from `1-Dissertation-Works/ERC20-Allowance-PageRank-Wallet-Reputation/proposal/archive/snapshots/proposal-0-research-baseline/`. Normal comment remediation does not require running it.

Backup on merge: `dissertation-proposal-commented.pre-merge.docx` (same folder).
