# phd_works — EndorseRank PhD Research

PhD research on **EndorseRank**: on-chain reputation ranking via Adaptive Weighted PageRank on Arbitrum One, validated against GMX V2 trading-success proxies.

This repository holds the completed dissertation proposal, the active dissertation draft, empirical tooling, and shared reference papers.

## Folder layout

| Path | Role |
|------|------|
| `1-Proposal/` | Completed dissertation proposal (LaTeX canonical: `1-Proposal/proposal/`) |
| `2-Dissertation-Draft/` | **Active** dissertation draft LaTeX (6-chapter thesis structure) |
| `A-Skill-Programs/` | Empirical code and agent tooling (`margin_rank/`, etc.) |
| `papers/` | Shared reference PDFs |

### Inside `1-Proposal/`

| Path | Role |
|------|------|
| `1-Proposal/proposal/` | Approved proposal LaTeX source |
| `1-Proposal/sources/professor-feedback/` | Professor-commented DOCX (read-only reference) |
| `1-Proposal/archive/` | DOCX conversion tools, snapshots, section fixes |
| `1-Proposal/presentations/` | Talks and slides |
| `1-Proposal/scripts/` | Utility scripts (DOCX merge, etc.) |

## Build

**Proposal (completed):**

```powershell
cd 1-Proposal/proposal
.\build.ps1
```

Output: `1-Proposal/proposal/main.pdf`

**Dissertation draft (active):**

```powershell
cd 2-Dissertation-Draft
.\build.ps1
```

Output: `2-Dissertation-Draft/main.pdf`

Requires XeLaTeX (Times New Roman via `fontspec`).

## AI agent guide — dissertation draft work

When editing **`2-Dissertation-Draft/`**, treat the approved proposal as the authoritative baseline. Do not rewrite from memory; align terminology, research questions, and methodology with these paths:

| Reference | Path |
|-----------|------|
| **Canonical proposal LaTeX** | `1-Proposal/proposal/` (`main.tex`, `02-Content/Chapter-*.tex`) |
| **Built proposal PDF** | `1-Proposal/proposal/main.pdf` |
| **Professor comments (read-only)** | `1-Proposal/sources/professor-feedback/dissertation-proposal-commented.docx` |
| **Research baseline snapshot** | `1-Proposal/archive/snapshots/proposal-0-research-baseline/` |
| **Dissertation outline (6 chapters)** | `1-Proposal/proposal/02-Content/Chapter-10.tex` |
| **Empirical tooling** | `A-Skill-Programs/margin_rank/` |
| **Shared reference PDFs** | `papers/` |

### Proposal → dissertation chapter mapping

| Dissertation chapter | Primary proposal sources |
|----------------------|--------------------------|
| Ch 1 Introduction | `Chapter-01`, `Chapter-02`, `Chapter-03` |
| Ch 2 Literature review | `Chapter-02`, `Chapter-04` |
| Ch 3 Methodology | `Chapter-05`–`Chapter-07` |
| Ch 4 Implementation & results | `Chapter-08`, `A-Skill-Programs/margin_rank/` |
| Ch 5 Discussion | `Chapter-08`, `Chapter-09` |
| Ch 6 Conclusion | `Chapter-09`, `Chapter-10` outline |

## Professor comments (proposal)

- **Word (reference):** `1-Proposal/sources/professor-feedback/dissertation-proposal-commented.docx`
- **LaTeX (edit):** `1-Proposal/proposal/` — proposal revisions only; dissertation work goes in `2-Dissertation-Draft/`

## Git remote

```
origin  https://github.com/abitocodes/phd_works.git
```
