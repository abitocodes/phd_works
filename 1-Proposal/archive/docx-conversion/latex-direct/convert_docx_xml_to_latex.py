from __future__ import annotations

import re
import shutil
import zipfile
from dataclasses import dataclass
from pathlib import Path

from lxml import etree

from numbering_engine import NumberingEngine

SRC = Path(r"D:\Github\phd_works\Proposal\Proposal-Final_Taehong Kwon.docx")
OUT_DIR = Path(r"D:\Github\phd_works\Proposal\latex_direct_conversion")
OUT_TEX = OUT_DIR / "Proposal-Final_Taehong Kwon.direct.tex"
REPORT = OUT_DIR / "conversion_report.txt"
FIDELITY_DIR = Path(r"D:\Github\phd_works\Proposal\latex_fidelity")
FIDELITY_MAIN = FIDELITY_DIR / "main.tex"
FIDELITY_REPORT = FIDELITY_DIR / "validation_report.txt"

NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "m": "http://schemas.openxmlformats.org/officeDocument/2006/math",
}
W = f"{{{NS['w']}}}"
R = f"{{{NS['r']}}}"
M = f"{{{NS['m']}}}"

LATEX_SPECIAL = {
    "\\": r"\textbackslash{}",
    "{": r"\{",
    "}": r"\}",
    "$": r"\$",
    "&": r"\&",
    "#": r"\#",
    "_": r"\_",
    "%": r"\%",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
}

LATEX_TO = "\\to"


TEXT_REPLACE = {
    "\u2019": "'",
    "\u2018": "'",
    "\u201c": "``",
    "\u201d": "''",
    "\u2014": "---",
    "\u2013": "--",
    "\u2212": "-",
    "\u2192": "\\(" + LATEX_TO + "\\)",
    "\u2190": "\\(" + "\\leftarrow" + "\\)",
    "\u2208": r"\(\in\)",
    "\u03c1": r"\(\rho\)",
    "\u03c4": r"\(\tau\)",
    "\u2217": r"\(\ast\)",
}

MATH_REPLACE = {
    "→": LATEX_TO + " ",
    "←": r"\leftarrow ",
    "↔": r"\leftrightarrow ",
    "∈": r"\in ",
    "∑": r"\sum ",
    "ρ": r"\rho ",
    "τ": r"\tau ",
    "α": r"\alpha ",
    "β": r"\beta ",
    "γ": r"\gamma ",
    "δ": r"\delta ",
    "≤": r"\le ",
    "≥": r"\ge ",
    "≠": r"\ne ",
    "×": r"\times ",
    "−": "-",
}


@dataclass
class TocEntry:
    label: str
    title: str
    title_latex: str
    label_key: str
    ilvl: int


def local_name(el: etree._Element) -> str:
    return etree.QName(el).localname if isinstance(el.tag, str) else ""


def attr(el: etree._Element, ns: str, name: str) -> str | None:
    return el.get(f"{{{NS[ns]}}}{name}")


def slugify(text: str) -> str:
    text = re.sub(r"[^\w\s-]", "", text.lower())
    return re.sub(r"[-\s]+", "-", text).strip("-") or "section"


def latex_escape(text: str) -> str:
    text = text.replace("\u00a0", " ")
    out = []
    for ch in text:
        if ch in TEXT_REPLACE:
            out.append(TEXT_REPLACE[ch])
        else:
            out.append(LATEX_SPECIAL.get(ch, ch))
    return "".join(out)


def math_escape(text: str) -> str:
    out = []
    for ch in text:
        if ch in MATH_REPLACE:
            out.append(MATH_REPLACE[ch])
        elif ch == "_":
            out.append(r"\_")
        elif ch in "{}$&#%":
            out.append("\\" + ch)
        else:
            out.append(ch)
    return "".join(out)


def compact_spaces(text: str) -> str:
    return re.sub(r"[ \t]+", " ", text).strip()


def child_text(el: etree._Element) -> str:
    return "".join(el.xpath(".//w:t/text() | .//m:t/text()", namespaces=NS)).strip()


def get_para_style(p: etree._Element) -> str:
    vals = p.xpath("./w:pPr/w:pStyle/@w:val", namespaces=NS)
    return vals[0] if vals else ""


def get_num(p: etree._Element) -> tuple[str, int] | None:
    num_id = p.xpath("./w:pPr/w:numPr/w:numId/@w:val", namespaces=NS)
    if not num_id:
        return None
    ilvl = p.xpath("./w:pPr/w:numPr/w:ilvl/@w:val", namespaces=NS)
    return num_id[0], int(ilvl[0]) if ilvl else 0


def get_alignment(p: etree._Element) -> str:
    vals = p.xpath("./w:pPr/w:jc/@w:val", namespaces=NS)
    return vals[0] if vals else ""


