# phd_works — EndorseRank Dissertation Proposal

PhD dissertation proposal on **EndorseRank**: on-chain reputation ranking via Adaptive Weighted PageRank on Arbitrum One, validated against GMX V2 trading-success proxies.

## Folder layout

| Path | Role |
|------|------|
| `proposal/` | Active LaTeX dissertation proposal (canonical source) |
| `proposal-ko/` | Korean LaTeX translation of the proposal (`main.pdf` via `build.ps1`) |
| `papers/` | Reference PDFs |
| `scripts/` | Utility scripts (DOCX merge, etc.) |
| `sources/professor-feedback/` | Professor-commented DOCX (read-only reference; edit in `proposal/`) |
| `archive/` | Past work — DOCX conversion tools, snapshots, section fixes |
| `presentations/` | Talks and slides |

## Build

```powershell
cd proposal
.\build.ps1
```

Output: `proposal/main.pdf`

Korean LaTeX:

```powershell
cd proposal-ko
.\build.ps1
```

Output: `proposal-ko/main.pdf` (본문 한국어; References는 영문 APA 유지)

Word export (PDF-matching layout):

```powershell
cd proposal
.\build-docx.ps1
```

Output: `proposal/main.docx` (pdf2docx from `main.pdf` — preserves Times New Roman, A4, margins, line breaks, figures)

## Professor comments

- **Word (reference):** `sources/professor-feedback/dissertation-proposal-commented.docx` — open to view comment anchors.
- **LaTeX (edit):** `proposal/` — apply all revisions here, then run `build.ps1`.

## Git remote

```
origin  https://github.com/abitocodes/dissertation_proposal.git
```

The GitHub repository name (`dissertation_proposal`) differs from the local folder name (`phd_works`); this is intentional and does not affect functionality.
