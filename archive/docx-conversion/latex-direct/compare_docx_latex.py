"""Compare docx structure against generated LaTeX."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

from docx_extractor import DocxBlock, extract_docx_blocks

SRC_DOCX = Path(r"D:\Github\phd_works\Proposal\Proposal-Final_Taehong Kwon.docx")
SRC_TEX = Path(r"D:\Github\phd_works\Proposal\latex_direct_conversion\Proposal-Final_Taehong Kwon.direct.tex")
OUT_MD = Path(r"D:\Github\phd_works\Proposal\latex_direct_conversion\diff_report.md")
OUT_JSON = Path(r"D:\Github\phd_works\Proposal\latex_direct_conversion\diff_report.json")


@dataclass
class LatexBlock:
    line: int
    kind: str
    text: str
    label: str
    level: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _strip_latex(text: str) -> str:
    text = re.sub(r"\\textbf\{([^}]*)\}", r"\1", text)
    text = re.sub(r"\\emph\{([^}]*)\}", r"\1", text)
    text = re.sub(r"\\textsubscript\{([^}]*)\}", r"_\1", text)
    text = re.sub(r"\\textsuperscript\{([^}]*)\}", r"^\1", text)
    text = re.sub(r"\\[a-zA-Z]+\*?", "", text)
    text = re.sub(r"[{}$]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _normalize_title(text: str) -> str:
    text = _strip_latex(text).lower()
    text = re.sub(r"^\d+(?:\.\d+)*\.?\s*", "", text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def extract_latex_blocks(tex_path: Path) -> list[LatexBlock]:
    lines = tex_path.read_text(encoding="utf-8").splitlines()
    blocks: list[LatexBlock] = []
    uses_tableofcontents = any("\\tableofcontents" in line for line in lines)

    for i, line in enumerate(lines, start=1):
        stripped = line.strip()
        if stripped == r"\tableofcontents":
            blocks.append(LatexBlock(i, "toc_auto", "Contents", "", "toc"))
            continue
        if stripped.startswith(r"{\Large\bfseries Table of Contents"):
            blocks.append(LatexBlock(i, "toc_title", "Table of Contents", "", "toc"))
            continue
        if r"\TOCentry{" in stripped:
            m = re.search(r"\\TOCentry\{([^}]*)\}\{(.*)\}\{(sec:[^}]+)\}\s*$", stripped)
            if m:
                blocks.append(
                    LatexBlock(i, "toc_entry", _strip_latex(m.group(2)), m.group(1).strip(), "toc")
                )
            continue
        if m := re.match(r"\\(section|subsection|subsubsection)\*?\{(.+)\}", stripped):
            level, raw = m.group(1), m.group(2)
            plain = _strip_latex(raw)
            label_match = re.match(r"^([\d•\-–]+(?:\.[\d]+)*\.?)\s+(.*)$", plain)
            if label_match:
                label, title = label_match.group(1), label_match.group(2)
            else:
                label, title = "", plain
            blocks.append(LatexBlock(i, "section" if level == "section" else "subsection", title, label, level))
            continue
        if stripped.startswith("\\item"):
            item_text = stripped[len("\\item") :].strip()
            if item_text.startswith("["):
                m = re.match(r"\\item\[([^]]+)\]\s*(.*)", stripped)
                if m:
                    blocks.append(LatexBlock(i, "list_item", _strip_latex(m.group(2)), m.group(1).strip(), "item"))
                    continue
            blocks.append(LatexBlock(i, "list_item", _strip_latex(item_text), "", "item"))
            continue
        if stripped.startswith("\\begin{longtable}"):
            blocks.append(LatexBlock(i, "table", "[table]", "", "table"))
            continue
        if stripped.startswith("\\caption{"):
            cap = re.sub(r"^\\caption\{|\}\\\\$", "", stripped)
            blocks.append(LatexBlock(i, "caption", _strip_latex(cap), "", "caption"))

    blocks.append(LatexBlock(0, "meta", "uses_tableofcontents=" + str(uses_tableofcontents), "", "meta"))
    return blocks


def _severity(category: str) -> str:
    critical = {"toc_title", "toc_numbering", "heading_numbering", "heading_level", "structure_drop", "structure_add"}
    major = {"list_numbering", "caption", "inline_markup", "references_format"}
    if category in critical:
        return "Critical"
    if category in major:
        return "Major"
    return "Minor"


def _normalize_list_marker(label: str) -> str:
    label = label.strip()
    if label in {r"\textbullet", "•"}:
        return "bullet"
    if label in {r"\textendash", "--", "–", "-"}:
        return "dash"
    return label


def compare(docx_blocks: list[DocxBlock], latex_blocks: list[LatexBlock]) -> list[dict[str, Any]]:
    diffs: list[dict[str, Any]] = []

    docx_toc_title = next((b for b in docx_blocks if b.kind == "toc_title"), None)
    latex_toc_titles = [b for b in latex_blocks if b.kind in {"toc_title", "toc_auto"}]
    if docx_toc_title:
        if any(b.kind == "toc_auto" for b in latex_toc_titles):
            diffs.append(
                {
                    "category": "toc_title",
                    "severity": _severity("toc_title"),
                    "docx": docx_toc_title.text,
                    "latex": "Contents (via \\tableofcontents)",
                    "detail": "LaTeX auto TOC replaces Word title",
                }
            )
        elif not any(b.text == "Table of Contents" for b in latex_toc_titles):
            diffs.append(
                {
                    "category": "toc_title",
                    "severity": _severity("toc_title"),
                    "docx": docx_toc_title.text,
                    "latex": latex_toc_titles[0].text if latex_toc_titles else "(missing)",
                    "detail": "TOC title mismatch",
                }
            )

    docx_toc = [b for b in docx_blocks if b.kind == "toc_entry"]
    latex_toc = [b for b in latex_blocks if b.kind == "toc_entry"]
    if docx_toc and not latex_toc:
        diffs.append(
            {
                "category": "structure_drop",
                "severity": _severity("structure_drop"),
                "docx": f"{len(docx_toc)} TOC entries",
                "latex": "0 manual TOC entries",
                "detail": "Word TOC entries were skipped",
            }
        )
    if any(b.kind == "toc_auto" for b in latex_blocks):
        diffs.append(
            {
                "category": "structure_add",
                "severity": _severity("structure_add"),
                "docx": "manual TOC block",
                "latex": "\\tableofcontents",
                "detail": "LaTeX-only auto TOC inserted",
            }
        )

    latex_toc_idx = 0
    for entry in docx_toc:
        latex_match = latex_toc[latex_toc_idx] if latex_toc_idx < len(latex_toc) else None
        if latex_match is None:
            diffs.append(
                {
                    "category": "structure_drop",
                    "severity": _severity("structure_drop"),
                    "docx": f"{entry.label} {entry.plain_text}",
                    "latex": "(missing)",
                    "detail": "TOC entry missing in LaTeX",
                }
            )
            continue
        latex_toc_idx += 1
        if entry.label and entry.label != latex_match.label:
            diffs.append(
                {
                    "category": "toc_numbering",
                    "severity": _severity("toc_numbering"),
                    "docx": f"{entry.label} {entry.plain_text}",
                    "latex": f"{latex_match.label} {latex_match.text}".strip(),
                    "detail": "TOC numbering mismatch",
                }
            )

    docx_sections = [b for b in docx_blocks if b.kind in {"section", "subsection"} and b.kind != "toc_entry"]
    latex_sections = [b for b in latex_blocks if b.kind in {"section", "subsection"}]

    for sec in docx_sections:
        if not sec.plain_text or sec.plain_text in {"Abstract", "Table of Contents"}:
            continue
        key = _normalize_title(sec.plain_text)
        latex_match = next((b for b in latex_sections if _normalize_title(b.text) == key), None)
        if latex_match is None:
            continue
        if sec.label and sec.label.replace(".", "") not in {"•", "-", "–"} and sec.label != latex_match.label:
            diffs.append(
                {
                    "category": "heading_numbering",
                    "severity": _severity("heading_numbering"),
                    "docx": f"{sec.label} {sec.plain_text}",
                    "latex": f"{latex_match.label} {latex_match.text}".strip(),
                    "detail": "Body heading numbering mismatch",
                }
            )
        docx_level = "section" if sec.kind == "section" else "subsection"
        if docx_level != latex_match.level and latex_match.level in {"section", "subsection"}:
            diffs.append(
                {
                    "category": "heading_level",
                    "severity": _severity("heading_level"),
                    "docx": f"{docx_level}: {sec.plain_text}",
                    "latex": f"{latex_match.level}: {latex_match.text}",
                    "detail": "Heading level mismatch",
                }
            )

    docx_lists = [b for b in docx_blocks if b.kind == "list_item" and b.label in {"•", "–", "-"} or re.match(r"^\d+\.?$", b.label or "")]
    for item in docx_blocks:
        if item.kind != "list_item" or not item.label:
            continue
        if item.label in {"•", "–", "-"}:
            key = _normalize_title(item.plain_text[:60])
            latex_match = next(
                (
                    b
                    for b in latex_blocks
                    if b.kind == "list_item" and _normalize_title(b.text[:60]) == key
                ),
                None,
            )
            if latex_match and _normalize_list_marker(latex_match.label) != _normalize_list_marker(item.label):
                diffs.append(
                    {
                        "category": "list_numbering",
                        "severity": _severity("list_numbering"),
                        "docx": f"[{item.label}] {item.plain_text[:60]}",
                        "latex": f"[{latex_match.label}] {latex_match.text[:60]}",
                        "detail": "List marker mismatch",
                    }
                )

    if re.search(r"\\textbf\{\\textbf\{", SRC_TEX.read_text(encoding="utf-8")):
        diffs.append(
            {
                "category": "inline_markup",
                "severity": _severity("inline_markup"),
                "docx": "single bold wrapper",
                "latex": "nested \\textbf{\\textbf{...}}",
                "detail": "Duplicate bold markup",
            }
        )

    return diffs


def write_reports(diffs: list[dict[str, Any]], docx_blocks: list[DocxBlock], latex_blocks: list[LatexBlock]) -> None:
    summary: dict[str, int] = {"Critical": 0, "Major": 0, "Minor": 0}
    for diff in diffs:
        summary[diff["severity"]] = summary.get(diff["severity"], 0) + 1

    OUT_JSON.write_text(
        json.dumps(
            {
                "summary": summary,
                "diffs": diffs,
                "docx_block_count": len(docx_blocks),
                "latex_block_count": len(latex_blocks),
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
        newline="\n",
    )

    lines = [
        "# docx vs LaTeX diff report",
        "",
        f"- Source docx: `{SRC_DOCX}`",
        f"- Source tex: `{SRC_TEX}`",
        f"- Critical: {summary.get('Critical', 0)}",
        f"- Major: {summary.get('Major', 0)}",
        f"- Minor: {summary.get('Minor', 0)}",
        "",
        "## Findings",
        "",
    ]
    if not diffs:
        lines.append("No differences detected.")
    else:
        for diff in diffs:
            lines.extend(
                [
                    f"### [{diff['severity']}] {diff['category']}",
                    f"- docx: {diff['docx']}",
                    f"- latex: {diff['latex']}",
                    f"- detail: {diff['detail']}",
                    "",
                ]
            )
    OUT_MD.write_text("\n".join(lines), encoding="utf-8", newline="\n")


def main() -> None:
    docx_blocks = extract_docx_blocks(SRC_DOCX)
    latex_blocks = extract_latex_blocks(SRC_TEX)
    diffs = compare(docx_blocks, latex_blocks)
    write_reports(diffs, docx_blocks, latex_blocks)
    print(f"Wrote {OUT_MD} ({len(diffs)} diffs)")


if __name__ == "__main__":
    main()