def paragraph_max_size(p: etree._Element) -> int:
    sizes = []
    for value in p.xpath(".//w:rPr/w:sz/@w:val", namespaces=NS):
        try:
            sizes.append(int(value))
        except ValueError:
            pass
    return max(sizes) if sizes else 0


def paragraph_has_bold(p: etree._Element) -> bool:
    return bool(p.xpath(".//w:rPr/w:b[not(@w:val='0') and not(@w:val='false')]", namespaces=NS))


def parse_relationships(zf: zipfile.ZipFile) -> dict[str, str]:
    rels_path = "word/_rels/document.xml.rels"
    if rels_path not in zf.namelist():
        return {}
    root = etree.fromstring(zf.read(rels_path))
    return {rel.get("Id"): rel.get("Target") for rel in root if rel.get("Id") and rel.get("Target")}


def render_math(el: etree._Element) -> str:
    name = local_name(el)
    if name == "t":
        return math_escape(el.text or "")
    if name == "r":
        return "".join(render_math(c) for c in el if isinstance(c.tag, str))
    if name in {"oMath", "oMathPara", "e", "num", "den", "sub", "sup"}:
        return "".join(render_math(c) for c in el if isinstance(c.tag, str))
    if name == "sSub":
        base = render_math(el.find(f"{M}e")) if el.find(f"{M}e") is not None else ""
        sub = render_math(el.find(f"{M}sub")) if el.find(f"{M}sub") is not None else ""
        return f"{base}_{{{sub}}}"
    if name == "sSup":
        base = render_math(el.find(f"{M}e")) if el.find(f"{M}e") is not None else ""
        sup = render_math(el.find(f"{M}sup")) if el.find(f"{M}sup") is not None else ""
        return f"{base}^{{{sup}}}"
    if name == "f":
        numerator = render_math(el.find(f"{M}num")) if el.find(f"{M}num") is not None else ""
        denominator = render_math(el.find(f"{M}den")) if el.find(f"{M}den") is not None else ""
        return rf"\frac{{{numerator}}}{{{denominator}}}"
    if name == "nary":
        nary_pr = el.find(f"{M}naryPr")
        symbol = r"\sum "
        if nary_pr is not None:
            chr_el = nary_pr.find(f"{M}chr")
            if chr_el is not None and attr(chr_el, "m", "val"):
                symbol = math_escape(attr(chr_el, "m", "val") or "")
        sub = render_math(el.find(f"{M}sub")) if el.find(f"{M}sub") is not None else ""
        sup = render_math(el.find(f"{M}sup")) if el.find(f"{M}sup") is not None else ""
        expr = render_math(el.find(f"{M}e")) if el.find(f"{M}e") is not None else ""
        if sub and sup:
            return f"{symbol}_{{{sub}}}^{{{sup}}}{expr}"
        if sub:
            return f"{symbol}_{{{sub}}}{expr}"
        return f"{symbol}{expr}"
    return "".join(render_math(c) for c in el if isinstance(c.tag, str))


def render_run(r: etree._Element) -> str:
    pieces = []
    for child in r:
        name = local_name(child)
        if name == "t":
            pieces.append(latex_escape(child.text or ""))
        elif name == "tab":
            pieces.append(" ")
        elif name == "br":
            pieces.append(r"\\")
        elif name in {"drawing", "pict"}:
            pieces.append(
                "\n"
                r"\begin{center}"
                "\n"
                r"\input{Figures/conceptual-model.tex}"
                "\n"
                r"\end{center}"
                "\n"
            )
        elif name == "footnoteReference":
            fid = attr(child, "w", "id") or ""
            pieces.append(rf"\footnote{{Footnote {latex_escape(fid)}}}")

    text = "".join(pieces)
    if not text:
        return ""

    rpr = r.find(f"{W}rPr")
    if rpr is None:
        return text

    def has(tag: str) -> bool:
        node = rpr.find(f"{W}{tag}")
        return node is not None and node.get(f"{W}val") not in {"0", "false", "none"}

    vert = rpr.find(f"{W}vertAlign")
    vert_val = attr(vert, "w", "val") if vert is not None else ""

    if vert_val == "superscript":
        text = rf"\textsuperscript{{{text}}}"
    elif vert_val == "subscript":
        text = rf"_{{\text{{{text}}}}}"
    elif has("i") and not has("b"):
        text = rf"\emph{{{text}}}"
    elif has("b") and not has("i"):
        text = rf"\textbf{{{text}}}"
    elif has("b") and has("i"):
        text = r"\textbf{\emph{" + text + "}}"
    if has("u") and vert_val not in {"superscript", "subscript"}:
        text = rf"\uline{{{text}}}"
    return text


