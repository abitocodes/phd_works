# phd_works — EndorseRank Dissertation Proposal

PhD dissertation proposal on **EndorseRank**: on-chain reputation ranking via Adaptive Weighted PageRank on Arbitrum One, validated against GMX V2 trading-success proxies.

## Folder layout

| Path | Role |
|------|------|
| `proposal/` | Active LaTeX dissertation proposal (canonical source) |
| `papers/` | Reference PDFs |
| `scripts/` | Utility scripts (DOCX merge, etc.) |
| `sources/professor-feedback/` | Professor-reviewed DOCX input |
| `archive/` | Past work — DOCX conversion tools, snapshots, section fixes |
| `presentations/` | Talks and slides |

## Build

```powershell
cd proposal
.\build.ps1
```

Output: `proposal/main.pdf`

## Git remote

```
origin  https://github.com/abitocodes/dissertation_proposal.git
```

The GitHub repository name (`dissertation_proposal`) differs from the local folder name (`phd_works`); this is intentional and does not affect functionality.
