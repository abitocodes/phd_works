"""Insert new bibliography entries alphabetically and renumber all \\cend citations.

Usage:
  python renumber_citations.py

Reads 2-Dissertation-Draft/en/Chapter-07-References/index.tex, inserts NEW_ENTRIES,
sorts APA-style by first-author surname, rewrites ref:N labels, and updates
every \\cend{...} in 01-Intro/, 02-Content/, and 03-End/.
Prints the old?�new mapping for QA.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3] / "2-Dissertation-Draft" / "en"
BIB = ROOT / "Chapter-07-References" / "index.tex"
CONTENT_DIRS = [ROOT / "01-Intro"] + sorted(ROOT.glob("Chapter-*"))

# Verified APA entries (Crossref / standard book citation). No leading label.
NEW_ENTRIES: list[str] = [
    "Akerlof, G. A. (1970). The market for ``lemons'': Quality uncertainty and the market mechanism. "
    r"\textit{The Quarterly Journal of Economics}, \textit{84}(3), 488--500. "
    r"\href{https://doi.org/10.2307/1879431}{doi:10.2307/1879431}",
    "Basu, S. (1977). Investment performance of common stocks in relation to their price-earnings ratios: "
    "A test of the efficient market hypothesis. "
    r"\textit{The Journal of Finance}, \textit{32}(3), 663--682. "
    r"\href{https://doi.org/10.1111/j.1540-6261.1977.tb01979.x}{doi:10.1111/j.1540-6261.1977.tb01979.x}",
    r"Fama, E. F., \& French, K. R. (1992). The cross-section of expected stock returns. "
    r"\textit{The Journal of Finance}, \textit{47}(2), 427--465. "
    r"\href{https://doi.org/10.1111/j.1540-6261.1992.tb04398.x}{doi:10.1111/j.1540-6261.1992.tb04398.x}",
    r"Graham, B., \& Dodd, D. L. (1934). \textit{Security analysis}. McGraw-Hill.",
    r"Healy, P. M., \& Wahlen, J. M. (1999). A review of the earnings management literature and its "
    "implications for standard setting. "
    r"\textit{Accounting Horizons}, \textit{13}(4), 365--383. "
    r"\href{https://doi.org/10.2308/acch.1999.13.4.365}{doi:10.2308/acch.1999.13.4.365}",
]

ITEM_RE = re.compile(
    r"\\item\\phantomsection\\label\{ref:(\d+)\} (.+?)(?=\n  \\item|\n\\end\{enumerate\})",
    re.S,
)
CEND_RE = re.compile(r"\\cend\{([^}]+)\}")


def normalize_sort_key(text: str) -> tuple[str, str, str]:
    """Return (surname_lower, year, title_lower) for APA-ish sort."""
    text = text.strip()
    # Strip LaTeX accents for sorting: Sch\"{a}r ??Schar
    plain = re.sub(r'\\[a-zA-Z]+\{([^{}]*)\}', r"\1", text)
    plain = plain.replace(r"\&", "&")
    # First author surname: text before first comma, or first token before period for orgs.
    if "," in plain.split("(")[0]:
        surname = plain.split(",", 1)[0].strip()
    else:
        surname = plain.split(".", 1)[0].strip()
    m_year = re.search(r"\((\d{4}|n\.d\.)\)", plain)
    year = m_year.group(1) if m_year else "0000"
    # Title fragment after year for tie-break
    title = plain
    if m_year:
        title = plain[m_year.end() :].lstrip(". ").lower()
    return (surname.lower(), year, title[:80])


def parse_bibliography(bib_text: str) -> list[tuple[int | None, str]]:
    """Return list of (old_number_or_None, entry_text)."""
    entries: list[tuple[int | None, str]] = []
    for m in ITEM_RE.finditer(bib_text):
        entries.append((int(m.group(1)), m.group(2).strip()))
    return entries


def rewrite_bibliography(header: str, footer: str, entries: list[str]) -> str:
    lines = [header.rstrip()]
    for i, text in enumerate(entries, start=1):
        lines.append(f"  \\item\\phantomsection\\label{{ref:{i}}} {text}")
    lines.append(footer)
    return "\n".join(lines) + "\n"


def update_cend(text: str, mapping: dict[int, int]) -> str:
    def repl(m: re.Match[str]) -> str:
        nums = [n.strip() for n in m.group(1).split(",")]
        new_nums = []
        for n in nums:
            if not n.isdigit():
                raise ValueError(f"non-numeric cite in \\cend{{{m.group(1)}}}")
            old = int(n)
            if old not in mapping:
                raise KeyError(f"old cite {old} missing from mapping")
            new_nums.append(str(mapping[old]))
        return "\\cend{" + ",".join(new_nums) + "}"

    return CEND_RE.sub(repl, text)


def main() -> None:
    bib_text = BIB.read_text(encoding="utf-8")
    begin_idx = bib_text.index("\\begin{enumerate}")
    end_line = bib_text.index("\n", begin_idx)
    header = bib_text[: end_line + 1]
    footer = "\\end{enumerate}\n"

    old_entries = parse_bibliography(bib_text)
    if not old_entries:
        raise RuntimeError("no bibliography entries parsed")

    # Identity key: full entry text (stable for mapping)
    combined: list[tuple[int | None, str]] = list(old_entries)
    for text in NEW_ENTRIES:
        combined.append((None, text))

    combined.sort(key=lambda pair: normalize_sort_key(pair[1]))

    mapping: dict[int, int] = {}
    new_texts: list[str] = []
    for new_num, (old_num, text) in enumerate(combined, start=1):
        new_texts.append(text)
        if old_num is not None:
            mapping[old_num] = new_num

    BIB.write_text(rewrite_bibliography(header, footer, new_texts), encoding="utf-8")
    print(f"wrote {BIB} ({len(new_texts)} entries)")
    print("old ??new mapping:")
    for old in sorted(mapping):
        print(f"  {old:3d} ??{mapping[old]:3d}")
    print("new entries (no old number):")
    for i, text in enumerate(new_texts, start=1):
        if i not in mapping.values() or all(mapping[o] != i for o in mapping):
            # entries that are new: not in mapping values from old
            pass
    new_only = set(range(1, len(new_texts) + 1)) - set(mapping.values())
    for n in sorted(new_only):
        print(f"  NEW [{n}] {new_texts[n - 1][:90]}...")

    # Update all content files
    updated_files = 0
    for d in CONTENT_DIRS:
        for path in sorted(d.rglob("*.tex")):
            if path.name == "bibliography.tex":
                continue
            original = path.read_text(encoding="utf-8")
            if "\\cend{" not in original:
                continue
            updated = update_cend(original, mapping)
            if updated != original:
                path.write_text(updated, encoding="utf-8")
                updated_files += 1
                print(f"updated cites in {path.relative_to(ROOT)}")
    print(f"updated {updated_files} content files")

    # Write mapping for QA
    map_path = Path(__file__).resolve().parent / "_cite_mapping.txt"
    lines = [f"{o}\t{mapping[o]}" for o in sorted(mapping)]
    for n in sorted(new_only):
        lines.append(f"NEW\t{n}\t{new_texts[n - 1][:120]}")
    map_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"mapping saved to {map_path}")


if __name__ == "__main__":
    main()