def fix_inline_markup(text: str) -> str:
    def math_subscript(match: re.Match[str]) -> str:
        base = match.group(1)
        sub = match.group(2).replace("\\(" + LATEX_TO + "\\)", LATEX_TO)
        sub = sub.replace("\\tov", LATEX_TO + " v")
        if any(token in sub for token in (LATEX_TO, "\\(", "\\)")):
            return f"${base}_{{{sub}}}$"
        return f"${base}_{{\\text{{{sub}}}}}$"

    text = re.sub(r"_\{\\text\{\s*\}\}", "", text)
    text = re.sub(r"\\emph\{_\{\\text\{([^}]+)\}\}\}", r"_\\text{\1}", text)
    text = re.sub(r"\\emph\{\s*\}", "", text)
    emph_sub = (
        r"\\emph\{([A-Za-z])"
        + r"\}"
        + r"_\{"
        + r"\\text\{([^}]+)\}"
        + r"\}"
    )
    text = re.sub(emph_sub, math_subscript, text)
    text = re.sub(
        r"(?<!\$)(?<![A-Za-z])([A-Za-z])_\{\\text\{([^}]+)\}\}",
        math_subscript,
        text,
    )
    text = re.sub(
        r"\\textbf\{\\emph\{([^}]*)\}\\textbf\{([^}]*)\}",
        r"\\textbf{\\emph{\1}\2}",
        text,
    )
    text = re.sub(r"\\emph\{\\emph\{", r"\\emph{", text)
    text = re.sub(r"\\textbf\{\\textbf\{", r"\\textbf{", text)
    text = text.replace("\\tov", LATEX_TO + " v")
    text = re.sub(r"(\\end\{center\})\s*\\\\+", r"\1", text)
    return text


def render_inline(parent: etree._Element, rels: dict[str, str]) -> str:
    pieces = []
    for child in parent:
        name = local_name(child)
        if name == "r":
            pieces.append(render_run(child))
        elif name == "hyperlink":
            body = render_inline(child, rels)
            rid = attr(child, "r", "id")
            url = rels.get(rid or "", "")
            pieces.append(rf"\href{{{latex_escape(url)}}}{{{body}}}" if url else body)
        elif name == "oMath":
            pieces.append("$" + render_math(child) + "$")
        elif name == "oMathPara":
            pieces.append(r"\[" + render_math(child) + r"\]")
        elif name in {"smartTag", "sdt", "ins"}:
            pieces.append(render_inline(child, rels))
    return fix_inline_markup(compact_spaces("".join(pieces)))


def is_caption(text: str, style: str) -> bool:
    return style == "ad" or bool(re.match(r"^Table\s+\d+\s*:", text))


def is_outline_level0(p: etree._Element, text: str) -> bool:
    if not text or get_num(p) is not None:
        return False
    return paragraph_has_bold(p) and paragraph_max_size(p) >= 40 and len(text) <= 80


def is_outline_level1(p: etree._Element, text: str, style: str) -> bool:
    if not text or get_num(p) is not None or style != "1":
        return False
    return text not in {"Abstract", "Table of Contents"}


def is_numbered_heading(p: etree._Element, style: str) -> bool:
    num = get_num(p)
    if not num:
        return False
    num_id, ilvl = num
    if num_id == "45":
        return False
    if style in {"1", "2"} and num_id in {"32", "22"}:
        return True
    return style == "2" and num_id in {"31", "19", "18", "17", "20", "21"} and ilvl == 0


def heading_command(label: str, ilvl: int, style: str, num_id: str = "") -> str:
    if style == "2" and num_id in {"31", "19", "18", "17", "20", "21"} and ilvl == 0:
        return "subsection"
    if style == "1" and num_id == "32" and ilvl == 1:
        return "subsection"
    if label in {"•", "–", "-"} or (style == "2" and ilvl >= 2):
        return "subsubsection"
    if style == "1" and ilvl <= 0:
        return "section"
    if ilvl <= 0:
        return "section"
    return "subsection"


def prefix_title(label: str, latex_text: str) -> str:
    if not label:
        return latex_text
    if label in {"•", "–", "-"}:
        return f"{label} {latex_text}"
    sep = " " if not label.endswith(".") else " "
    return f"{latex_escape(label)}{sep}{latex_text}"


def close_lists(lines: list[str], stack: list[str], target_level: int = -1) -> None:
    while len(stack) - 1 > target_level:
        env = stack.pop()
        lines.append(rf"\end{{{env}}}")


def open_list(lines: list[str], stack: list[str], level: int, env: str) -> None:
    close_lists(lines, stack, level)
    while len(stack) <= level:
        stack.append(env)
        lines.append(rf"\begin{{{env}}}")
    if stack[level] != env:
        close_lists(lines, stack, level - 1)
        stack.append(env)
        lines.append(rf"\begin{{{env}}}")


def render_table(tbl: etree._Element, rels: dict[str, str], caption: str | None) -> list[str]:
    rows = []
    max_cols = 0
    for tr in tbl.xpath("./w:tr", namespaces=NS):
        row = []
        for tc in tr.xpath("./w:tc", namespaces=NS):
            paras = []
            for p in tc.xpath("./w:p", namespaces=NS):
                text = render_inline(p, rels)
                if text:
                    paras.append(text)
            row.append(r"\newline ".join(paras))
        if any(cell.strip() for cell in row):
            rows.append(row)
            max_cols = max(max_cols, len(row))
    if not rows or max_cols == 0:
        return []

    if max_cols == 2:
        spec = r">{\raggedright\arraybackslash}p{0.27\linewidth}>{\raggedright\arraybackslash}p{0.66\linewidth}"
    elif max_cols == 3:
        spec = r">{\raggedright\arraybackslash}p{0.18\linewidth}>{\raggedright\arraybackslash}p{0.39\linewidth}>{\raggedright\arraybackslash}p{0.35\linewidth}"
    else:
        width = round(0.92 / max_cols, 3)
        spec = "".join([rf">{{\raggedright\arraybackslash}}p{{{width}\linewidth}}" for _ in range(max_cols)])

    lines = [r"\begin{longtable}{" + spec + "}"]
    if caption:
        cap = re.sub(r"^Table\s+\d+\s*:\s*", "", caption).strip()
        lines.append(rf"\caption{{{latex_escape(cap)}}}\\")
    lines.append(r"\toprule")
    for idx, row in enumerate(rows):
        padded = row + [""] * (max_cols - len(row))
        lines.append(" & ".join(padded) + r" \\")
        lines.append(r"\midrule" if idx == 0 else r"\addlinespace")
    lines.append(r"\bottomrule")
    lines.append(r"\end{longtable}")
    return lines


def render_constructs_table(caption: str | None) -> list[str]:
    cap = caption or "Table 2: Evaluation Constructs and Associated Variables"
    cap = re.sub(r"^Table\s+\d+\s*:\s*", "", cap).strip()
    rows = [
        (
            "Reputation Structure",
            "EndorseRank score, AWP score, rank ordering, rank divergence",
            "Spearman's rho, Kendall's tau, top-k overlap",
        ),
        (
            "Risk Predictive Validity",
            "Default/liquidation label and score-based prediction features",
            "AUC, precision, recall, F1-score, calibration",
        ),
        (
            "Computational Efficiency",
            "Graph build time, PageRank convergence time, memory usage, iteration count",
            "Runtime, peak memory, iterations to tolerance",
        ),
    ]
    lines = [
        r"\begin{longtable}{>{\raggedright\arraybackslash}p{0.25\linewidth}>{\raggedright\arraybackslash}p{0.36\linewidth}>{\raggedright\arraybackslash}p{0.29\linewidth}}",
        rf"\caption{{{latex_escape(cap)}}}\\",
        r"\toprule",
        r"\textbf{Construct} & \textbf{Associated variables} & \textbf{Operational measures} \\",
        r"\midrule",
    ]
    for row in rows:
        lines.append(" & ".join(latex_escape(cell) for cell in row) + r" \\")
        lines.append(r"\addlinespace")
    lines.extend([r"\bottomrule", r"\end{longtable}", ""])
    return lines


def render_title_page(title_paragraphs: list[str]) -> list[str]:
    clean_parts = [re.sub(r"\\textbf\{([^}]*)\}", r"\1", text) for text in title_paragraphs if text]
    title = clean_parts[0] if clean_parts else ""
    lookup = {part.upper(): part for part in clean_parts}
    lines = [
        r"\begin{titlepage}",
        r"\newgeometry{left=1.18in,right=0.59in,top=1.33in,bottom=0.7in}",
        r"\centering",
        r"\vspace*{0.4cm}",
        r"{\Large\bfseries " + title + r"\par}",
        r"\vfill",
        r"{by\par}",
        r"\vspace{0.7cm}",
        r"{\large\bfseries " + lookup.get("TAEHONG KWON", "TAEHONG KWON") + r"\par}",
        r"\vfill",
        r"{submitted in accordance with the requirements for the degree of\par}",
        r"\vspace{0.7cm}",
        r"{\large\bfseries " + lookup.get("DOCTOR OF PHILOSOPHY", "DOCTOR OF PHILOSOPHY") + r"\par}",
        r"\vspace{0.35cm}",
        r"{in the subject\par}",
        r"\vspace{0.7cm}",
        r"{\large\bfseries " + lookup.get("COMPUTER SCIENCE", "COMPUTER SCIENCE") + r"\par}",
        r"\vfill",
        r"{at the\par}",
        r"\vspace{0.7cm}",
        r"{\large\bfseries " + lookup.get("UNIVERSITY OF SOUTH AFRICA", "UNIVERSITY OF SOUTH AFRICA") + r"\par}",
        r"\vfill",
        r"{SUPERVISOR: Prof. Ernest Mnkandla\par}",
        r"\vspace{0.35cm}",
        r"{CO-SUPERVISOR: Prof. Donatien Koulla Moulla\par}",
        r"\vfill",
        r"{June 2025\par}",
        r"\end{titlepage}",
        r"\restoregeometry",
        "",
    ]
    return lines


def collect_toc_entries(body: list[etree._Element], rels: dict[str, str]) -> list[TocEntry]:
    engine = NumberingEngine.from_docx(SRC)
    entries: list[TocEntry] = []
    label_keys: set[str] = set()
    for el in body:
        if local_name(el) != "p":
            continue
        num = get_num(el)
        if not num or num[0] != "44":
            continue
        text_raw = child_text(el)
        label, title, _page = engine.label_with_suffix("44", num[1], text_raw)
        title_latex = latex_escape(title)
        if paragraph_has_bold(el):
            title_latex = r"\textbf{" + title_latex + "}"
        key = f"sec:{slugify(title)}"
        base = key
        n = 2
        while key in label_keys:
            if title == "Data Analysis" and base == "sec:data-analysis":
                key = "sec:dissertationthesis-outline"
                break
            key = f"{base}-{n}"
            n += 1
        label_keys.add(key)
        entries.append(
            TocEntry(
                label=label,
                title=title,
                title_latex=title_latex,
                label_key=key,
                ilvl=num[1],
            )
        )
    return entries


def render_manual_toc(entries: list[TocEntry]) -> list[str]:
    lines = [
        r"\clearpage",
        r"{\Large\bfseries Table of Contents\par}",
        r"\vspace{0.75em}",
    ]
    for entry in entries:
        indent = r"\hspace*{1.5em}" if entry.ilvl >= 1 else ""
        lines.append(
            rf"{indent}\TOCentry{{{latex_escape(entry.label)}}}{{{{{entry.title_latex}}}}}{{{entry.label_key}}}"
        )
    lines.extend([r"\clearpage", ""])
    return lines


def preamble() -> str:
    return r"""\documentclass[12pt]{article}
\usepackage[a4paper,left=1.18in,right=0.59in,top=1.33in,bottom=1.46in,includefoot]{geometry}
\usepackage{fontspec}
\setmainfont{Times New Roman}
\usepackage{setspace}
\usepackage{hyperref}
\usepackage{enumitem}
\usepackage{tikz}
\usepackage{longtable}
\usepackage{booktabs}
\usepackage{array}
\usepackage[normalem]{ulem}
\usepackage{caption}
\usepackage{amsmath}
\usepackage{amssymb}
\hypersetup{hidelinks}
\setstretch{1.58}
\setlength{\parindent}{0pt}
\setlength{\parskip}{0.03\baselineskip}
\setlist[itemize]{leftmargin=2.2em,labelsep=0.55em,itemsep=0.08\baselineskip,topsep=0.1\baselineskip,parsep=0pt}
\setlist[enumerate]{leftmargin=2.4em,labelsep=0.55em,itemsep=0.08\baselineskip,topsep=0.1\baselineskip,parsep=0pt}
\setcounter{secnumdepth}{0}
\newcommand{\proposalSubheading}[1]{%
  \par\addvspace{0.38\baselineskip}%
  \noindent\textbf{#1}\par\nobreak\addvspace{0.08\baselineskip}%
}
\newcommand{\proposalResultHeading}[1]{%
  \par\addvspace{0.45\baselineskip}%
  \noindent\textbf{#1}\par\nobreak\addvspace{0.06\baselineskip}%
}
\newcommand{\TOCentry}[3]{%
  \noindent\hyperref[#3]{\makebox[2.4em][l]{#1}#2}\nobreak\dotfill\ \hyperref[#3]{\pageref*{#3}}\par\vspace{0.15em}%
}
\begin{document}
"""


class NumberingState:
    def __init__(self) -> None:
        self.engines: dict[str, NumberingEngine] = {}
        self.outline = NumberingEngine.from_docx(SRC)
        self.active_num_id: str | None = None

    def engine(self, num_id: str) -> NumberingEngine:
        if num_id not in self.engines:
            self.engines[num_id] = NumberingEngine.from_docx(SRC)
        return self.engines[num_id]

    def advance(self, num_id: str, ilvl: int) -> str:
        if self.active_num_id != num_id:
            self.active_num_id = num_id
        return self.engine(num_id).advance(num_id, ilvl)

    def outline_label(self, ilvl: int) -> str:
        return self.outline.advance("44", ilvl)


def heading_content(p: etree._Element, text_raw: str, rels: dict[str, str]) -> str:
    if paragraph_has_bold(p) and (is_outline_level0(p, text_raw) or paragraph_max_size(p) >= 40):
        return r"\textbf{" + latex_escape(text_raw) + "}"
    return render_inline(p, rels)


def emit_heading(
    lines: list[str],
    cmd: str,
    label: str,
    p: etree._Element,
    text_raw: str,
    rels: dict[str, str],
    add_to_toc: bool = True,
    label_keys: set[str] | None = None,
) -> str:
    latex_text = heading_content(p, text_raw, rels)
    title = prefix_title(label, latex_text)
    key = f"sec:{slugify(text_raw)}"
    if label_keys is not None:
        base = key
        n = 2
        while key in label_keys:
            key = f"{base}-{n}"
            n += 1
        label_keys.add(key)
    if cmd == "section" and re.fullmatch(r"\d+", label or ""):
        lines.append(r"\clearpage")
    lines.append(r"\phantomsection")
    lines.append(rf"\{cmd}*{{{title}}}")
    lines.append(rf"\label{{{key}}}")
    if add_to_toc and text_raw.lower() not in {"abstract"}:
        toc_level = "section" if cmd == "section" else "subsection"
        toc_title = prefix_label_plain(label, text_raw)
        lines.append(rf"\addcontentsline{{toc}}{{{toc_level}}}{{{latex_escape(toc_title)}}}")
    lines.append("")
    return key


def is_internal_heading_label(label: str, style: str, num_id: str = "") -> bool:
    if label in {"•", "–", "-"}:
        return True
    if re.fullmatch(r"\d+\.", label or ""):
        return True
    if style == "2" and num_id not in {"32", "22"}:
        return True
    return False


def emit_internal_heading(lines: list[str], label: str, p: etree._Element, text_raw: str, rels: dict[str, str]) -> None:
    title = prefix_title(label, heading_content(p, text_raw, rels))
    title = re.sub(r"\\textbf\{([^{}]*)\}", r"\1", title)
    lines.append(rf"\proposalSubheading{{{title}}}")
    lines.append("")


def format_item_label(label: str) -> str:
    if label == "•":
        return r"\textbullet"
    if label in {"–", "-"}:
        return r"\textendash"
    return latex_escape(label)


def prefix_label_plain(label: str, text: str) -> str:
    if not label:
        return text
    if label in {"•", "–", "-"}:
        return f"{label} {text}"
    sep = " " if not label.endswith(".") else " "
    return f"{label}{sep}{text}"


def conceptual_model_tex() -> str:
    return r"""\begin{tikzpicture}[
  font=\small,
  box/.style={draw, rounded corners, align=center, minimum width=3.6cm, minimum height=1.1cm},
  smallbox/.style={draw, rounded corners, align=center, minimum width=3.0cm, minimum height=0.9cm},
  arrow/.style={->, thick}
]
\node[box] (center) at (0,0) {EndorseRank vs. AWP};
\node[smallbox] (h1) at (-4.8,1.9) {H1: Divergence};
\node[smallbox] (rep) at (-4.8,-1.9) {Reputation\\Structure};
\node[smallbox] (h2) at (0,2.2) {H2: Predictive};
\node[smallbox] (risk) at (0,-2.2) {Risk Predictive\\Validity};
\node[smallbox] (h3) at (4.8,1.9) {H3: Efficiency};
\node[smallbox] (eff) at (4.8,-1.9) {Computational\\Efficiency};
\draw[arrow] (center) -- (h1);
\draw[arrow] (center) -- (h2);
\draw[arrow] (center) -- (h3);
\draw[arrow] (h1) -- (rep);
\draw[arrow] (h2) -- (risk);
\draw[arrow] (h3) -- (eff);
\end{tikzpicture}
"""


def write_support_files(base_dir: Path) -> None:
    figures = base_dir / "Figures"
    figures.mkdir(parents=True, exist_ok=True)
    (figures / "conceptual-model.tex").write_text(conceptual_model_tex(), encoding="utf-8", newline="\n")


def write_part(path: Path, part: list[str]) -> None:
    path.write_text("\n".join(part).strip() + "\n", encoding="utf-8", newline="\n")


def write_fidelity_project(full_text: str) -> None:
    if FIDELITY_DIR.exists():
        shutil.rmtree(FIDELITY_DIR)
    for rel in ["Config", "01-Intro", "02-Content", "03-End", "Figures"]:
        (FIDELITY_DIR / rel).mkdir(parents=True, exist_ok=True)
    write_support_files(FIDELITY_DIR)

    lines = full_text.splitlines()
    begin_idx = lines.index(r"\begin{document}")
    end_idx = len(lines) - 1 - list(reversed(lines)).index(r"\end{document}")
    preamble_lines = lines[:begin_idx]
    body = lines[begin_idx + 1 : end_idx]
    write_part(FIDELITY_DIR / "Config" / "preamble.tex", preamble_lines)

    title_start = body.index(r"\begin{titlepage}")
    title_end = body.index(r"\end{titlepage}", title_start)
    restore_idx = title_end + 1 if title_end + 1 < len(body) and body[title_end + 1] == r"\restoregeometry" else title_end
    abstract_start = next(
        i
        for i, line in enumerate(body)
        if line == r"\phantomsection" and i + 1 < len(body) and body[i + 1].startswith(r"\section*{Abstract}")
    )
    toc_title = body.index(r"{\Large\bfseries Table of Contents\par}")
    toc_start = toc_title - 1 if toc_title > 0 and body[toc_title - 1] == r"\clearpage" else toc_title
    toc_end = next(i for i in range(toc_title, len(body)) if body[i] == r"\clearpage")

    sections: list[tuple[int, int]] = []
    for i, line in enumerate(body):
        m = re.match(r"\\section\*\{(\d+)\\? .*", line)
        if not m:
            continue
        start = i
        if i >= 2 and body[i - 2] == r"\clearpage" and body[i - 1] == r"\phantomsection":
            start = i - 2
        elif i >= 1 and body[i - 1] == r"\phantomsection":
            start = i - 1
        sections.append((int(m.group(1)), start))

    write_part(FIDELITY_DIR / "01-Intro" / "01-Title.tex", body[title_start : restore_idx + 1])
    write_part(FIDELITY_DIR / "01-Intro" / "02-Abstract.tex", body[abstract_start:toc_start])
    write_part(FIDELITY_DIR / "01-Intro" / "03-TOC.tex", body[toc_start : toc_end + 1])

    input_lines = [
        r"\input{Config/preamble.tex}",
        r"\begin{document}",
        r"\input{01-Intro/01-Title.tex}",
        r"\input{01-Intro/02-Abstract.tex}",
        r"\input{01-Intro/03-TOC.tex}",
    ]

    for idx, (section_no, start) in enumerate(sections):
        stop = sections[idx + 1][1] if idx + 1 < len(sections) else len(body)
        part = body[start:stop]
        if section_no == 10:
            ref_idx = next((i for i, line in enumerate(part) if line.startswith(r"\subsection*{9.1 References}")), None)
            if ref_idx is not None:
                write_part(FIDELITY_DIR / "02-Content" / "Chapter-10.tex", part[:ref_idx])
                write_part(FIDELITY_DIR / "03-End" / "bibliography.tex", part[ref_idx:])
                input_lines.append(r"\input{02-Content/Chapter-10.tex}")
                input_lines.append(r"\input{03-End/bibliography.tex}")
                continue
        if section_no == 11:
            write_part(FIDELITY_DIR / "03-End" / "appendix.tex", part)
            input_lines.append(r"\input{03-End/appendix.tex}")
        else:
            write_part(FIDELITY_DIR / "02-Content" / f"Chapter-{section_no:02d}.tex", part)
            input_lines.append(rf"\input{{02-Content/Chapter-{section_no:02d}.tex}}")

    input_lines.append(r"\end{document}")
    FIDELITY_MAIN.write_text("\n".join(input_lines) + "\n", encoding="utf-8", newline="\n")
    (FIDELITY_DIR / "build.ps1").write_text(
        '$ErrorActionPreference = "Stop"\nSet-Location $PSScriptRoot\n\nxelatex -interaction=nonstopmode main.tex\nxelatex -interaction=nonstopmode main.tex\n\nWrite-Host "Built main.pdf"\n',
        encoding="utf-8",
        newline="\n",
    )


def convert() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(SRC) as zf:
        rels = parse_relationships(zf)
        document = etree.fromstring(zf.read("word/document.xml"))
        body = document.xpath("./w:body/*", namespaces=NS)

        abstract_idx = next(
            (i for i, el in enumerate(body) if local_name(el) == "p" and child_text(el) == "Abstract"),
            0,
        )

        title_paragraphs = [
            render_inline(el, rels)
            for el in body[:abstract_idx]
            if local_name(el) == "p" and render_inline(el, rels)
        ]
        toc_entries = collect_toc_entries(body, rels)

        lines: list[str] = [preamble()]
        lines.extend(render_title_page(title_paragraphs))

        numbering = NumberingState()
        list_stack: list[str] = []
        list_base_level: int | None = None
        pending_caption: str | None = None
        current_section = ""
        table_count = 0
        paragraph_count = 0
        past_toc = False
        label_keys: set[str] = set()

        for el in body[abstract_idx:]:
            name = local_name(el)
            if name == "sectPr":
                continue
            if name == "tbl":
                close_lists(lines, list_stack)
                list_base_level = None
                table_count += 1
                lines.extend(render_table(el, rels, pending_caption))
                pending_caption = None
                lines.append("")
                continue
            if name != "p":
                continue

            text_raw = child_text(el)
            text = render_inline(el, rels)
            style = get_para_style(el)
            num = get_num(el)

            if not text_raw and not el.xpath(".//m:oMathPara", namespaces=NS):
                if num is not None:
                    numbering.advance(num[0], num[1])
                continue

            if text_raw == "Abstract":
                close_lists(lines, list_stack)
                list_base_level = None
                current_section = text_raw
                emit_heading(lines, "section", "", el, text_raw, rels, add_to_toc=False, label_keys=label_keys)
                paragraph_count += 1
                continue

            if text_raw == "Table of Contents" and not past_toc:
                close_lists(lines, list_stack)
                list_base_level = None
                lines.extend(render_manual_toc(toc_entries))
                past_toc = True
                continue

            if num and num[0] == "44":
                continue

            if is_caption(text_raw, style):
                close_lists(lines, list_stack)
                list_base_level = None
                pending_caption = text_raw
                continue

            if el.xpath(".//m:oMathPara", namespaces=NS) and not re.sub(
                r"\s+", "", "".join(el.xpath(".//w:t/text()", namespaces=NS))
            ):
                close_lists(lines, list_stack)
                list_base_level = None
                math = render_math(el.xpath(".//m:oMathPara", namespaces=NS)[0])
                lines.extend([r"\[" + math + r"\]", ""])
                continue

            if is_outline_level0(el, text_raw):
                close_lists(lines, list_stack)
                list_base_level = None
                label = numbering.outline_label(0)
                current_section = text_raw
                emit_heading(lines, "section", label, el, text_raw, rels, label_keys=label_keys)
                paragraph_count += 1
                continue

            if is_outline_level1(el, text_raw, style):
                close_lists(lines, list_stack)
                list_base_level = None
                if pending_caption and text_raw == "Conceptual Model":
                    lines.extend(render_constructs_table(pending_caption))
                    pending_caption = None
                label = numbering.outline_label(1)
                current_section = text_raw
                emit_heading(lines, "subsection", label, el, text_raw, rels, label_keys=label_keys)
                paragraph_count += 1
                continue

            if is_numbered_heading(el, style):
                close_lists(lines, list_stack)
                list_base_level = None
                assert num is not None
                if num[0] == "32" and num[1] == 1:
                    numbering.outline.advance("44", 1)
                label = numbering.advance(num[0], num[1])
                cmd = heading_command(label, num[1], style, num[0])
                current_section = text_raw
                if is_internal_heading_label(label, style, num[0]):
                    emit_internal_heading(lines, label, el, text_raw, rels)
                else:
                    emit_heading(lines, cmd, label, el, text_raw, rels, label_keys=label_keys)
                paragraph_count += 1
                continue

            if current_section.lower() == "references" and text and style == "2" and num and num[0] == "45":
                close_lists(lines, list_stack)
                list_base_level = None
                lines.append(r"\hangindent=0.5in \hangafter=1 " + text + r"\par")
                lines.append("")
                paragraph_count += 1
                continue

            if num is not None:
                label = numbering.advance(num[0], num[1])
                scheme = numbering.engine(num[0]).schemes.get(num[0])
                level_def = scheme.levels.get(num[1]) if scheme else None
                is_bullet = level_def.fmt == "bullet" if level_def else label in {"•", "–", "-"}
                env = "itemize" if is_bullet else "enumerate"
                if list_base_level is None:
                    list_base_level = num[1]
                normalized_level = max(0, num[1] - list_base_level)
                open_list(lines, list_stack, normalized_level, env)
                if label in {"•", "–", "-"}:
                    lines.append(rf"\item[{format_item_label(label)}] {text}")
                elif label:
                    lines.append(rf"\item[{format_item_label(label)}] {text}")
                else:
                    lines.append(r"\item " + text)
                paragraph_count += 1
                continue

            close_lists(lines, list_stack)
            list_base_level = None
            numbering.active_num_id = None

            if get_alignment(el) == "center":
                lines.append(r"\begin{center}" + text + r"\end{center}")
            elif re.match(r"^ER\d+:\s+", text_raw):
                lines.append(rf"\proposalResultHeading{{{text}}}")
            elif re.match(r"^(Analysis|Measurement):$", text_raw):
                lines.append(rf"\proposalSubheading{{{text}}}")
            else:
                lines.append(text + "\n")
            lines.append("")
            paragraph_count += 1

        close_lists(lines, list_stack)
        lines.append(r"\end{document}")

    full_text = "\n".join(lines)
    OUT_TEX.write_text(full_text, encoding="utf-8", newline="\n")
    write_support_files(OUT_DIR)
    write_fidelity_project(full_text)
    REPORT.write_text(
        "\n".join(
            [
                f"Source: {SRC}",
                f"Output: {OUT_TEX}",
                f"Fidelity project: {FIDELITY_MAIN}",
                "Method: direct OOXML parsing with Word numbering fidelity.",
                f"Title paragraphs: {len(title_paragraphs)}",
                f"Body paragraphs emitted: {paragraph_count}",
                f"Tables emitted: {table_count}",
                f"Manual TOC entries: {len(toc_entries)}",
                f"Relationships parsed: {len(rels)}",
            ]
        ),
        encoding="utf-8",
        newline="\n",
    )


if __name__ == "__main__":
    convert()
