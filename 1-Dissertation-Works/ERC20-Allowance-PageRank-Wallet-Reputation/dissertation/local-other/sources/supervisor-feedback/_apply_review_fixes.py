# -*- coding: utf-8 -*-
"""Apply the 2026-09 supervisor-review revisions to the review DOCX *in place*.

The DOCX is the LaTeX->Word export that Moulla and Attipoe annotated (27 Word
comments).  This script ports the revised English LaTeX (``2-Dissertation-Draft/en``)
into that file so that both artefacts say the same thing:

* replaces / inserts revised text at the comment anchors and in the affected
  sections (new sections: research objectives, literature/methodology summaries,
  literature summary table, research gap, temporal holdout, objectives
  achievement, RQ answers, chapter-link paragraphs);
* withdraws GF-PR / SRQ1 / SC1 from the main narrative (comment 14);
* updates every benchmark / robustness number from ``eval_summary.json``
  (one timing protocol, 5 timed repeats) and removes headline repetition;
* removes bold from body text (meeting 2026-09-09) and renumbers the citations
  in order of first appearance using the LaTeX mapping (``_cite_mapping.txt``),
  reorders the reference list, inserts the new 2020-2026 sources and drops
  uncited entries;
* leaves a **Taehong Kwon** comment on every edited span and a threaded
  **Taehong Kwon** reply under each of the 27 supervisor comments (Word COM);
* updates ``README.md``.

Run with the system interpreter (needs ``lxml``; ``pywin32`` for the Word pass)::

    python _apply_review_fixes.py                 # XML pass + Word reply pass
    python _apply_review_fixes.py --no-word       # XML pass only
    python _apply_review_fixes.py --out <path>    # write elsewhere (dry run)

The LaTeX texts are read from the ``en/`` chapters and de-LaTeXed here, so the
DOCX never drifts from the LaTeX wording.
"""
from __future__ import annotations

import argparse
import json
import random
import re
import shutil
import sys
import unicodedata
import zipfile
from copy import deepcopy
from pathlib import Path

from lxml import etree

HERE = Path(__file__).resolve().parent
WORKS = HERE.parents[2]  # dissertation/ (this folder is dissertation/local-other/sources/supervisor-feedback)
DOCX = HERE / "Taehong_Thesis_Reviewed_Moulla_Attipoe.docx"
EN = WORKS / "overleaf-github"
MR = WORKS / "wallet-reputation-experiments"
SUMMARY = MR / "data" / "2-processed-tables-and-evaluations" / "eval_summary.json"
MAPPING = MR / "scripts" / "_cite_mapping.txt"
README = HERE / "README.md"

AUTHOR = "Taehong Kwon"
INITIALS = "TK"
TODAY = "2026-09-12"
STAMP = f"{TODAY}T09:00:00Z"
REPO_URL = "https://github.com/abitocodes/phd_works"
COMMIT = "0c70518a35540c8b56be66b52452cb94ca3fb916"

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
W14_NS = "http://schemas.microsoft.com/office/word/2010/wordml"
W15_NS = "http://schemas.microsoft.com/office/word/2012/wordml"
W16CID_NS = "http://schemas.microsoft.com/office/word/2016/wordml/cid"
W16CEX_NS = "http://schemas.microsoft.com/office/word/2018/wordml/cex"
XML_NS = "http://www.w3.org/XML/1998/namespace"


def qn(tag: str) -> str:
    pfx, local = tag.split(":")
    ns = {"w": W_NS, "w14": W14_NS, "w15": W15_NS, "w16cid": W16CID_NS, "w16cex": W16CEX_NS, "xml": XML_NS}[pfx]
    return "{%s}%s" % (ns, local)


def localname(el) -> str:
    return etree.QName(el).localname


LOG: list[str] = []


def log(msg: str) -> None:
    LOG.append(msg)
    print(msg)


# --------------------------------------------------------------------------- numbers
def load_numbers() -> dict:
    d = json.loads(SUMMARY.read_text(encoding="utf-8"))
    b = d["benchmark"]
    fam = d["alignment"]["bootstrap"]["family_ci"]
    inter = d["alignment"]["inter_method"]
    n = {
        "er_rt": b["endorserank"]["runtime_sec_mean"],
        "er_sd": b["endorserank"]["runtime_sec_std"],
        "awp_rt": b["awp"]["runtime_sec_mean"],
        "awp_sd": b["awp"]["runtime_sec_std"],
        "er_mem": b["endorserank"]["peak_memory_mb"],
        "awp_mem": b["awp"]["peak_memory_mb"],
        "er_it": int(round(b["endorserank"]["iterations_mean"])),
        "awp_it": int(round(b["awp"]["iterations_mean"])),
        "er_E": b["endorserank"]["edge_count"],
        "awp_E": b["awp"]["edge_count"],
        "er_V": b["endorserank"]["node_count"],
        "awp_V": b["awp"]["node_count"],
        "pool_N": d["wallet_pool_meta"]["extraction_wallet_count"],
        "pool_supp": d["wallet_pool_meta"]["supplemental_count"],
        "scaling_rows": d["benchmark_scaling"]["rows"],
        "tier2_rows": d["benchmark_tier2"]["rows"],
        "damping_rows": d["robustness"]["damping_sweep"]["rows"],
        "ssw_rows": d["robustness"]["sample_size_sweep"]["rows"],
        "fam": fam,
        "inter": inter,
        "tau_diff": d["alignment"]["bootstrap"]["tau_diff"],
        "n_boot": d["bootstrap_protocol"]["n_boot"],
        "seed": d["bootstrap_protocol"]["seed"],
        "repeats": d["timing_protocol"]["timed_repeats"],
    }
    n["speedup"] = n["awp_rt"] / n["er_rt"]
    return n


def f3(x: float) -> str:
    return f"{x:.3f}"


def f1(x: float) -> str:
    return f"{x:.1f}"


def ci(lo: float, hi: float) -> str:
    return f"[{lo:.3f}, {hi:.3f}]"


def ic(n: int) -> str:
    return f"{n:,}"


# --------------------------------------------------------------------------- LaTeX -> text
CH_FILES = {
    "abstract": EN / "01-Intro" / "02-Abstract.tex",
    "ch1": EN / "Chapter-01-Introduction-and-Research-Problem" / "index.tex",
    "ch2": EN / "Chapter-02-Literature-Review-and-Theoretical-Framework" / "index.tex",
    "ch3": EN / "Chapter-03-Research-Methodology" / "index.tex",
    "ch4": EN / "Chapter-04-Implementation-and-Empirical-Results" / "index.tex",
    "ch5": EN / "Chapter-05-Discussion" / "index.tex",
    "ch6": EN / "Chapter-06-Conclusion-and-Future-Work" / "index.tex",
    "app": EN / "Chapter-08-Appendix" / "index.tex",
    "appb": EN / "Chapter-08-Appendix" / "appendix-b.tex",
    "appc": EN / "Chapter-08-Appendix" / "appendix-c.tex",
    "appd": EN / "Chapter-08-Appendix" / "appendix-d.tex",
    "appe": EN / "Chapter-08-Appendix" / "appendix-e.tex",
    "refs": EN / "Chapter-07-References" / "index.tex",
}

# DOCX table / figure numbers for LaTeX labels (the DOCX has literal captions).
FIXED_LABELS = {
    "ch:introduction": "1", "ch:literature": "2", "ch:methodology": "3", "ch:results": "4",
    "ch:discussion": "5", "ch:conclusion": "6", "ch:references": "7", "ch:appendix": "8",
    "ch:appendix-eval": "8.1", "ch:appendix-archive": "8.4", "ch:appendix-ethics": "8.6",
    "tab:primary-methods-preview": "1.1", "tab:hrq-claim-map": "1.3", "tab:literature-summary": "2.2",
    "tab:method-comparison-lit": "2.1", "tab:notation-methods": "3.1", "tab:dataset": "4.1",
    "tab:benchmark-runtime": "4.2", "tab:benchmark-scaling": "4.3", "tab:robustness-damping": "4.4",
    "tab:robustness-tokens": "4.5", "tab:robustness-sample-size": "4.6", "tab:alignment-family-ci": "4.7",
    "tab:alignment-transfer": "4.8", "tab:alignment-allowance": "4.9", "tab:alignment-inverse-risk": "4.10",
    "tab:alignment-sybil-stability": "4.11", "tab:alignment-gmx": "4.12", "tab:holdout-spenders": "4.13",
    "tab:tau-diff": "4.14", "tab:objectives-achievement": "5.1",
    "tab:benchmark-scaling-incohort": "8.1", "tab:alignment-summary": "8.2", "tab:parameter-summary": "8.3",
    "tab:alignment-seven-methods": "8.4", "tab:alignment-six-aave-methods": "8.5",
    "fig:allowance-sequence": "2.1", "fig:random-surfer": "2.2", "fig:conceptual-model": "2.3",
    "fig:pipeline-architecture": "3.1", "fig:logistic-decay-methods": "3.2",
    "fig:runtime-scaling": "4.4", "fig:damping-sensitivity": "4.5", "fig:alignment-heatmap": "4.6",
    "fig:score-distributions": "4.7", "fig:rank-scatter": "4.8",
}


def load_labels() -> dict:
    labels = dict(FIXED_LABELS)
    toc = (EN / "01-Intro" / "03-TOC.tex").read_text(encoding="utf-8")
    for m in re.finditer(r"\\TOCentry\{([^{}]*)\}\{\{.*?\}\}\{([^{}]+)\}", toc):
        num, lab = m.group(1).strip(), m.group(2).strip()
        if num and lab not in labels:
            labels[lab] = num
    # sub-subsection numbers are not listed in the TOC: derive them from heading order
    for key, ch in (("ch1", 1), ("ch2", 2), ("ch3", 3), ("ch4", 4), ("ch5", 5), ("ch6", 6)):
        sec, sub = 0, 0
        for m in re.finditer(r"\\dissertationSub(sub)?heading\[([^\]]+)\]", CH_FILES[key].read_text(encoding="utf-8")):
            if m.group(1):
                sub += 1
                labels.setdefault(m.group(2), f"{ch}.{sec}.{sub}")
            else:
                sec, sub = sec + 1, 0
                labels.setdefault(m.group(2), f"{ch}.{sec}")
    return labels


LABELS: dict = {}
UNRESOLVED: set = set()

GREEK = {
    "tau": "τ", "rho": "ρ", "Delta": "Δ", "alpha": "α", "beta": "β", "gamma": "γ", "lambda": "λ",
    "sigma": "σ", "mu": "μ", "varepsilon": "ε", "epsilon": "ε", "delta": "δ", "theta": "θ", "pi": "π",
    "phi": "φ", "omega": "ω", "eta": "η", "kappa": "κ", "ell": "ℓ",
}
SYMBOLS = {
    "times": "×", "approx": "≈", "leq": "≤", "le": "≤", "geq": "≥", "ge": "≥", "neq": "≠", "ne": "≠",
    "pm": "±", "in": "∈", "to": "→", "rightarrow": "→", "Rightarrow": "⇒", "cdot": "·", "ldots": "…",
    "dots": "…", "infty": "∞", "mid": "|", "vert": "|", "lvert": "|", "rvert": "|", "sum": "Σ",
    "log": "log", "max": "max", "min": "min", "setminus": "∖", "cup": "∪", "cap": "∩", "subseteq": "⊆",
    "propto": "∝", "sim": "~", "prime": "′", "circ": "∘", "quad": " ", "qquad": "  ", "star": "*",
    "top": "⊤", "exp": "exp", "forall": "∀", "exists": "∃", "emptyset": "∅", "partial": "∂", "nabla": "∇",
    "langle": "⟨", "rangle": "⟩", "lfloor": "⌊", "rfloor": "⌋", "lceil": "⌈", "rceil": "⌉", "ll": "≪", "gg": "≫",
    "colon": ":", "mathbb": "", "boldsymbol": "", "mathbf": "", "mathrm": "", "text": "", "mathcal": "",
}
SUP = str.maketrans("0123456789-+", "⁰¹²³⁴⁵⁶⁷⁸⁹⁻⁺")
SUB = str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉")


def _strip_braces(s: str) -> str:
    return s.replace("{", "").replace("}", "")


def _brace_group(s: str, i: int) -> tuple[str, int]:
    """Content of the brace group starting at s[i] == '{' and the index after its closing brace."""
    depth, j = 0, i
    while j < len(s):
        if s[j] == "{":
            depth += 1
        elif s[j] == "}":
            depth -= 1
            if depth == 0:
                return s[i + 1:j], j + 1
        j += 1
    return s[i + 1:], len(s)


def _apply_two_arg(s: str, name: str, fmt) -> str:
    key = "\\" + name
    while True:
        k = s.find(key)
        if k < 0 or k + len(key) >= len(s) or s[k + len(key)] != "{":
            return s
        a, e1 = _brace_group(s, k + len(key))
        while e1 < len(s) and s[e1] in " \n\t":
            e1 += 1
        if e1 >= len(s) or s[e1] != "{":
            return s
        b, e2 = _brace_group(s, e1)
        s = s[:k] + fmt(a, b) + s[e2:]


def _apply_one_arg(s: str, name: str, fmt) -> str:
    key = "\\" + name
    while True:
        k = s.find(key)
        if k < 0:
            return s
        j = k + len(key)
        while j < len(s) and s[j] == " ":
            j += 1
        if j < len(s) and s[j] == "{":
            a, e = _brace_group(s, j)
        elif j < len(s) and re.match(r"[A-Za-z0-9]", s[j]):
            a, e = s[j], j + 1
        else:
            return s
        s = s[:k] + fmt(a) + s[e:]


def math_to_text(m: str) -> str:
    s = m
    s = re.sub(r"\\begin\{cases\}(.*?)\\end\{cases\}",
               lambda mm: "{" + "; ".join(" if ".join(c.strip() for c in row.split("&")) for row in mm.group(1).split("\\\\") if row.strip()) + "}",
               s, flags=re.S)
    s = re.sub(r"\\(?:left|right|,|;|!|displaystyle|bigl|bigr|Bigl|Bigr|big|Big|nonumber|quad|qquad)\b", " ", s)
    for _ in range(3):
        s = re.sub(r"\\(?:mathrm|text|mathbf|mathit|operatorname|mathcal|textrm|mathsf|boldsymbol|textit)\{([^{}]*)\}", r"\1", s)
    s = _apply_two_arg(s, "frac", lambda a, b: f"({a})/({b})" if (len(a) > 3 or len(b) > 3) else f"{a}/{b}")
    s = _apply_two_arg(s, "tfrac", lambda a, b: f"({a})/({b})" if (len(a) > 3 or len(b) > 3) else f"{a}/{b}")
    s = _apply_one_arg(s, "sqrt", lambda a: f"√({a})")
    s = _apply_one_arg(s, "bar", lambda a: a + "\u0304")
    s = _apply_one_arg(s, "hat", lambda a: a + "\u0302")
    s = _apply_one_arg(s, "tilde", lambda a: a + "\u0303")
    s = s.replace("\\{", "\u0001").replace("\\}", "\u0002")
    s = s.replace("{,}", ",")
    s = s.replace("\\_", "_").replace("\\%", "%")

    def cmd(mm):
        name = mm.group(1)
        if name in GREEK:
            return GREEK[name]
        if name in SYMBOLS:
            return SYMBOLS[name]
        UNRESOLVED.add("\\" + name + " @ " + CURRENT_CTX)
        return name

    s = re.sub(r"\\([A-Za-z]+)", cmd, s)

    def sup(mm):
        inner = _strip_braces(mm.group(1) if mm.group(1) is not None else mm.group(2))
        if re.fullmatch(r"[-+]?\d+", inner):
            return inner.translate(SUP)
        if inner in ("⊤", "*", "′"):
            return inner
        if re.fullmatch(r"[A-Za-z]{2,}", inner):
            return f"({inner})"  # T_2^{start} -> T₂(start)
        return "^" + inner if len(inner) == 1 else f"^({inner})"

    def sub(mm):
        inner = _strip_braces(mm.group(1) if mm.group(1) is not None else mm.group(2))
        if re.fullmatch(r"\d+", inner):
            return inner.translate(SUB)
        return "_" + inner if len(inner) <= 3 or re.fullmatch(r"[A-Za-z]+", inner) else f"_({inner})"

    s = re.sub(r"\^\{([^{}]*)\}|\^(\S)", sup, s)
    s = re.sub(r"_\{([^{}]*)\}|_(\S)", sub, s)
    s = _strip_braces(s)
    s = s.replace("\u0001", "{").replace("\u0002", "}")
    s = s.replace("&", " ")
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"\s*=\s*", " = ", s)
    s = re.sub(r"\s*(≤|≥|≈|≠|∈|→|<|>)\s*", r" \1 ", s)
    return s


ACCENTS = {'"': "\u0308", "'": "\u0301", "`": "\u0300", "^": "\u0302", "~": "\u0303", "=": "\u0304", ".": "\u0307",
           "u": "\u0306", "v": "\u030c", "H": "\u030b", "c": "\u0327", "k": "\u0328", "r": "\u030a", "d": "\u0323"}


def _accent(mm):
    acc, ch = mm.group(1), mm.group(2)
    return unicodedata.normalize("NFC", ch + ACCENTS[acc])


def delatex(s: str) -> str:
    """LaTeX fragment -> plain text with [[n]] citation and {{i:...}} italic markers."""
    s = re.sub(r"(?<!\\)%.*", "", s)
    s = s.replace("\\phantomsection", "")
    s = re.sub(r"\\label\{[^{}]*\}", "", s)
    s = re.sub(r"\\(?:begin|end)\{(?:center|small|footnotesize|flushleft|sloppypar|samepage)\}", " ", s)
    s = re.sub(r"\\(?:bigl|bigr|Bigl|Bigr|big|Big|left|right)\b", "", s)
    s = re.sub(r"\\cend\{([^{}]*)\}", lambda m: "[[" + m.group(1).replace(" ", "") + "]]", s)
    s = re.sub(r"Equations~\\eqref\{eq:([^{}]*)\}--\\eqref\{eq:([^{}]*)\}", r"The equations from \1 to \2", s)
    s = re.sub(r"(?:Equation|Eq\.)?~?\\(?:eq)?ref\s*\{eq:([^{}]*)\}", r"the \1 equation", s)
    s = re.sub(r"\\(?:S|ref)\s*\{([^{}]*)\}", lambda m: _ref(m.group(1)), s)
    s = re.sub(r"\\S", "§", s)
    s = re.sub(r"\\href\{[^{}]*\}\{([^{}]*)\}", r"\1", s)
    s = re.sub(r"\\url\{([^{}]*)\}", r"\1", s)
    s = re.sub(r"\\footnote\{((?:[^{}]|\{[^{}]*\})*)\}", r" (\1)", s)
    # accents
    s = re.sub(r"\\([\"'`^~=.uvHckrd])\{(\w)\}", _accent, s)
    s = re.sub(r"\\([\"'`^~=])(\w)", _accent, s)
    s = s.replace("\\ss", "ß").replace("\\o{}", "ø").replace("\\o ", "ø ").replace("\\ae", "æ")
    # math
    s = re.sub(r"\$([^$]+)\$", lambda m: math_to_text(m.group(1)), s)
    s = re.sub(r"\\\((.+?)\\\)", lambda m: math_to_text(m.group(1)), s)
    # inline formatting (innermost first, repeat)
    for _ in range(4):
        s2 = re.sub(r"\\(?:textit|emph)\{([^{}]*)\}", r"{{i:\1}}", s)
        s2 = re.sub(r"\\(?:texttt|textbf|textsc|textrm|textnormal|mbox|text|textsf)\{([^{}]*)\}", r"\1", s2)
        if s2 == s:
            break
        s = s2
    s = re.sub(r"\\(?:noindent|centering|clearpage|newpage|par|smallskip|medskip|bigskip|hfill|linebreak)\b", " ", s)
    s = s.replace("\\\\", " ")
    s = s.replace("\\%", "%").replace("\\&", "&").replace("\\_", "_").replace("\\#", "#").replace("\\$", "$")
    s = s.replace("\\{", "{").replace("\\}", "}")
    s = s.replace("~", " ").replace("\\,", " ").replace("\\;", " ").replace("\\ ", " ").replace("\\-", "")
    s = s.replace("---", "—").replace("--", "–")
    s = s.replace("``", "“").replace("''", "”").replace("`", "‘")
    s = re.sub(r"(\w)'(\w)", "\\1’\\2", s)
    s = re.sub(r"'(?=[\s.,;:)])", "’", s)
    s = re.sub(r"(?<=[\s(])'", "‘", s)
    # leftover commands
    for m in re.finditer(r"\\([A-Za-z]+)", s):
        UNRESOLVED.add("\\" + m.group(1) + " @ " + CURRENT_CTX)
    s = re.sub(r"\\([A-Za-z]+)\s*", r"\1 ", s)
    # protect markers, strip braces
    s = s.replace("{{i:", "\u0003").replace("}}", "\u0004")
    s = s.replace("{", "").replace("}", "")
    s = s.replace("\u0003", "{{i:").replace("\u0004", "}}")
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r" +([,.;:)])", r"\1", s)
    s = re.sub(r"\( ", "(", s)
    return s.strip()


def _ref(label: str) -> str:
    label = label.strip()
    if label in LABELS:
        return LABELS[label]
    UNRESOLVED.add("ref:" + label + " @ " + CURRENT_CTX)
    return "?"


def tex_source(key: str) -> str:
    return CH_FILES[key].read_text(encoding="utf-8")


def fig_caption(key: str, label: str) -> str:
    """Plain-text caption of the figure whose \\label follows its \\caption (one brace level of nesting)."""
    global CURRENT_CTX
    src = tex_source(key)
    m = re.search(r"\\caption\{((?:[^{}]|\{(?:[^{}]|\{[^{}]*\})*\})*)\}\s*\\label\{" + re.escape(label) + r"\}", src)
    if not m:
        raise KeyError(f"caption for {label} not in {key}")
    CURRENT_CTX = f"{key}:{label}"
    return delatex(m.group(1))


HEADING_RE = re.compile(r"^\\(dissertationSub(?:sub)?heading|chapter|section)\b", re.M)


CURRENT_CTX = ""


def tex_section(key: str, label: str) -> str:
    global CURRENT_CTX
    src = tex_source(key)
    m = re.search(r"\\dissertationSub(?:sub)?heading\[" + re.escape(label) + r"\]\{[^\n]*\}\n", src)
    if not m:
        raise KeyError(f"label {label} not in {key}")
    start = m.end()
    m2 = HEADING_RE.search(src, start)
    CURRENT_CTX = f"{key}:{label}"
    return src[start: m2.start() if m2 else len(src)]


def tex_preamble(key: str) -> str:
    global CURRENT_CTX
    src = tex_source(key)
    m = re.search(r"\\label\{ch:[^{}]*\}\n", src)
    start = m.end()
    m2 = HEADING_RE.search(src, start)
    CURRENT_CTX = f"{key}:preamble"
    return src[start: m2.start() if m2 else len(src)]


def split_paras(text: str) -> list[str]:
    out = []
    for chunk in re.split(r"\n\s*\n", text):
        t = " ".join(ln.strip() for ln in chunk.strip().splitlines() if ln.strip())
        t = re.sub(r"\\label\{[^{}]*\}", "", t).strip()
        if not t:
            continue
        if t.startswith("\\input{") or t.startswith("\\begin{figure}") or t.startswith("\\includegraphics"):
            continue
        probe = re.sub(r"\\[A-Za-z]+\*?(\[[^\]]*\])?(\{[^{}]*\})*", "", t)
        if not probe.strip("{} \t"):
            continue  # command-only lines such as {\footnotesize \setlength{...}} or a stray brace
        out.append(t)
    return out


def tex_items(raw: str, *, tables: str = "lines") -> list[tuple]:
    """Split a LaTeX block into ('p'|'li'|'table'|'eq', payload) items in order."""
    raw = re.sub(r"(?<!\\)%.*", "", raw)
    items: list[tuple] = []
    # figures are dropped; tables and \input tables become 'table' items
    raw = re.sub(r"\\begin\{figure\}.*?\\end\{figure\}", "\n\n", raw, flags=re.S)
    raw = re.sub(r"\\begin\{algorithm\}.*?\\end\{algorithm\}", "\n\n", raw, flags=re.S)
    raw = re.sub(r"\\begin\{verbatim\}(.*?)\\end\{verbatim\}",
                 lambda mm: "\n\n" + "\n\n".join("\\texttt{" + ln.replace("{", "\\{").replace("}", "\\}").replace("_", "\\_") + "}"
                                                 for ln in mm.group(1).splitlines() if ln.strip()) + "\n\n",
                 raw, flags=re.S)
    pattern = re.compile(
        r"(\\begin\{table\}.*?\\end\{table\})|(\\input\{(results/tables/[^{}]+)\})|"
        r"(\\begin\{(itemize|enumerate|description)\}(.*?)\\end\{\5\})|"
        r"(\\begin\{(?:equation|align)\*?\}(.*?)\\end\{(?:equation|align)\*?\})|(\\begin\{longtable\}.*?\\end\{longtable\})|"
        r"(\\begin\{tabular\}.*?\\end\{tabular\})",
        re.S,
    )
    pos = 0
    for m in pattern.finditer(raw):
        items += [("p", t) for t in split_paras(raw[pos:m.start()])]
        if m.group(1) or m.group(9) or m.group(10):
            if tables != "skip":
                items.append(("table", m.group(1) or m.group(9) or m.group(10)))
        elif m.group(2):
            if tables != "skip":
                items.append(("table", (EN / (m.group(3) if m.group(3).endswith(".tex") else m.group(3) + ".tex")).read_text(encoding="utf-8")))
        elif m.group(4):
            body = m.group(6)
            for it in re.split(r"\\item\b", body)[1:]:
                it = it.strip()
                lab = None
                mm = re.match(r"\[((?:[^\[\]]|\[[^\[\]]*\])*)\]\s*", it)
                if mm:
                    lab = mm.group(1)
                    it = it[mm.end():]
                # equations inside items -> inline text
                it = re.sub(r"\\begin\{equation\*?\}(.*?)\\end\{equation\*?\}", lambda e: " " + math_to_text(re.sub(r"\\label\{[^{}]*\}", "", e.group(1))) + " ", it, flags=re.S)
                it = " ".join(ln.strip() for ln in it.splitlines() if ln.strip())
                text = (lab.strip() + " " if lab else "") + it
                items.append(("li", text))
        elif m.group(7):
            body = re.sub(r"\\label\{[^{}]*\}", "", m.group(8))
            lines = [math_to_text(ln) for ln in body.split("\\\\") if ln.strip()]
            items.append(("eq", "; ".join(ln for ln in lines if ln)))
        pos = m.end()
    items += [("p", t) for t in split_paras(raw[pos:])]
    return items


def table_lines(latex: str) -> tuple[str, list[list[str]]]:
    """Return (caption, rows) of a tabular/longtable; rows include the header row."""
    cap = ""
    m = re.search(r"\\caption(?:\[[^\]]*\])?\{((?:[^{}]|\{(?:[^{}]|\{[^{}]*\})*\})*)\}", latex, flags=re.S)
    if m:
        cap = delatex(m.group(1))
    env = "longtable" if "\\begin{longtable}" in latex else "tabular"
    body = re.search(r"\\begin\{" + env + r"\}\{(?:[^{}]|\{[^{}]*\})*\}(.*?)\\end\{" + env + r"\}", latex, flags=re.S)
    rows: list[list[str]] = []
    if body:
        b = body.group(1)
        b = re.sub(r"\\caption(?:\[[^\]]*\])?\{(?:[^{}]|\{(?:[^{}]|\{[^{}]*\})*\})*\}\s*(\\label\{[^{}]*\})?\s*\\\\", "", b, flags=re.S)
        b = re.sub(r"\\multicolumn\{\d+\}\{[^{}]*\}\{[^{}]*(?:[Cc]ontinued|\\thetable)[^{}]*\}\s*\\\\", "", b)
        b = re.sub(r"\\(?:endfirsthead|endhead|endfoot|endlastfoot|midrule|hline|toprule|bottomrule|addlinespace)\b(?:\[[^\]]*\])?", "", b)
        b = re.sub(r"\\(?:cmidrule|cline)(?:\([^)]*\))?\{[^{}]*\}", "", b)
        b = re.sub(r"\\label\{[^{}]*\}", "", b)
        b = re.sub(r"\\multicolumn\{\d+\}\{[^{}]*\}\{((?:[^{}]|\{[^{}]*\})*)\}", r"\1", b)
        seen = set()
        for line in b.split("\\\\"):
            line = " ".join(ln.strip() for ln in line.splitlines() if ln.strip())
            if not line.strip():
                continue
            cells = [delatex(c) for c in re.split(r"(?<!\\)&", line)]
            if not any(c.strip() for c in cells):
                continue
            key = tuple(cells)
            if key in seen:  # longtable repeats the header in \endhead
                continue
            seen.add(key)
            rows.append(cells)
    return cap, rows


# --------------------------------------------------------------------------- run building
MARK_RE = re.compile(r"(\[\[[\d,]+\]\]|\{\{i:.*?\}\})")


def clean_rpr(rpr, *, drop=("b", "bCs", "i", "iCs", "vertAlign", "u", "strike", "highlight", "rStyle", "spacing", "w")):
    if rpr is None:
        return etree.Element(qn("w:rPr"))
    r = deepcopy(rpr)
    for child in list(r):
        if localname(child) in drop:
            r.remove(child)
    return r


def make_run(text: str, rpr, *, sup=False, italic=False):
    r = etree.Element(qn("w:r"))
    rp = clean_rpr(rpr)
    if italic:
        etree.SubElement(rp, qn("w:i"))
        etree.SubElement(rp, qn("w:iCs"))
    if sup:
        va = etree.SubElement(rp, qn("w:vertAlign"))
        va.set(qn("w:val"), "superscript")
    if len(rp):
        r.append(rp)
    t = etree.SubElement(r, qn("w:t"))
    t.text = text
    t.set(qn("xml:space"), "preserve")
    return r


NEW_CITE_RUNS: set = set()


def build_runs(text: str, rpr) -> list:
    runs = []
    for tok in MARK_RE.split(text):
        if not tok:
            continue
        if tok.startswith("[["):
            nums = [n for n in tok[2:-2].split(",") if n]
            r = make_run(",".join(f"[{n}]" for n in nums), rpr, sup=True)
            NEW_CITE_RUNS.add(id(r))
            runs.append(r)
        elif tok.startswith("{{i:"):
            runs.append(make_run(tok[4:-2], rpr, italic=True))
        else:
            runs.append(make_run(tok, rpr))
    return runs


def para_text(p) -> str:
    return "".join(t.text or "" for t in p.iter(qn("w:t")))


def norm(s: str) -> str:
    s = s.replace("\u00a0", " ").replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    s = s.replace("–", "-").replace("—", "-").replace("\u037e", ";").replace("\u2011", "-").replace("\u2010", "-")
    return re.sub(r"\s+", " ", s).strip().lower()


def pstyle(p) -> str:
    ppr = p.find(qn("w:pPr"))
    if ppr is None:
        return ""
    ps = ppr.find(qn("w:pStyle"))
    return ps.get(qn("w:val")) if ps is not None else ""


MARKER_TAGS = {"commentRangeStart", "commentRangeEnd", "commentReference", "bookmarkStart", "bookmarkEnd",
               "sectPr", "footnoteReference", "endnoteReference", "drawing", "pict", "object"}


def has_markers(el) -> bool:
    return any(localname(e) in MARKER_TAGS for e in el.iter())


# --------------------------------------------------------------------------- document
class Doc:
    def __init__(self, path: Path):
        self.path = path
        self.zin = zipfile.ZipFile(path)
        self.parts = {n: self.zin.read(n) for n in self.zin.namelist()}
        self.zin.close()
        self.doc = etree.fromstring(self.parts["word/document.xml"])
        self.body = self.doc.find(qn("w:body"))
        self.comments = etree.fromstring(self.parts["word/comments.xml"])
        self.comments_ex = etree.fromstring(self.parts["word/commentsExtended.xml"])
        self.comments_ids = etree.fromstring(self.parts["word/commentsIds.xml"])
        self.comments_cex = etree.fromstring(self.parts["word/commentsExtensible.xml"])
        self.people = etree.fromstring(self.parts["word/people.xml"])
        self.paras = list(self.body.iter(qn("w:p")))
        self.next_cid = max(int(c.get(qn("w:id"))) for c in self.comments.iter(qn("w:comment"))) + 1
        self.used_para_ids = {e.get(qn("w14:paraId")) for e in self.doc.iter() if e.get(qn("w14:paraId"))}
        self.used_para_ids |= {e.get(qn("w14:paraId")) for e in self.comments.iter() if e.get(qn("w14:paraId"))}
        self.new_comments: list[tuple[int, str]] = []
        self.templates: dict = {}
        self.edit_count = 0
        # heading bookkeeping for the static table of contents
        self.renames: list[tuple[str, str]] = []          # (norm old heading, new heading)
        self.deleted_headings: list[str] = []             # norm old heading
        self.inserted_headings: list[tuple[str, str, str]] = []  # (norm previous heading, new heading, kind)

    # -- lookup ---------------------------------------------------------------
    def P(self, idx: int, prefix: str | None = None, *, style: str | None = None):
        """1-based paragraph index as in the dump; checks the text prefix (±3 tolerance)."""
        cands = [idx] + [idx + k for k in (1, -1, 2, -2, 3, -3)]
        for i in cands:
            if not (1 <= i <= len(self.paras)):
                continue
            p = self.paras[i - 1]
            ok = True
            if prefix is not None:
                nt, npf = norm(para_text(p)), norm(prefix)[:40]
                pos = nt.find(npf)
                if pos < 0 or pos > 12:  # allow a short leading artefact such as a footnote/page number
                    ok = False
            if style is not None and pstyle(p) != style:
                ok = False
            if ok:
                if i != idx:
                    log(f"  [note] paragraph {idx} matched at {i}: {prefix!r}")
                return p
        raise LookupError(f"paragraph {idx} with prefix {prefix!r} not found (got {para_text(self.paras[idx-1])[:80]!r})")

    def heading(self, text: str, *, level: str | None = None, after: int = 0):
        n = norm(text)
        for i, p in enumerate(self.paras, 1):
            if i <= after:
                continue
            st = pstyle(p)
            if st.startswith("Heading") and (level is None or st == level) and norm(para_text(p)) == n:
                return p
        raise LookupError(f"heading {text!r} not found")

    def idx(self, p) -> int:
        return self.paras.index(p) + 1

    def body_level(self, el):
        while el is not None and el.getparent() is not self.body:
            el = el.getparent()
        return el

    def section_targets(self, heading_p, *, stop_at=None):
        """Non-empty body-level paragraphs after heading_p until the next heading (any level) or stop_at."""
        out = []
        el = heading_p.getnext()
        while el is not None:
            if el is stop_at:
                break
            if localname(el) == "p":
                if pstyle(el).startswith("Heading"):
                    break
                if para_text(el).strip():
                    out.append(el)
            el = el.getnext()
        return out

    def find_after(self, prefix: str, after_idx: int, *, style: str | None = None):
        n = norm(prefix)
        for i, p in enumerate(self.paras, 1):
            if i <= after_idx:
                continue
            if style is not None and pstyle(p) != style:
                continue
            if norm(para_text(p)).startswith(n):
                return p
        raise LookupError(f"no paragraph starting with {prefix!r} after {after_idx}")

    def range_targets(self, a: int, b: int):
        out = []
        for i in range(a, b + 1):
            p = self.paras[i - 1]
            if p.getparent() is not self.body:
                continue
            if pstyle(p).startswith("Heading"):
                continue
            if para_text(p).strip():
                out.append(p)
        return out

    def section_elements(self, heading_p):
        """All body-level elements (paragraphs and tables) from heading_p up to the next heading of same/higher level."""
        lvl = pstyle(heading_p)
        out = []
        el = heading_p.getnext()
        while el is not None:
            if localname(el) == "p" and pstyle(el).startswith("Heading") and pstyle(el) <= lvl:
                break
            out.append(el)
            el = el.getnext()
        return out

    # -- templates ------------------------------------------------------------
    def set_templates(self, **kw):
        for k, p in kw.items():
            self.templates[k] = p

    def template_rpr(self, p):
        for r in p.iter(qn("w:r")):
            if r.find(qn("w:t")) is not None and r.find(qn("w:commentReference")) is None:
                return r.find(qn("w:rPr"))
        return None

    def kind_of(self, p) -> str:
        st = pstyle(p)
        if st.startswith("Heading"):
            return "h"
        ppr = p.find(qn("w:pPr"))
        if st == "ListParagraph" and ppr is not None and ppr.find(qn("w:numPr")) is not None:
            return "li"
        if st in ("BodyText", "ListParagraph"):
            return "p"
        if st == "TableParagraph":
            return "cell"
        return "tline"

    # -- paragraph editing ----------------------------------------------------
    def set_para(self, p, text: str, *, kind: str | None = None, rpr=None):
        ppr = p.find(qn("w:pPr"))
        if pstyle(p).startswith("Heading") and p.getparent() is self.body:
            old = para_text(p).strip()
            if old and text.strip() and norm(old) != norm(text):
                self.renames.append((norm(old), text.strip()))
            elif old and not text.strip():
                self.deleted_headings.append(norm(old))
        if kind in ("p", "li", "tline") and self.kind_of(p) in ("p", "li", "tline") and self.kind_of(p) != kind:
            tmpl_ppr = self.templates[kind].find(qn("w:pPr"))
            new_ppr = deepcopy(tmpl_ppr) if tmpl_ppr is not None else etree.Element(qn("w:pPr"))
            if ppr is not None:
                sect = ppr.find(qn("w:sectPr"))
                if sect is not None:
                    new_ppr.append(sect)
                p.remove(ppr)
            p.insert(0, new_ppr)
            ppr = new_ppr
        tmpl = rpr if rpr is not None else self.template_rpr(p)
        if tmpl is None and kind in self.templates:
            tmpl = self.template_rpr(self.templates[kind])
        starts, ends, refs = [], [], []
        for el in list(p.iter()):
            if el is p:
                continue
            ln = localname(el)
            if ln in ("commentRangeStart", "bookmarkStart"):
                starts.append(el)
            elif ln in ("commentRangeEnd", "bookmarkEnd"):
                ends.append(el)
            elif ln in ("commentReference", "footnoteReference"):
                run = el.getparent()
                refs.append(run if localname(run) == "r" else el)
        for el in starts + ends + refs:
            par = el.getparent()
            if par is not None:
                par.remove(el)
        for el in list(p):
            if el is ppr:
                continue
            p.remove(el)
        for el in starts:
            p.append(el)
        for r in build_runs(text, tmpl):
            p.append(r)
        for el in ends:
            p.append(el)
        for el in refs:
            p.append(el)
        self.edit_count += 1
        return p

    def new_para(self, text: str, kind: str = "p", *, like=None):
        tmpl = like if like is not None else self.templates[kind]
        p = etree.Element(qn("w:p"))
        tppr = tmpl.find(qn("w:pPr"))
        if tppr is not None:
            ppr = deepcopy(tppr)
            for bad in ppr.findall(qn("w:sectPr")):
                ppr.remove(bad)
            p.append(ppr)
        for r in build_runs(text, self.template_rpr(tmpl)):
            p.append(r)
        self.edit_count += 1
        return p

    def insert_after(self, anchor, text: str, kind: str = "p", *, like=None):
        p = self.new_para(text, kind, like=like)
        anchor.addnext(p)
        if kind in ("h2", "h3"):
            # remember up to four preceding non-empty headings so the TOC pass can fall back
            # when the nearest one is not listed in the TOC (e.g. a Heading3 in a chapter listed to level 2)
            prevs: list[tuple[str, str]] = []  # (norm heading text, style) nearest first, ending at the enclosing Heading2/1
            prev = anchor
            while prev is not None:
                if localname(prev) == "p" and pstyle(prev).startswith("Heading") and para_text(prev).strip():
                    prevs.append((norm(para_text(prev)), pstyle(prev)))
                    if pstyle(prev) in ("Heading1", "Heading2"):
                        break
                prev = prev.getprevious()
            self.inserted_headings.append((prevs, text, kind))
        return p

    def replace_table_after(self, cap_p, rows: list[list[str]]):
        """Replace the first table following cap_p (skipping empty paragraphs) with a new table built from rows."""
        el = cap_p.getnext()
        while el is not None and localname(el) == "p" and not para_text(el).strip():
            el = el.getnext()
        assert el is not None and localname(el) == "tbl", f"no table after {para_text(cap_p)[:60]!r}"
        new = self.insert_table_after(cap_p, rows)
        if has_markers(el):
            for p in el.iter(qn("w:p")):
                self.set_para(p, "")
        else:
            self.body.remove(el)
        self.edit_count += 1
        return new

    def delete_or_clear(self, el):
        if localname(el) == "p":
            parent = el.getparent()
            removable_parent = parent is self.body or (localname(parent) == "sdtContent" and len(parent) > 1)
            if not removable_parent or has_markers(el):
                if pstyle(el).startswith("Heading") and el.getparent() is self.body:
                    self.set_para(el, "")  # records the heading as deleted
                    # demote the emptied heading to a body paragraph so no blank heading remains
                    ppr = el.find(qn("w:pPr"))
                    tppr = self.templates["p"].find(qn("w:pPr"))
                    new_ppr = deepcopy(tppr) if tppr is not None else etree.Element(qn("w:pPr"))
                    if ppr is not None:
                        sect = ppr.find(qn("w:sectPr"))
                        if sect is not None:
                            new_ppr.append(sect)
                        el.remove(ppr)
                    el.insert(0, new_ppr)
                else:
                    self.set_para(el, "")
                return "cleared"
            if pstyle(el).startswith("Heading"):
                self.deleted_headings.append(norm(para_text(el)))
            parent.remove(el)
            self.edit_count += 1
            return "deleted"
        if localname(el) == "tbl":
            if has_markers(el):
                for p in el.iter(qn("w:p")):
                    self.set_para(p, "")
                return "cleared"
            self.body.remove(el)
            self.edit_count += 1
            return "deleted"
        return "kept"

    def delete_section(self, heading_p):
        els = self.section_elements(heading_p)
        for el in els:
            self.delete_or_clear(el)
        self.delete_or_clear(heading_p)

    def fill(self, targets: list, items: list[tuple], *, anchor, note: str | None = None, table_titles: list[str] | None = None):
        """Write items into targets in order; insert extras after the last written element; clear leftovers."""
        ti = 0
        first_el, last_el = None, None
        prev_written = anchor
        titles = list(table_titles or [])
        for kind, payload in items:
            if kind == "table":
                cap, rows = table_lines(payload)
                pos = prev_written
                if cap:
                    title = titles.pop(0) if titles else ""
                    pos = self.insert_after(pos, (title + ": " if title else "") + cap, "p")
                    if first_el is None:
                        first_el = pos
                pos = self.insert_table_after(pos, rows)
                pos = self.insert_after(pos, "", "p")
                prev_written = pos
                last_el = pos
                continue
            text = delatex(payload) if kind != "eq" else payload
            k = "p" if kind in ("p", "eq") else kind
            if ti < len(targets):
                p = targets[ti]
                ti += 1
                self.set_para(p, text, kind=k)
                # keep document order: anything inserted meanwhile sits before p already
                prev_written = p
            else:
                prev_written = self.insert_after(prev_written, text, k)
            if first_el is None:
                first_el = prev_written
            last_el = prev_written
        for p in targets[ti:]:
            res = self.delete_or_clear(p)
            if res == "cleared":
                last_el = p
        if note and first_el is not None:
            self.comment_span(first_el, last_el if last_el is not None else first_el, note)
        return first_el, last_el

    def fill_section(self, heading_p, items, *, note=None, stop_at=None, table_titles=None):
        targets = self.section_targets(heading_p, stop_at=stop_at)
        return self.fill(targets, items, anchor=heading_p, note=note, table_titles=table_titles)

    # -- tables ---------------------------------------------------------------
    def insert_table_after(self, anchor, rows: list[list[str]]):
        tmpl = self.templates["tbl"]
        tbl = deepcopy(tmpl)
        for e in list(tbl.iter()):
            if localname(e) in ("bookmarkStart", "bookmarkEnd", "commentRangeStart", "commentRangeEnd"):
                e.getparent().remove(e)
            elif localname(e) == "commentReference":
                r = e.getparent()
                r.getparent().remove(r)
        trs = tbl.findall(qn("w:tr"))
        head_tr, data_tr = trs[0], trs[1]
        for tr in trs:
            tbl.remove(tr)
        ncol = max(len(r) for r in rows)
        grid = tbl.find(qn("w:tblGrid"))
        total = sum(int(g.get(qn("w:w"))) for g in grid.findall(qn("w:gridCol")))
        total = max(total, 9000)
        for g in list(grid):
            grid.remove(g)
        for _ in range(ncol):
            g = etree.SubElement(grid, qn("w:gridCol"))
            g.set(qn("w:w"), str(total // ncol))
        tblpr = tbl.find(qn("w:tblPr"))
        if tblpr is not None:
            lay = tblpr.find(qn("w:tblLayout"))
            if lay is None:
                lay = etree.SubElement(tblpr, qn("w:tblLayout"))
            lay.set(qn("w:type"), "fixed")

        def build_row(tr_tmpl, cells, bold=False):
            tr = deepcopy(tr_tmpl)
            tcs = tr.findall(qn("w:tc"))
            while len(tcs) < ncol:
                tcs.append(deepcopy(tcs[-1]))
                tr.append(tcs[-1])
            for extra in tcs[ncol:]:
                tr.remove(extra)
            tcs = tcs[:ncol]
            for i, tc in enumerate(tcs):
                tcpr = tc.find(qn("w:tcPr"))
                if tcpr is not None:
                    w = tcpr.find(qn("w:tcW"))
                    if w is not None:
                        w.set(qn("w:w"), str(total // ncol))
                        w.set(qn("w:type"), "dxa")
                    for gs in tcpr.findall(qn("w:gridSpan")):
                        tcpr.remove(gs)
                ps = tc.findall(qn("w:p"))
                for extra in ps[1:]:
                    tc.remove(extra)
                p = ps[0]
                ppr = p.find(qn("w:pPr"))
                if ppr is not None:
                    for ind in ppr.findall(qn("w:ind")):
                        ppr.remove(ind)
                    jc = ppr.find(qn("w:jc"))
                    if jc is not None:
                        jc.set(qn("w:val"), "left")
                self.set_para(p, cells[i] if i < len(cells) else "")
                if bold:
                    for r in p.findall(qn("w:r")):
                        rp = r.find(qn("w:rPr"))
                        if rp is None:
                            rp = etree.Element(qn("w:rPr"))
                            r.insert(0, rp)
                        rp.insert(0, etree.Element(qn("w:b")))
            return tr

        tbl.append(build_row(head_tr, rows[0], bold=True))
        for cells in rows[1:]:
            tbl.append(build_row(data_tr, cells))
        anchor.addnext(tbl)
        return tbl

    def set_cells(self, first_idx: int, values: list[str], expect: list[str] | None = None):
        """Set consecutive table-cell paragraphs starting at 1-based index first_idx."""
        for k, v in enumerate(values):
            p = self.paras[first_idx - 1 + k]
            assert pstyle(p) == "TableParagraph", f"paragraph {first_idx + k} is not a table cell"
            if expect and expect[k] is not None:
                assert norm(para_text(p)) == norm(expect[k]), f"cell {first_idx + k}: expected {expect[k]!r} got {para_text(p)!r}"
            self.set_para(p, v)

    def remove_row_of(self, idx: int):
        p = self.paras[idx - 1]
        tr = p.getparent().getparent()
        assert localname(tr) == "tr"
        if has_markers(tr):
            for q in tr.iter(qn("w:p")):
                self.set_para(q, "")
        else:
            tr.getparent().remove(tr)
        self.edit_count += 1

    # -- comments -------------------------------------------------------------
    def _para_id(self) -> str:
        while True:
            v = "%08X" % random.randint(0x10000000, 0x7FFFFFFF)
            if v not in self.used_para_ids:
                self.used_para_ids.add(v)
                return v

    def comment_span(self, first_el, last_el, text: str) -> int:
        cid = self.next_cid
        self.next_cid += 1
        if localname(first_el) == "tbl":
            first_el = next(first_el.iter(qn("w:p")))
        if localname(last_el) == "tbl":
            last_el = list(last_el.iter(qn("w:p")))[-1]
        start = etree.Element(qn("w:commentRangeStart"))
        start.set(qn("w:id"), str(cid))
        ppr = first_el.find(qn("w:pPr"))
        first_el.insert(1 if ppr is not None else 0, start)
        end = etree.Element(qn("w:commentRangeEnd"))
        end.set(qn("w:id"), str(cid))
        last_el.append(end)
        r = etree.SubElement(last_el, qn("w:r"))
        rp = etree.SubElement(r, qn("w:rPr"))
        rs = etree.SubElement(rp, qn("w:rStyle"))
        rs.set(qn("w:val"), "CommentReference")
        cr = etree.SubElement(r, qn("w:commentReference"))
        cr.set(qn("w:id"), str(cid))
        # comments.xml
        c = etree.SubElement(self.comments, qn("w:comment"))
        c.set(qn("w:id"), str(cid))
        c.set(qn("w:author"), AUTHOR)
        c.set(qn("w:date"), STAMP)
        c.set(qn("w:initials"), INITIALS)
        pid = self._para_id()
        p = etree.SubElement(c, qn("w:p"))
        p.set(qn("w14:paraId"), pid)
        p.set(qn("w14:textId"), "77777777")
        pp = etree.SubElement(p, qn("w:pPr"))
        ps = etree.SubElement(pp, qn("w:pStyle"))
        ps.set(qn("w:val"), "CommentText")
        r0 = etree.SubElement(p, qn("w:r"))
        rp0 = etree.SubElement(r0, qn("w:rPr"))
        rs0 = etree.SubElement(rp0, qn("w:rStyle"))
        rs0.set(qn("w:val"), "CommentReference")
        etree.SubElement(r0, qn("w:annotationRef"))
        r1 = etree.SubElement(p, qn("w:r"))
        t1 = etree.SubElement(r1, qn("w:t"))
        t1.set(qn("xml:space"), "preserve")
        t1.text = text
        ex = etree.SubElement(self.comments_ex, qn("w15:commentEx"))
        ex.set(qn("w15:paraId"), pid)
        ex.set(qn("w15:done"), "0")
        durable = "%08X" % random.randint(0x10000000, 0x7FFFFFFF)
        cidel = etree.SubElement(self.comments_ids, qn("w16cid:commentId"))
        cidel.set(qn("w16cid:paraId"), pid)
        cidel.set(qn("w16cid:durableId"), durable)
        cex = etree.SubElement(self.comments_cex, qn("w16cex:commentExtensible"))
        cex.set(qn("w16cex:durableId"), durable)
        cex.set(qn("w16cex:dateUtc"), STAMP)
        self.new_comments.append((cid, text))
        return cid

    def comment_para(self, p, text: str) -> int:
        return self.comment_span(p, p, text)

    def ensure_person(self):
        for person in self.people.iter(qn("w15:person")):
            if person.get(qn("w15:author")) == AUTHOR:
                return
        person = etree.SubElement(self.people, qn("w15:person"))
        person.set(qn("w15:author"), AUTHOR)

    # -- save -----------------------------------------------------------------
    def save(self, out: Path):
        self.ensure_person()
        upd = {
            "word/document.xml": etree.tostring(self.doc, xml_declaration=True, encoding="UTF-8", standalone=True),
            "word/comments.xml": etree.tostring(self.comments, xml_declaration=True, encoding="UTF-8", standalone=True),
            "word/commentsExtended.xml": etree.tostring(self.comments_ex, xml_declaration=True, encoding="UTF-8", standalone=True),
            "word/commentsIds.xml": etree.tostring(self.comments_ids, xml_declaration=True, encoding="UTF-8", standalone=True),
            "word/commentsExtensible.xml": etree.tostring(self.comments_cex, xml_declaration=True, encoding="UTF-8", standalone=True),
            "word/people.xml": etree.tostring(self.people, xml_declaration=True, encoding="UTF-8", standalone=True),
        }
        tmp = out.with_name(out.name + ".__tmp")
        with zipfile.ZipFile(self.path) as zin, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
            for info in zin.infolist():
                data = upd.get(info.filename, self.parts[info.filename])
                zout.writestr(info, data)
        shutil.move(str(tmp), str(out))


# --------------------------------------------------------------------------- edits
def split_targets_at(targets: list, pivot) -> tuple[list, list]:
    """Split a target list into the elements before and after `pivot` (pivot itself excluded)."""
    before, after, seen = [], [], False
    for p in targets:
        if p is pivot:
            seen = True
            continue
        (after if seen else before).append(p)
    return before, after


def split_at_table(items: list[tuple]) -> tuple[list[tuple], list[tuple]]:
    """Items before the first table item, and the non-table items after it."""
    for k, (kind, _) in enumerate(items):
        if kind == "table":
            return items[:k], [it for it in items[k + 1:] if it[0] != "table"]
    return items, []


def apply_edits(d: Doc, N: dict) -> None:
    P = d.P
    # templates
    d.set_templates(
        p=P(41, style="BodyText"),
        li=P(501, style="ListParagraph"),
        tline=P(1630),
        h2=P(443, "Research questions", style="Heading2"),
        h3=P(730, "Interpretation bands", style="Heading3"),
        tbl=d.body_level(P(1591, "Method", style="TableParagraph")),
    )
    ab = tex_source("abstract")

    def sec_fill(idx, prefix, style, key, label, note, *, table_titles=None, drop_tables=False):
        """Rename a DOCX heading to its LaTeX title if needed and fill the section (up to the next heading) from the LaTeX."""
        h = P(idx, prefix, style=style)
        m = re.search(r"\\dissertationSub(?:sub)?heading\[" + re.escape(label) + r"\]\{((?:[^{}]|\{[^{}]*\})*)\}", tex_source(key))
        title = delatex(re.sub(r"\\texorpdfstring\{([^{}]*)\}\{[^{}]*\}", r"\1", m.group(1)))
        if norm(title) != norm(para_text(h)):
            d.set_para(h, title)
        if drop_tables:
            for el in d.section_elements(h):
                if localname(el) == "tbl":
                    d.delete_or_clear(el)
        d.fill_section(h, tex_items(tex_section(key, label)), note=note, table_titles=table_titles)
        return h

    # ------------------------------------------------------------- Abstract (comments 1, 3, 6, 2, 7)
    abs_body = re.search(r"\\label\{ch:abstract\}\n(.*)", ab, flags=re.S).group(1)
    abs_paras = split_paras(abs_body)
    kw = abs_paras[-1]
    abs_items = [("p", t) for t in abs_paras[:-1]]
    abs_targets = [P(40, style="BodyText"), P(41, style="BodyText"), P(42, style="BodyText"),
                   P(43, style="BodyText"), P(44, style="BodyText"), P(45, "During empirical work")]
    d.fill(abs_targets, abs_items, anchor=P(38, "Abstract", style="Heading1"),
           note=f"{AUTHOR} {TODAY}: Abstract rewritten to state background, problem, design, numerical results with intervals, "
                f"benchmark against AWP and significance (comments 1, 3, 6, 2, 7). Citations and bold removed; AWP attributed to "
                f"Do, Do and Nguyen (2023, IEEE RIVF). Source: en/01-Intro/02-Abstract.tex.")
    d.set_para(P(47, "Keywords"), delatex(kw))
    d.comment_para(P(47, "Keywords"), f"{AUTHOR} {TODAY}: Keywords updated (temporal holdout, Kendall's tau added; GF-PR removed).")

    # ------------------------------------------------------------- Abbreviations (comment 14)
    for i, pre in ((309, "GF-PR"), (314, "SRQ")):
        p = P(i, pre)
        d.set_para(p, "")
    d.comment_span(P(309), P(314), f"{AUTHOR} {TODAY}: GF-PR and SRQ entries removed from the abbreviation list; "
                                    f"GF-PR/SRQ1/SC1 are withdrawn from the main narrative (comment 14).")

    # ------------------------------------------------------------- Chapter 1
    h_intro = P(356, "Introduction and Research Problem", style="Heading1")
    d.fill_section(h_intro, tex_items(tex_preamble("ch1")),
                   note=f"{AUTHOR} {TODAY}: Chapter 1 opening rewritten; citation clusters split so each sentence cites its own source "
                        f"(comment 20); AWP attributed to Do, Do and Nguyen [3] (comment 2). Source: en/Chapter-01/index.tex.")
    d.fill_section(P(362, "Background", style="Heading2"), tex_items(tex_section("ch1", "sec:background")),
                   note=f"{AUTHOR} {TODAY}: Background paragraphs aligned with the revised LaTeX: one source per claim (comment 20); "
                        f"Do and Do [4] (PageRank/HodgeRank) and Do, Do and Nguyen [3] (AWP) cited separately (comment 2).")
    d.fill_section(P(375, "Motivation", style="Heading2"), tex_items(tex_section("ch1", "sec:motivation")),
                   note=f"{AUTHOR} {TODAY}: Motivation rewritten; the speedup is framed as an expected consequence of graph sparsity "
                        f"with an identical solver, not as an algorithmic contribution, and headline numbers are removed (comments 62, 82). "
                        f"Expanded pool N = {ic(N['pool_N'])}.")
    rp_items = tex_items(tex_section("ch1", "sec:research-problem"), tables="skip")
    rp_before = rp_items[:3]
    rp_after = rp_items[3:]
    d.fill(d.range_targets(391, 397), rp_before, anchor=P(389, "Research problem", style="Heading2"),
           note=f"{AUTHOR} {TODAY}: Research problem restated for the EndorseRank-vs-AWP comparison with the temporal holdout; "
                f"SRQ1 removed (comments 14, 74).")
    d.set_para(P(406, "Primary baseline"), delatex(r"Primary baseline: IEEE RIVF 2023 transfer-graph method \cend{3}; Do and Do\cend{4} is the earlier PageRank/HodgeRank study on Ethereum transfers"))
    d.comment_para(P(406), f"{AUTHOR} {TODAY}: Table 1.1 baseline row re-attributed to Do, Do and Nguyen (2023) [3]; Do and Do [4] cited separately (comment 2).")
    d.fill(d.range_targets(407, 427), rp_after, anchor=P(406),
           note=f"{AUTHOR} {TODAY}: Definitions aligned with the revised LaTeX (AWP definition cites [3]; one source per definition).")
    # Temporal holdout replaces the GF-PR extension
    h_ext = P(429, "Supplementary extension (GF-PR)", style="Heading2")
    d.set_para(h_ext, "Temporal holdout")
    th_items = tex_items(tex_section("ch1", "sec:supplementary-extension"), tables="skip")
    d.fill(d.range_targets(430, 431), th_items, anchor=h_ext)
    for el in [P(432, "Table 1.2")] + [d.paras[i - 1] for i in range(433, 438)]:
        if el.getparent() is d.body:
            d.delete_or_clear(el)
    d.comment_span(h_ext, P(431), f"{AUTHOR} {TODAY}: Section 'Supplementary extension (GF-PR)' and Table 1.2 replaced by 'Temporal holdout' "
                                  f"(scores frozen 28 Feb 2026; labels = new owner-spender approvals Mar-May 2026; spender cohort n = 1,335) (comments 14, 74).")
    # Table 1.3 blob rows
    d.set_para(P(464, "§4.6; inter-method"), "§4.6; inter-method τ with 95% CI")
    d.set_para(P(466, "Tables 4.7"), "Tables 4.7–4.9, 4.14; Claims C2–C3")
    d.set_para(P(470, "RQ4"), "RQ4 Do t1 scores predict t2 new approvals beyond same-window allowance?")
    d.set_para(P(471, "SRQ1"), "")
    d.set_para(P(473, "C2"), "C2 Intended-construct checks: allowance for ER, transfer for AWP")
    d.set_para(P(477, "SC1"), "")
    d.set_para(P(480, "§4.7; Claim SC1"), "§4.7; Table 4.13 | Table 4.2")
    d.set_para(P(481, "Tables 4.8"), "Tables 4.8–4.9")
    d.comment_span(P(458, "Table 1.3"), P(487), f"{AUTHOR} {TODAY}: Table 1.3 updated: RQ4 re-posed as the temporal holdout, SRQ1/SC1 rows removed, "
                                                f"C2 restated as intended-construct checks, evidence columns point to the CI and difference tables (comments 14, 74, 237).")
    # Research objectives (new section, comment 72) before Research questions
    h_rq = P(443, "Research questions", style="Heading2")
    h_obj = d.insert_after(h_rq.getprevious(), "Research objectives", "h2")
    cur = h_obj
    for kind, payload in tex_items(tex_section("ch1", "sec:research-objectives")):
        cur = d.insert_after(cur, delatex(payload), "p" if kind == "p" else "li")
    cur = d.insert_after(cur, "", "p")
    d.comment_span(h_obj, cur, f"{AUTHOR} {TODAY}: New section 'Research objectives' (O1-O4 with measurement and criterion, mapped to RQ1-RQ4); "
                               f"Chapter 5 judges each objective (comment 72; UNISA guideline Table 2).")
    # RQs
    rq_items = tex_items(tex_section("ch1", "sec:research-questions"))
    d.fill(d.range_targets(445, 446), rq_items[:2], anchor=h_rq)
    d.fill(d.range_targets(489, 497), rq_items[2:], anchor=P(487))
    d.comment_span(P(445), P(495), f"{AUTHOR} {TODAY}: Hypotheses and RQ1-RQ4 aligned with the LaTeX; RQ4 re-posed as a temporal holdout and SRQ1 removed; "
                                    f"explanation states that same-window own-construct agreement is a construct-validity observation (comments 14, 72, 74).")
    # Literature / methodology summaries (new sections) before Contributions
    h_con = P(498, "Contributions", style="Heading2")
    h_ls = d.insert_after(h_con.getprevious(), "Summary of the literature review", "h2")
    cur = h_ls
    for kind, payload in tex_items(tex_section("ch1", "sec:literature-summary")):
        cur = d.insert_after(cur, delatex(payload), "p")
    cur = d.insert_after(cur, "", "p")
    h_ms = d.insert_after(cur, "Summary of the research methodology", "h2")
    cur = h_ms
    for kind, payload in tex_items(tex_section("ch1", "sec:methodology-summary")):
        cur = d.insert_after(cur, delatex(payload), "p")
    cur = d.insert_after(cur, "", "p")
    d.comment_span(h_ls, cur, f"{AUTHOR} {TODAY}: New sections 'Summary of the literature review' and 'Summary of the research methodology' "
                              f"(UNISA guideline Table 2, Chapter 1 structure; meeting 2026-09-09).")
    d.fill_section(h_con, tex_items(tex_section("ch1", "sec:contributions")),
                   note=f"{AUTHOR} {TODAY}: Contributions rewritten as three (latest-allowance edge construct; same-cohort comparison with bootstrap "
                        f"intervals and paired difference tests; temporal holdout). Efficiency (C1) demoted to an expected consequence of sparsity; "
                        f"the pipeline is no longer a contribution but is referenced with repository and commit; headline numbers removed "
                        f"(comments 77, 78, 81, 82, 62).")
    d.fill_section(P(511, "Scope", style="Heading2"), tex_items(tex_section("ch1", "sec:scope-limitations")),
                   note=f"{AUTHOR} {TODAY}: Scope updated (expanded pool N = {ic(N['pool_N'])}; spender holdout cohort; archived baselines).")
    d.fill_section(P(519, "Thesis organization"), tex_items(tex_section("ch1", "sec:roadmap")),
                   note=f"{AUTHOR} {TODAY}: Roadmap rewritten with chapter-linking paragraphs (meeting 2026-09-09).")

    # ------------------------------------------------------------- Chapter 2
    h_ch2 = d.heading("Literature Review and Theoretical Framework", level="Heading1")
    d.fill_section(h_ch2, tex_items(tex_preamble("ch2")),
                   note=f"{AUTHOR} {TODAY}: Chapter 2 opening rewritten as a link from Chapter 1 (meeting 2026-09-09).")
    h_gf = P(696, "Supplementary extension: outcome-native reference", style="Heading2")
    d.set_para(h_gf, "What this research does not claim")
    d.fill_section(h_gf, tex_items(tex_section("ch2", "sub:gf-pr")),
                   note=f"{AUTHOR} {TODAY}: GF-PR section replaced by a single methodological caveat stating why the outcome-native reference is circular "
                        f"and that GF-PR/SRQ1/SC1 and the trading-success families are withdrawn (comment 14).")
    rc_items = [t for k, t in tex_items(tex_section("ch2", "sec:rank-correlation-theory")) if k == "p"]
    d.set_para(P(702, "Reputation scores and validation proxies"), delatex(rc_items[0]))
    kend = [t for t in rc_items if t.startswith("where $C$")][0]
    d.set_para(P(728, "where C (D)"), delatex(kend))
    h_bands = P(730, "Interpretation bands", style="Heading3")
    d.set_para(P(732, "There is no universal cutoff"),
               "No absolute cutoff is used to label a coefficient as weak or strong. Values are compared relatively across methods on the same cohort; "
               "every reported coefficient carries a 95% percentile bootstrap interval and differences between coefficients are tested with paired-difference intervals (Chapter 3).")
    d.set_para(P(733, "0.35 substantively"), "")
    d.delete_or_clear(P(734, "relatively across methods"))
    d.delete_or_clear(h_bands)
    d.comment_span(P(702), P(733), f"{AUTHOR} {TODAY}: Interpretation bands deleted; coefficients are reported with 95% bootstrap intervals and compared with "
                                    f"paired-difference tests instead of thresholds (comments 128, 129). Rank-correlation paragraphs cite the AWP protocol [3] and Efron [34].")
    # literature summary table + research gap before Open problems
    h_open = P(899, "Open problems motivating this dissertation", style="Heading2")
    d.set_para(h_open, "Open problems motivating this research")
    h_lit = d.insert_after(h_open.getprevious(), "Summary of the reviewed literature", "h2")
    cur = h_lit
    lit_raw = tex_section("ch2", "sec:literature-summary-table")
    for kind, payload in tex_items(lit_raw):
        if kind == "table":
            cap, rows = table_lines(payload)
            cur = d.insert_after(cur, cap if cap.lower().startswith("table") else "Table 2.2: " + cap, "p")
            cur = d.insert_table_after(cur, rows)
            cur = d.insert_after(cur, "", "p")
        else:
            cur = d.insert_after(cur, delatex(payload), "p")
    cur = d.insert_after(cur, "", "p")
    h_gap = d.insert_after(cur, "Research gap", "h2")
    cur = h_gap
    for kind, payload in tex_items(tex_section("ch2", "sec:research-gap")):
        cur = d.insert_after(cur, delatex(payload), "p")
    cur = d.insert_after(cur, "", "p")
    d.comment_span(h_lit, cur, f"{AUTHOR} {TODAY}: New 'Summary of the reviewed literature' (Table 2.2: source, methodology, strengths, limitations, relation) "
                               f"and 'Research gap' sections (meeting 2026-09-09; UNISA guideline; comment 77).")
    d.fill_section(h_open, tex_items(tex_section("ch2", "sec:open-problems")),
                   note=f"{AUTHOR} {TODAY}: Open problems aligned with the revised LaTeX (GF-PR removed; holdout added).")

    # ------------------------------------------------------------- Chapter 3
    h_ch3 = d.heading("Research Methodology", level="Heading1")
    d.fill_section(h_ch3, tex_items(tex_preamble("ch3")),
                   note=f"{AUTHOR} {TODAY}: Chapter 3 opening rewritten as a link from Chapter 2 (meeting 2026-09-09).")
    h_gfg = P(1188, "Supplementary GF-PR graph", style="Heading2")
    d.set_para(h_gfg, "Temporal holdout protocol")
    d.fill_section(h_gfg, tex_items(tex_section("ch3", "sec:gf-pr-graph")),
                   note=f"{AUTHOR} {TODAY}: GF-PR graph section replaced by the temporal holdout protocol (T1 = 28 Feb 2026; T2 = Mar-May 2026; spender cohort) (comments 14, 74).")
    h_five = P(1201, "Five-proxy evaluation design", style="Heading2")
    d.set_para(h_five, "Construct-check design")
    d.fill_section(h_five, tex_items(tex_section("ch3", "sec:proxy-evaluation")),
                   note=f"{AUTHOR} {TODAY}: Evaluation design restated as construct checks on three families (transfer, allowance, Sybil-stability); "
                        f"inverse-risk and trading-success families withdrawn (comments 14, 310).")
    for i, pre in ((1254, "Inverse-risk family"), (1292, "Trading-success family"), (1309, "Liquidation family")):
        h = P(i, pre)
        d.set_para(h, para_text(h).strip() + " (archived; not used in the main comparison)")
        d.comment_para(h, f"{AUTHOR} {TODAY}: Family marked as archived: withdrawn from the main comparison because the proxies share their event source "
                          f"with the withdrawn outcome-native reference (comment 14). Definitions kept for the appendix archive.")
    # statistical tests: items
    st_items = {}
    for k, t in tex_items(tex_section("ch3", "sec:statistical-tests")):
        if k == "li":
            mm = re.match(r"([^:]+):", delatex(t))
            st_items[mm.group(1).strip() if mm else delatex(t)[:20]] = ("li", t)
    p_fam = P(1376, "Family aggregation")
    d.set_para(p_fam, delatex(st_items["Family aggregation"][1]))
    for i in (1377, 1378):
        d.delete_or_clear(d.paras[i - 1])
    p_or = P(1379, "Orientation and missingness")
    d.set_para(p_or, delatex(st_items["Orientation and missingness"][1]))
    p_not = P(1380, "What is not tested")
    d.set_para(p_not, delatex(st_items["What is not tested"][1]))
    p_unc = d.insert_after(p_fam, delatex(st_items["Uncertainty"][1]), "li")
    p_dif = d.insert_after(p_unc, delatex(st_items["Difference tests"][1]), "li")
    d.comment_span(p_fam, p_not, f"{AUTHOR} {TODAY}: Statistical tests extended: paired wallet bootstrap ({N['n_boot']} resamples, seed {N['seed']}) for every tau, "
                                 f"and six pre-specified paired difference tests; 'What is not tested' updated (comment 237).")
    # benchmark protocol
    h_bench = P(1382, "Computational benchmark (Claim C1)", style="Heading2")
    d.fill_section(h_bench, tex_items(tex_section("ch3", "sec:computational-benchmark")),
                   note=f"{AUTHOR} {TODAY}: Benchmark protocol unified: one untimed warm-up, {N['repeats']} timed solves, per-session memoisation so identical graphs "
                        f"give identical numbers in every table (comments 240, 283, 286).")
    # scaling / robustness protocol sections
    h_scal = P(1393, "Scaling and robustness extensions", style="Heading2")
    d.fill_section(h_scal, tex_items(tex_section("ch3", "sec:scaling-robustness")))
    for idx_h, pre, lab in ((1397, "Expanded wallet pool", "sub:expanded-pool"), (1403, "Damping sensitivity", "sub:damping-protocol"),
                            (1406, "Top-token subgraph", "sub:top-tokens"), (1410, "Sample-size sensitivity", "sub:sample-size-protocol")):
        h = P(idx_h, pre, style="Heading3")
        new_title = re.search(r"\\dissertationSubsubheading\[" + re.escape(lab) + r"\]\{([^}]*)\}", tex_source("ch3")).group(1)
        d.set_para(h, delatex(new_title))
        d.fill_section(h, tex_items(tex_section("ch3", lab)),
                       note=f"{AUTHOR} {TODAY}: Protocol re-framed: the {ic(N['pool_supp'])} supplemental pool addresses have no extracted edges, so pool stages vary "
                            f"node count only, and the sample-definition sweep is not a robustness check; matched cohort is the primary sample (comments 288, 299).")
    h_gmxv = P(1413, "GMX proxy definition variants", style="Heading3")
    d.set_para(h_gmxv, "GMX proxy definition variants (archived)")
    d.comment_para(h_gmxv, f"{AUTHOR} {TODAY}: GMX proxy variants belong to the withdrawn trading-success family; kept for the appendix archive only (comment 14).")
    # reproducibility
    h_rep = P(1417, "Reproducibility", style="Heading2")
    d.fill_section(h_rep, tex_items(tex_section("ch3", "sec:reproducibility")),
                   note=f"{AUTHOR} {TODAY}: Repository {REPO_URL}, commit {COMMIT}, versioned configuration and machine-readable summary named (comment 81).")
    # ethics
    h_eth = P(1438, "Ethics", style="Heading2")
    d.fill_section(h_eth, tex_items(tex_section("ch3", "sec:ethics")),
                   note=f"{AUTHOR} {TODAY}: Ethics wording made definite and the certificate appendix referenced; the certificate reference number and date "
                        f"are placeholders (TBD) to be filled from the issued certificate, not invented (comment 264).")

    # ------------------------------------------------------------- Chapter 4
    h_ch4 = d.heading("Implementation and Empirical Results", level="Heading1")
    d.fill_section(h_ch4, tex_items(tex_preamble("ch4")),
                   note=f"{AUTHOR} {TODAY}: Chapter 4 opening rewritten as a link from Chapter 3; results are stated once and referenced thereafter (comment 82).")
    h_ds = P(1458, "Dataset", style="Heading2")
    d.set_para(h_ds, "Case study setting: Arbitrum One")
    d.comment_para(h_ds, f"{AUTHOR} {TODAY}: Heading renamed to present the case-study setting (UNISA guideline Table 2). Cohort table and figures unchanged.")
    h_b = P(1586, "EndorseRank vs. AWP benchmark", style="Heading2")
    d.set_para(h_b, "Computational benchmark (Claim C1)")
    b_before, b_after = split_at_table(tex_items(tex_section("ch4", "sec:benchmark-results")))
    d.fill(d.range_targets(1588, 1588), b_before, anchor=h_b)
    d.set_para(P(1589, "Table 4.2"), f"Table 4.2: Computational benchmark on the matched wallet cohort (n = 5,521). Runtime = mean PageRank wall time over "
                                     f"{N['repeats']} timed solves after one untimed warm-up (SD in parentheses); peak memory via tracemalloc during the warm-up; "
                                     f"|V| and |E| of each graph.")
    d.set_cells(1592, ["Runtime (s), mean (SD)", "Peak mem. (MB)", "Iters", "|E| (|V|)"], expect=["Runtime (s)", "Peak mem. (MB)", "Iters", "Edges"])
    d.set_cells(1597, [f"{f3(N['er_rt'])} ({f3(N['er_sd'])})", f1(N["er_mem"]), str(N["er_it"]), f"{N['er_E']} ({N['er_V']})"],
                expect=["2.105", "4.6", "37.0", "14727"])
    d.set_cells(1602, [f"{f3(N['awp_rt'])} ({f3(N['awp_sd'])})", f1(N["awp_mem"]), str(N["awp_it"]), f"{N['awp_E']} ({N['awp_V']})"],
                expect=["18.711", "38.2", "100.0", "137087"])
    assert norm(para_text(d.paras[1605])) == "gf-pr"
    d.remove_row_of(1606)
    d.comment_span(P(1589), P(1589), f"{AUTHOR} {TODAY}: Table 4.2 regenerated from eval_summary.json ({TODAY}): {f3(N['er_rt'])} s vs {f3(N['awp_rt'])} s "
                                     f"({N['speedup']:.1f}x), SD, |V| and |E| added, GF-PR row removed (comments 14, 240, 283, 288).")
    d.set_para(P(1615, "1Excluding graph construction"), "")
    d.fill(d.range_targets(1611, 1623), b_after, anchor=P(1589),
           note=f"{AUTHOR} {TODAY}: Benchmark interpretation rewritten: numbers stated once, the three previously different runtimes explained and unified "
                f"under one protocol, GF-PR runtime paragraph removed (comments 283, 240, 82, 14).")
    # scaling
    h_sc = P(1624, "Runtime scaling on the expanded wallet pool", style="Heading3")
    d.set_para(h_sc, "Node-count sensitivity on the expanded pool")
    s_before, s_after = split_at_table(tex_items(tex_section("ch4", "sub:runtime-scaling")))
    d.fill(d.range_targets(1625, 1626), s_before, anchor=h_sc)
    d.set_para(P(1628, "Table 4.3"), f"Table 4.3: Node-count sensitivity of runtime on the expanded wallet pool (N = {ic(N['pool_N'])}; SHA256 seed benchmark-tier2-v1). "
                                     f"Stages subsample the extraction wallet set; ER speedup = AWP/ER runtime ratio. Supplemental pool addresses have no extracted edges, "
                                     f"so |E| grows only up to the cohort graph.")
    hdr = P(1630)
    d.set_para(hdr, "n | ER (s) | AWP (s) | Speedup | ER |V| | ER |E| | AWP |V| | AWP |E|")
    rows_t2 = N["tier2_rows"]
    cur = hdr
    tline_targets = [P(1631)]
    for k, r in enumerate(rows_t2):
        line = " | ".join([ic(r["n_wallets"]), f3(r["endorserank"]["runtime_sec_mean"]), f3(r["awp"]["runtime_sec_mean"]),
                           f"{r['er_speedup_ratio']:.1f}×", ic(r["endorserank"]["node_count"]), ic(r["endorserank"]["edge_count"]),
                           ic(r["awp"]["node_count"]), ic(r["awp"]["edge_count"])])
        if k < len(tline_targets):
            d.set_para(tline_targets[k], line)
            cur = tline_targets[k]
        else:
            cur = d.insert_after(cur, line, "tline")
    d.comment_span(P(1628), cur, f"{AUTHOR} {TODAY}: Table 4.3 regenerated with per-stage |V| and |E| for both methods; N = {ic(N['pool_N'])}; "
                                 f"n = 10,000 row agrees with Table 4.6 ({rows_t2[0]['er_speedup_ratio']:.1f}x) (comments 286, 288).")
    fig44 = d.find_after("Figure 4.4:", 1631)
    d.fill(d.range_targets(1632, d.idx(fig44) - 1), s_after, anchor=cur,
           note=f"{AUTHOR} {TODAY}: Scaling text re-framed as node-count sensitivity; caveats state that pool stages do not grow the edge set (comments 286, 288).")
    # robustness heading + damping
    h_rob = P(1675, "Robustness checks", style="Heading2")
    d.set_para(h_rob, "Robustness and sensitivity checks")
    d.fill_section(h_rob, tex_items(tex_section("ch4", "sec:robustness-results")))
    h_damp = P(1679, "Damping sensitivity", style="Heading3")
    dm_before, dm_after = split_at_table(tex_items(tex_section("ch4", "sub:damping")))
    d.fill(d.range_targets(1680, 1681), dm_before, anchor=h_damp)
    d.set_para(P(1682, "Table 4.4"), "Table 4.4: Sensitivity of family-mean Kendall τ and runtime to PageRank damping d ∈ {0.75, 0.85, 0.95} on the matched wallet cohort "
                                     f"(n = 5,521). Runtime = mean of {N['repeats']} timed solves after one warm-up; the d = 0.85 row is the same measurement as Table 4.2.")
    dr = {round(r["damping"], 2): r for r in N["damping_rows"]}
    for base, dv in ((1691, 0.75), (1698, 0.85), (1705, 0.95)):
        r = dr[dv]
        d.set_cells(base, [f"{dv:.2f}", f3(r["er_allowance_tau"]), f3(r["awp_allowance_tau"]), f3(r["er_transfer_tau"]), f3(r["awp_transfer_tau"]),
                           f3(r["endorserank_runtime_sec"]), f3(r["awp_runtime_sec"])], expect=[f"{dv:.2f}", None, None, None, None, None, None])
    d.comment_para(P(1682), f"{AUTHOR} {TODAY}: Table 4.4 regenerated under the unified timing protocol; d = 0.85 row now equals Table 4.2 "
                            f"({f3(dr[0.85]['endorserank_runtime_sec'])} s / {f3(dr[0.85]['awp_runtime_sec'])} s) (comment 283).")
    fig45 = d.find_after("Figure 4.5:", 1712)
    d.fill(d.range_targets(1713, d.idx(fig45) - 1), dm_after, anchor=P(1712),
           note=f"{AUTHOR} {TODAY}: Damping interpretation rewritten from the regenerated table (comment 283).")
    # top tokens
    h_tok = P(1758, "Top-token subgraph", style="Heading3")
    tk_before, tk_after = split_at_table(tex_items(tex_section("ch4", "sub:token-subgraph")))
    tok_targets = [p for p in d.section_targets(h_tok) if not norm(para_text(p)).startswith("table 4.5")]
    d.fill(tok_targets, tk_before + tk_after, anchor=h_tok, note=f"{AUTHOR} {TODAY}: Top-token paragraph aligned with the revised LaTeX.")
    # sample size
    h_ss = P(1768, "Sample-size sensitivity", style="Heading3")
    d.set_para(h_ss, "Sample-definition sensitivity")
    ss_before, ss_after = split_at_table(tex_items(tex_section("ch4", "sub:sample-size")))
    d.fill(d.range_targets(1769, 1770), ss_before, anchor=h_ss)
    d.set_para(P(1771, "Table 4.6"), f"Table 4.6: Sample-definition sensitivity: allowance and transfer family-mean τ and runtime for staged subsamples of the expanded "
                                     f"wallet pool (N = {ic(N['pool_N'])}; seed benchmark-tier2-v1). The pool is a different population from the matched cohort; "
                                     f"decimal values are not comparable with Table 4.7.")
    hdr = P(1772)
    d.set_para(hdr, "n | ER all. | AWP all. | ER tr. | AWP tr. | ER (s) | AWP (s) | Speedup")
    cur = hdr
    tline_targets = [P(1773)]
    for k, r in enumerate(N["ssw_rows"]):
        line = " | ".join([ic(r["n_wallets"]), f3(r["er_allowance_tau"]), f3(r["awp_allowance_tau"]), f3(r["er_transfer_tau"]), f3(r["awp_transfer_tau"]),
                           f3(r["endorserank_runtime_sec"]), f3(r["awp_runtime_sec"]), f"{r['er_speedup_ratio']:.1f}×"])
        if k < len(tline_targets):
            d.set_para(tline_targets[k], line)
            cur = tline_targets[k]
        else:
            cur = d.insert_after(cur, line, "tline")
    d.comment_span(P(1771), cur, f"{AUTHOR} {TODAY}: Table 4.6 regenerated; runtimes are the same memoised measurements as Table 4.3 (comment 286).")
    d.fill(d.range_targets(1774, 1781), ss_after, anchor=cur,
           note=f"{AUTHOR} {TODAY}: Re-framed: the matched cohort is primary and presented with intervals; the pool rows show that the comparative structure, "
                f"not the decimal values, travels across populations; no longer described as robustness (comment 299).")
    # alignment section
    h_al = P(1782, "Social-method alignment", style="Heading2")
    d.set_para(h_al, "Same-window alignment: EndorseRank vs. AWP (Claims C2–C3)")
    al_items = tex_items(tex_section("ch4", "sec:three-method-alignment"))
    k_tbl = next(i for i, it in enumerate(al_items) if it[0] == "table")
    al_before = al_items[:k_tbl]
    al_rest = [it for it in al_items[k_tbl + 1:] if it[0] != "table"]  # tau-diff table is built below from the summary
    d.fill(d.range_targets(1783, 1784), al_before, anchor=h_al)
    # old Table 4.7 (3-method summary incl. GF-PR) is removed: the LaTeX moved the two-method summary to the appendix (Table 8.2)
    cap47 = P(1785, "Table 4.7")
    fam = N["fam"]
    ci_rows = [["Family", "ER mean τ", "ER 95% CI", "AWP mean τ", "AWP 95% CI"]]
    for key, name in (("transfer", "Transfer"), ("allowance", "Allowance"), ("sybil_stability", "Sybil-adjusted stability")):
        e, a = fam["endorserank"][key], fam["awp"][key]
        ci_rows.append([name, f3(e["mean_tau"]), ci(e["ci_low"], e["ci_high"]), f3(a["mean_tau"]), ci(a["ci_low"], a["ci_high"])])
    inter = N["inter"]
    ci_rows.append(["EndorseRank vs. AWP score agreement", f3(inter["kendall_tau"]), ci(inter["ci_low"], inter["ci_high"]), "", ""])
    c7 = d.insert_after(cap47.getprevious(), f"Table 4.7: Family-mean Kendall τ with bootstrap confidence intervals on the matched cohort (n = 5,521). "
                                             f"CI = 95% percentile bootstrap over wallets ({N['n_boot']} paired resamples, seed {N['seed']}).", "p")
    t7 = d.insert_table_after(c7, ci_rows)
    sp = d.insert_after(t7, "", "p")
    d.comment_span(c7, sp, f"{AUTHOR} {TODAY}: New Table 4.7: family-mean tau with 95% paired-bootstrap CI and the inter-method tau {f3(inter['kendall_tau'])} "
                           f"{ci(inter['ci_low'], inter['ci_high'])}, generated from eval_summary.json; it replaces the old three-method summary table with the GF-PR row, "
                           f"which now lives (two methods only) in Appendix Table 8.2 (comments 237, 129, 14).")
    old47 = cap47.getnext()
    while old47 is not None and localname(old47) != "tbl":
        old47 = old47.getnext()
    d.delete_or_clear(cap47)
    d.delete_or_clear(old47)
    for p in d.range_targets(1819, 1823):  # text between the old table and the heatmap
        d.delete_or_clear(p)
    # heatmap caption + text after the heatmap: pattern paragraph, Table 4.14, remaining paragraphs
    fig46 = d.find_after("Figure 4.6:", 1785)
    d.set_para(fig46, "Figure 4.6: " + fig_caption("ch4", "fig:alignment-heatmap"))
    d.comment_para(fig46, f"{AUTHOR} {TODAY}: Heatmap caption updated (values of Table 4.7; GF-PR removed from the figure in the LaTeX build; the embedded "
                          f"image is the reviewed export and is regenerated by the build).")
    h_pfd = P(1904, "Proxy family detail", style="Heading2")
    after_fig = split_targets_at(d.section_targets(h_al), fig46)[1]
    d.set_para(after_fig[0], delatex(al_rest[0][1]))
    td_rows = [["Contrast (a minus b)", "τa", "τb", "Δτ", "95% CI of Δτ", "P(Δτ > 0)"]]
    for r in N["tau_diff"]:
        lab = r["label"].replace("GMX-success", "GMX-success (archived)")
        td_rows.append([lab, f3(r["a"]["tau"]), f3(r["b"]["tau"]), f"{r['delta_tau']:+.3f}", ci(r["ci_low"], r["ci_high"]), f3(r["share_positive"])])
    c14 = d.insert_after(after_fig[0], f"Table 4.14: Paired bootstrap tests of differences between Kendall τ coefficients (matched cohort, n = 5,521). Family entries use the "
                                       f"family-mean τ; the same wallet resamples are used for a and b, so the interval is on the paired difference. An interval excluding 0 "
                                       f"indicates a difference not attributable to sampling variation at the 5% level ({N['n_boot']} paired resamples, seed {N['seed']}).", "p")
    t14 = d.insert_table_after(c14, td_rows)
    sp2 = d.insert_after(t14, "", "p")
    d.fill(after_fig[1:], al_rest[1:], anchor=sp2)
    d.comment_span(after_fig[0], after_fig[-1] if is_attached(after_fig[-1], d.body) else sp2,
                   f"{AUTHOR} {TODAY}: Alignment interpretation rewritten around intervals and the six pre-specified paired difference tests of new Table 4.14; "
                   f"family winners stated once; GF-PR removed (comments 237, 82, 14).")
    d.fill_section(h_pfd, tex_items(tex_section("ch4", "sec:proxy-family-detail")),
                   note=f"{AUTHOR} {TODAY}: Proxy-family introduction aligned with the LaTeX (per-proxy rho, tau and 95% CI; transfer proxies from Do, Do and Nguyen [3]).")

    def table_section(h_idx, h_prefix, style, key, label, cap_prefix, title_no, note_text, table_note):
        """Section = [text] + caption + real table + [text]; caption and table are rebuilt from the LaTeX table file."""
        h = P(h_idx, h_prefix, style=style)
        m = re.search(r"\\dissertationSub(?:sub)?heading\[" + re.escape(label) + r"\]\{((?:[^{}]|\{[^{}]*\})*)\}", tex_source(key))
        title = delatex(m.group(1))
        if norm(title) != norm(para_text(h)):
            d.set_para(h, title)
        items = tex_items(tex_section(key, label))
        k = next(i for i, it in enumerate(items) if it[0] == "table")
        cap, rows = table_lines(items[k][1])
        cap_p = d.find_after(cap_prefix, h_idx)
        before, after = split_targets_at(d.section_targets(h), cap_p)
        d.fill(before, items[:k], anchor=h)
        d.set_para(cap_p, f"Table {title_no}: {cap}")
        el = cap_p.getnext()
        while el is not None and localname(el) == "p":  # caption continuation lines / blanks before the table
            nxt = el.getnext()
            d.delete_or_clear(el)
            el = nxt
        new_tbl = d.replace_table_after(cap_p, rows)
        d.comment_span(cap_p, new_tbl, table_note)
        after = [q for q in after if is_attached(q, d.body)]
        d.fill(after, [it for it in items[k + 1:] if it[0] != "table"], anchor=new_tbl, note=note_text)
        return h

    def family_block(h_idx, h_prefix, label, cap_prefix, title_no, note_text):
        return table_section(h_idx, h_prefix, "Heading3", "ch4", label, cap_prefix, title_no, note_text,
                             f"{AUTHOR} {TODAY}: Table {title_no} regenerated from eval_summary.json with a 95% bootstrap CI column for tau; caption from the LaTeX (comment 237).")

    family_block(1908, "Transfer family", "sub:transfer-family", "Table 4.8:", "4.8",
                 f"{AUTHOR} {TODAY}: Transfer-family interpretation aligned with the LaTeX (AWP own-construct agreement read as a construct check; Do, Do and Nguyen [3]).")
    family_block(1951, "Allowance family", "sub:allowance-family", "Table 4.9:", "4.9",
                 f"{AUTHOR} {TODAY}: Allowance-family interpretation rewritten: agreement is expected because EndorseRank smooths allowance in-degree; "
                 f"it is an intended-construct check, and the within-method difference against transfer is not significant (Table 4.14) (comment 310).")
    h_inv = P(1994, "Inverse-risk family (GMX PnL)", style="Heading3")
    for h in (h_inv, P(2106, "Trading-success family", style="Heading3")):
        d.set_para(h, para_text(h).strip() + " (archived; not part of the main comparison)")
        d.comment_para(h, f"{AUTHOR} {TODAY}: Results for this family are archived and excluded from the primary claims (comments 14, 310).")
    family_block(2053, "Sybil-adjusted stability family", "sub:sybil-family", "Table 4.11:", "4.11",
                 f"{AUTHOR} {TODAY}: Sybil-stability interpretation aligned with the LaTeX (difference test in Table 4.14).")
    # holdout section replaces GF-PR ceiling
    h_gfc = P(2254, "Supplementary GF-PR ceiling analysis", style="Heading2")
    d.set_para(h_gfc, "Temporal holdout of future new approvals (RQ4)")
    d.fill_section(h_gfc, tex_items(tex_section("ch4", "sec:gf-pr-ceiling")), table_titles=["Table 4.13"],
                   note=f"{AUTHOR} {TODAY}: GF-PR ceiling section (SRQ1/SC1) replaced by the temporal holdout of future new approvals with Table 4.13 "
                        f"(spender cohort n = 1,335; EndorseRank tau 0.479 [0.426, 0.529] vs AWP 0.044 [-0.011, 0.095]) (comments 14, 74, 78).")
    # claims
    h_cl = P(2264, "Primary claims (C1–C4) and supplementary claim (SC1)", style="Heading2")
    d.set_para(h_cl, "Primary claims (C1–C4)")
    d.delete_or_clear(P(2279, "Supplementary claim:", style="Heading3"))
    cl_targets = [p for p in d.range_targets(2266, 2290)]
    d.fill(cl_targets, tex_items(tex_section("ch4", "sec:empirical-claims")), anchor=h_cl,
           note=f"{AUTHOR} {TODAY}: Claims C1-C4 restated (C1 as a sparsity consequence with edge counts; C2 as intended-construct checks; C3 with paired-difference "
                f"intervals; C4 including the holdout); SC1 removed; numbers referenced by table instead of repeated (comments 14, 62, 82, 237).")

    # ------------------------------------------------------------- Chapter 5
    h_ch5 = d.heading("Discussion", level="Heading1")
    d.fill_section(h_ch5, tex_items(tex_preamble("ch5")),
                   note=f"{AUTHOR} {TODAY}: Chapter 5 opening rewritten as a link from Chapter 4; numbers are not restated (comment 82).")
    h_frq = P(2297, "Findings by research question", style="Heading2")
    d.fill_section(h_frq, tex_items(tex_section("ch5", "sec:findings-rq")), stop_at=P(2301, "RQ1", style="Heading3"))
    for i, lab in ((2301, "sub:finding-rq1"), (2308, "sub:finding-rq2"), (2321, "sub:finding-rq3"), (2329, "sub:finding-rq4")):
        h = d.paras[i - 1]
        assert pstyle(h) == "Heading3", (i, para_text(h))
        title = re.search(r"\\dissertationSubsubheading\[" + re.escape(lab) + r"\]\{([^}]*)\}", tex_source("ch5")).group(1)
        d.set_para(h, delatex(title))
        d.fill_section(h, tex_items(tex_section("ch5", lab)),
                       note=f"{AUTHOR} {TODAY}: {delatex(title)} rewritten: interpretation refers to the Chapter 4 tables and intervals instead of repeating numbers; "
                            f"RQ4 is the temporal holdout (comments 74, 82, 237, 310).")
    h_srq = P(2335, "Supplementary finding (SRQ1)", style="Heading2")
    nxt = P(2342, "Theoretical implications", style="Heading2")
    d.delete_section(h_srq)
    # objectives achievement section before Theoretical implications
    anchor = nxt.getprevious()
    if anchor is None or para_text(anchor).strip():
        anchor = nxt.getprevious() or nxt
    h_oa = d.insert_after(anchor, "Achievement of the research objectives", "h2")
    cur = h_oa
    for kind, payload in tex_items(tex_section("ch5", "sec:objectives-achievement")):
        if kind == "table":
            cap, rows = table_lines(payload)
            cur = d.insert_after(cur, "Table 5.1: " + cap, "p")
            cur = d.insert_table_after(cur, rows)
            cur = d.insert_after(cur, "", "p")
        else:
            cur = d.insert_after(cur, delatex(payload), "p")
    cur = d.insert_after(cur, "", "p")
    d.comment_span(h_oa, cur, f"{AUTHOR} {TODAY}: New section 'Achievement of the research objectives' (Table 5.1: objective, criterion, evidence, outcome) "
                              f"replacing 'Supplementary finding (SRQ1)' (comments 72, 14).")
    h_mult = P(2393, "From valuation multiples to reputation multiples", style="Heading3")
    d.set_para(h_mult, "Standardised scores as shared infrastructure")
    d.fill_section(h_mult, tex_items(tex_section("ch5", "sub:deploy-multiples")),
                   note=f"{AUTHOR} {TODAY}: Valuation-multiples analogy cut to one paragraph without the finance-theory citation cluster (comment 349).")
    h_syb = P(2405, "Sybil attack cost model on allowance graphs", style="Heading2")
    anchor = h_syb.getprevious()
    if anchor is None or para_text(anchor).strip():
        anchor = h_syb.getprevious() or h_syb
    h_soc = d.insert_after(anchor, "Societal and practical impact", "h2")
    cur = h_soc
    for kind, payload in tex_items(tex_section("ch5", "sec:societal-impact")):
        cur = d.insert_after(cur, delatex(payload), "p" if kind != "li" else "li")
    cur = d.insert_after(cur, "", "p")
    d.comment_span(h_soc, cur, f"{AUTHOR} {TODAY}: New section 'Societal and practical impact' (comment 1; meeting 2026-09-09).")

    # ------------------------------------------------------------- Chapter 6
    h_ch6 = P(2546, "Conclusion and Future Work", style="Heading1")
    d.fill_section(h_ch6, tex_items(tex_preamble("ch6")),
                   note=f"{AUTHOR} {TODAY}: Chapter 6 opening rewritten as a link from Chapter 5.")
    h_sf = P(2550, "Summary of findings", style="Heading2")
    d.set_para(h_sf, "Answers to the research questions")
    d.fill_section(h_sf, tex_items(tex_section("ch6", "sec:summary-findings")),
                   note=f"{AUTHOR} {TODAY}: Findings restated as one answer per research question with references to the Chapter 4 tables; SRQ1 paragraph removed; "
                        f"numbers not repeated (comments 14, 82).")
    h_oc = P(2566, "Original contribution to knowledge", style="Heading2")
    d.fill_section(h_oc, tex_items(tex_section("ch6", "sec:contribution-knowledge")),
                   note=f"{AUTHOR} {TODAY}: Contribution to knowledge rewritten (construct, inference design, temporal holdout) without repeating the Chapter 1 list "
                        f"(comments 378, 77, 78).")
    h_fw = P(2578, "Future work", style="Heading2")
    d.fill_section(h_fw, tex_items(tex_section("ch6", "sec:future-work")),
                   note=f"{AUTHOR} {TODAY}: Future work aligned with the LaTeX (edge-growth scaling, credit-risk labels, methodological development).")

    # ------------------------------------------------------------- Appendix
    h_pipe = P(2695, "Pipeline stages", style="Heading3")
    d.fill_section(h_pipe, tex_items(tex_section("app", "sec:pipeline-stages")),
                   note=f"{AUTHOR} {TODAY}: Pipeline stages updated: bootstrap and timing protocol, run command and date, second-tier extraction outcome (comments 81, 240, 288).")
    # Table 8.1
    d.set_para(P(2711, "Table 8.1"), f"Table 8.1: In-cohort runtime scaling (SHA256 seed benchmark-scale-v1; n ≤ 5,521 matched cohort). Runtime = mean of {N['repeats']} timed solves "
                                     f"after one warm-up; the n = 5,521 row is the same measurement as Table 4.2.")
    for k, r in enumerate(N["scaling_rows"]):
        base = 2719 + 6 * k
        d.set_cells(base, [ic(r["n_wallets"]).replace(",", ""), f3(r["endorserank"]["runtime_sec_mean"]), f3(r["awp"]["runtime_sec_mean"]),
                           f"{r['er_speedup_ratio']:.1f}×", str(r["endorserank"]["edge_count"]), str(r["awp"]["edge_count"])],
                    expect=[str(r["n_wallets"]), None, None, None, None, None])
    d.comment_para(P(2711), f"{AUTHOR} {TODAY}: Table 8.1 regenerated under the unified timing protocol; n = 5,521 row equals Table 4.2 (comments 240, 283).")
    # claim map
    d.set_para(P(3209, "Evidence: Table 4.2"), f"Evidence: Table 4.2 ({f3(N['er_rt'])} s vs. {f3(N['awp_rt'])} s, ≈ {N['speedup']:.1f}×, |E| 14,727 vs. 137,087); "
                                                f"Table 4.3 (node-count sensitivity, speedup {min(r['er_speedup_ratio'] for r in N['tier2_rows']):.1f}×–"
                                                f"{max(r['er_speedup_ratio'] for r in N['tier2_rows']):.1f}×); Table 8.1; Figure 4.4.")
    d.delete_or_clear(P(3210))
    d.set_para(P(3212, "RQ4", style="Heading3"), "RQ4 — Temporal holdout")
    d.set_para(P(3214, "Statement:"), "Statement: Scores frozen at t1 predict new owner–spender approvals at t2 on inbound spenders more strongly for EndorseRank than for AWP.")
    d.set_para(P(3215, "Evidence:"), "Evidence: Table 4.13 (EndorseRank τ = 0.479 [0.426, 0.529]; AWP τ = 0.044 [−0.011, 0.095]); Section 4.7.")
    d.delete_section(P(3217, "SRQ1 / SC1", style="Heading3"))
    d.set_para(P(3225, "C2:"), "C2: intended-construct checks with intervals away from zero (Table 4.7; Tables 4.8–4.9).")
    d.set_para(P(3227, "C4:"), "C4: efficiency–alignment trade-off combining C1 with the allowance and holdout results (Tables 4.7, 4.13); robustness in Tables 4.4–4.6 and Figure 4.5.")
    d.delete_or_clear(P(3228))
    d.comment_span(P(3208), P(3227), f"{AUTHOR} {TODAY}: Claim map updated to the regenerated tables; RQ4 = temporal holdout; SRQ1/SC1 block removed (comments 14, 74, 283).")
    # claim-map sub-sections whose LaTeX text changed (statements/evidence for H1-H3, non-claims, artifacts)
    for i, pre, lab in ((3192, "H1 / RQ1", "sec:map-h1"), (3199, "H2 / RQ2", "sec:map-h2"), (3206, "H3 / RQ3", "sec:map-h3"),
                        (3230, "Explicit non-claims", "sec:map-nonclaims"), (3240, "Artifact checklist", "sec:map-artifacts")):
        if i in (3206,):
            continue  # H3 block edited cell by cell above
        sec_fill(i, pre, "Heading3", "appe", lab,
                 f"{AUTHOR} {TODAY}: Claim-map entry aligned with the revised LaTeX (tables with intervals; GF-PR/SC1 removed) (comments 14, 237).")

    # ------------------------------------------------------------- remaining sections mirrored from the LaTeX
    # Chapter 2 body sections with new 2020-2026 sources and re-attributed AWP citations
    sec_fill(536, "Blockchain and DeFi foundations", "Heading2", "ch2", "sec:blockchain-defi-foundations",
             f"{AUTHOR} {TODAY}: Section aligned with the LaTeX: recent (2020-2026) sources added, citation clusters split, superseded references dropped (comments 396, 20; meeting 2026-09-09).")
    sec_fill(544, "Pseudonymity and the credit problem", "Heading3", "ch2", "sub:pseudonymity-credit",
             f"{AUTHOR} {TODAY}: Section aligned with the LaTeX (citations split; recent sources).")
    sec_fill(551, "Ethereum, Layer-2 rollups, and Arbitrum One", "Heading2", "ch2", "sec:ethereum-l2",
             f"{AUTHOR} {TODAY}: Section aligned with the LaTeX: recent L2/Arbitrum sources added (meeting 2026-09-09).")
    sec_fill(558, "ERC-20 tokens and the allowance lifecycle", "Heading2", "ch2", "sec:erc20-allowance-lifecycle",
             f"{AUTHOR} {TODAY}: Section aligned with the LaTeX (Figure 2.1 unchanged).")
    h_gr = P(564, "Graph-based on-chain reputation", style="Heading2")
    gr_items = [it for it in tex_items(tex_section("ch2", "sec:graph-reputation")) if it[0] != "table"]
    d.fill(d.range_targets(565, 567), gr_items[:1], anchor=h_gr)
    d.fill(d.range_targets(590, 593), gr_items[1:], anchor=P(589, "Figure 2.1:"),
           note=f"{AUTHOR} {TODAY}: Graph-based reputation paragraphs rewritten: AWP attributed to Do, Do and Nguyen (RIVF 2023) [3] and kept distinct from "
                f"Do and Do (2023) [4]; Lin et al. and recent graph-risk sources cited (comments 396, 2, 20).")
    h_tsv = P(689, "Trading success validation frame (GMX V2)", style="Heading2")
    d.delete_section(h_tsv)
    d.comment_para(P(696), f"{AUTHOR} {TODAY}: Section 'Trading success validation frame (GMX V2)' removed: the trading-success frame is withdrawn from the main narrative (comment 14).")
    h_tf = P(737, "Theoretical framework", style="Heading2")
    tf_items = tex_items(tex_section("ch2", "sec:theoretical-framework"))
    d.fill(d.range_targets(738, 758), tf_items, anchor=h_tf,
           note=f"{AUTHOR} {TODAY}: Theoretical framework aligned with the LaTeX: GF-PR supplementary role removed; construct checks and the temporal holdout named; "
                f"AWP cited as Do, Do and Nguyen [3] (comments 14, 396).")
    for i in range(759, 787):
        p = d.paras[i - 1]
        for old, new in (("Trading Success Alignment", "Construct Checks"), ("Social-method alignment", "Allowance vs transfer"),
                         ("Supplementary: GF-PR outcome-native ceiling (SRQ1)", "RQ4: temporal holdout of future new approvals")):
            replace_in_para(p, old, new)
    cap23 = P(787, "Figure 2.3:")
    d.set_para(cap23, "Figure 2.3: " + fig_caption("ch2", "fig:conceptual-model"))
    d.comment_para(cap23, f"{AUTHOR} {TODAY}: Conceptual model relabelled (construct checks; RQ4 temporal holdout replaces the GF-PR box) and caption updated (comment 14).")
    sec_fill(790, "Reader’s guide to terminology", "Heading2", "ch2", "sub:terminology",
             f"{AUTHOR} {TODAY}: Terminology guide aligned with the LaTeX: GF-PR reference and alignment bands removed (comments 14, 128, 129).")
    sec_fill(804, "Domain alignment metrics", "Heading2", "ch2", "sec:domain-alignment-metrics",
             f"{AUTHOR} {TODAY}: Section aligned with the LaTeX (intervals instead of thresholds).")
    sec_fill(822, "DeFi risk taxonomy and where reputation fits", "Heading2", "ch2", "sec:defi-risk-taxonomy",
             f"{AUTHOR} {TODAY}: Section aligned with the LaTeX (recent sources; superseded references dropped).")
    h_perp = P(828, "Perpetual markets as a validation laboratory", style="Heading2")
    d.delete_section(h_perp)
    sec_fill(834, "Related measurement traditions", "Heading2", "ch2", "sec:related-measurement",
             f"{AUTHOR} {TODAY}: Section aligned with the LaTeX; preceding section 'Perpetual markets as a validation laboratory' removed with the trading-success frame (comment 14).")
    sec_fill(841, "Accounts, gas, and why logs are the measurement surface", "Heading2", "ch2", "sec:account-model",
             f"{AUTHOR} {TODAY}: Section aligned with the LaTeX.")
    sec_fill(846, "Approvals as security-relevant events", "Heading2", "ch2", "sec:approval-security",
             f"{AUTHOR} {TODAY}: Section aligned with the LaTeX (recent approval-security sources).")
    sec_fill(851, "AWP in depth", "Heading2", "ch2", "sec:awp-in-depth",
             f"{AUTHOR} {TODAY}: Heading and text corrected: AWP is Do, Do and Nguyen (RIVF 2023) [3]; Do and Do (2023) [4] is the PageRank/HodgeRank paper (comments 396, 2).")
    table_section(855, "Comparison of graph reputation methods", "Heading2", "ch2", "sec:method-comparison-table", "Table 2.1:", "2.1",
                  f"{AUTHOR} {TODAY}: Text around Table 2.1 aligned with the LaTeX.",
                  f"{AUTHOR} {TODAY}: Table 2.1 regenerated from the LaTeX (GF-PR row removed; AWP attribution corrected) (comments 14, 396).")
    # Chapter 3 sections whose LaTeX dropped the GMX phase
    sec_fill(988, "Data sources and sampling", "Heading2", "ch3", "sec:data-sources",
             f"{AUTHOR} {TODAY}: Data sources aligned with the LaTeX: GMX outcome stream removed from the primary universe; matched cohort definition kept (comment 14).")
    sec_fill(1010, "Three-phase collection strategy", "Heading2", "ch3", "sec:collection-strategy",
             f"{AUTHOR} {TODAY}: Collection strategy reduced to two phases (reputation streams; local evaluation); the GMX phase is withdrawn with the trading-success frame (comment 14).")
    sec_fill(1424, "Sampling considerations and missingness", "Heading2", "ch3", "sec:sampling-bias",
             f"{AUTHOR} {TODAY}: Sampling considerations aligned with the LaTeX (expanded pool N = {ic(N['pool_N'])}, nodes only).")
    sec_fill(1430, "Implementation notes", "Heading2", "ch3", "sec:implementation-notes", f"{AUTHOR} {TODAY}: Implementation notes aligned with the LaTeX.")
    # Chapter 4 figure caption
    cap44 = d.find_after("Figure 4.4:", 1631)
    d.set_para(cap44, "Figure 4.4: " + fig_caption("ch4", "fig:runtime-scaling"))
    d.comment_para(cap44, f"{AUTHOR} {TODAY}: Figure 4.4 caption updated (N = {ic(N['pool_N'])}; pool stages add nodes, not edges); the plot is regenerated by the LaTeX build (comments 286, 288).")
    # Chapter 5 remaining sections
    for i, pre, lab in ((2346, "Propagation semantics beyond transfers", "sub:theory-propagation"),
                        (2351, "Multi-construct domain alignment", "sub:theory-construct"),
                        (2356, "Reputation under cheap pseudonyms", "sub:theory-pseudonymity")):
        sec_fill(i, pre, "Heading3", "ch5", lab, f"{AUTHOR} {TODAY}: Theoretical implication rewritten without repeating numbers; GF-PR/five-proxy framing removed (comments 82, 14).")
    sec_fill(2360, "Practical implications and deployment scenarios", "Heading2", "ch5", "sec:practical-implications",
             f"{AUTHOR} {TODAY}: Practical implications introduction aligned with the LaTeX.")
    for i, pre, lab in ((2364, "Transfer-hub and flow monitoring", "sub:deploy-transfer"),
                        (2368, "Authorization-aware and low-latency refresh", "sub:deploy-allowance"),
                        (2371, "Evaluation design and hybrid use", "sub:deploy-hybrid"),
                        (2378, "Industry adoption scenarios", "sub:deploy-industry")):
        sec_fill(i, pre, "Heading3", "ch5", lab, f"{AUTHOR} {TODAY}: Deployment scenario rewritten: runtimes referenced by table, not repeated; GF-PR removed; adoption effects stated as hypotheses (comments 82, 14, 349).")
    sec_fill(2498, "Regulatory and ethical considerations", "Heading2", "ch5", "sec:regulatory-ethics",
             f"{AUTHOR} {TODAY}: Section aligned with the LaTeX (ethics clearance reference placeholder; comment 20).")
    sec_fill(2506, "Threats to validity", "Heading2", "ch5", "sec:threats-validity", f"{AUTHOR} {TODAY}: Threats-to-validity introduction aligned with the LaTeX.")
    for i, pre, lab in ((2510, "Construct validity", "sub:threat-construct"), (2518, "Internal validity", "sub:threat-internal"),
                        (2524, "External validity", "sub:threat-external"), (2531, "Adversarial validity", "sub:threat-adversarial")):
        sec_fill(i, pre, "Heading3", "ch5", lab, f"{AUTHOR} {TODAY}: Threat rewritten for the two-method design: GF-PR overlap removed, expanded pool N = {ic(N['pool_N'])} and its node-only limitation stated (comments 14, 288).")
    sec_fill(2536, "Limitations", "Heading2", "ch5", "sec:limitations",
             f"{AUTHOR} {TODAY}: Limitations aligned with the LaTeX: one window, matched cohort, node-only pool, non-significant within-method contrasts, holdout scope (comments 14, 237, 288).")
    # Chapter 6 closing
    sec_fill(2592, "Closing reflection", "Heading2", "ch6", "sec:closing-reflection",
             f"{AUTHOR} {TODAY}: Closing reflection rewritten without restating headline numbers; SC1/SRQ1 removed (comments 82, 14).")
    # Appendix
    sec_fill(2744, "Credit-delegation extract (deferred)", "Heading3", "app", "sec:delegation-deferred", f"{AUTHOR} {TODAY}: Aligned with the LaTeX.")
    table_section(2748, "Supplementary alignment summary table", "Heading3", "app", "sec:supplementary-summary", "Table 8.2:", "8.2",
                  f"{AUTHOR} {TODAY}: Supplementary summary text aligned with the LaTeX (withdrawn families named; rows shared with Table 4.7).",
                  f"{AUTHOR} {TODAY}: Table 8.2 regenerated as the two-method six-family summary (GF-PR row removed) (comment 14).")
    sec_fill(2898, "Complexity notes", "Heading3", "appb", "sec:complexity-notes", f"{AUTHOR} {TODAY}: Complexity note aligned with the LaTeX (edge counts referenced by table).")
    sec_fill(2903, "Interpretation checklist for readers", "Heading3", "appb", "sec:interpretation-checklist",
             f"{AUTHOR} {TODAY}: Checklist rewritten for the two-method design with intervals (GF-PR items removed) (comments 14, 128).")
    sec_fill(2914, "Archived extended baselines", "Heading3", "appb", "sec:archived-baselines", f"{AUTHOR} {TODAY}: Aligned with the LaTeX.")
    sec_fill(2918, "Limitations reprise", "Heading3", "appb", "sec:limitations-reprise", f"{AUTHOR} {TODAY}: Aligned with the LaTeX (N = {ic(N['pool_N'])}).")
    sec_fill(2939, "Sparsity and per-iteration cost", "Heading3", "appc", "sec:pr-sparsity", f"{AUTHOR} {TODAY}: Speed-up referenced by table instead of restated (comment 82).")
    sec_fill(2947, "Properties of Kendall", "Heading3", "appc", "sec:kendall-properties", f"{AUTHOR} {TODAY}: Aligned with the LaTeX (no interpretation bands; AWP as Do, Do and Nguyen [3]) (comments 128, 396).")
    sec_fill(2954, "Construct validity note", "Heading3", "appc", "sec:construct-validity-note", f"{AUTHOR} {TODAY}: Construct-validity note aligned with the LaTeX (GF-PR/SRQ1 removed) (comment 14).")
    sec_fill(2958, "Numerical summary sheet", "Heading3", "appc", "sec:numerical-summary-sheet",
             f"{AUTHOR} {TODAY}: The numerical summary sheet is replaced by a pointer list to the tables that report each primary quantity, so that no headline number is repeated (comment 82).",
             drop_tables=True)
    p_mat = d.find_after("These matrices motivate future work", 3086)
    d.set_para(p_mat, "These matrices motivate future work on credit-delegation edges and cross-protocol lending labels, but they do not alter Claims C1–C4.")
    d.comment_para(p_mat, f"{AUTHOR} {TODAY}: SC1 reference removed (supplementary claim withdrawn with GF-PR) (comment 14).")
    sec_fill(3151, "Why the main narrative uses three methods", "Heading3", "appd", "sec:why-archived",
             f"{AUTHOR} {TODAY}: Heading and text updated: the main narrative uses two methods (GF-PR withdrawn) (comment 14).")
    sec_fill(3178, "Decision log", "Heading3", "appd", "sec:archive-decision-log", f"{AUTHOR} {TODAY}: Decision log aligned with the LaTeX (comment 14).")


# --------------------------------------------------------------------------- global passes
NUMBER_REPL = [
    ("18.711 s", "11.253 s"), ("2.105 s", "1.426 s"), ("18.711", "11.253"), ("2.105", "1.426"),
    ("8.9×", "7.9×"), ("31,612", "99,080"), ("31612", "99080"), ("10.4×", "10.5×"), ("9.4×", "7.9×"),
    ("12.28 s", "1.37 s"), ("1.18 s", "0.13 s"), ("21.40 s", "11.25 s"), ("2.29 s", "1.43 s"),
    ("3 repeats", "5 timed repeats"), ("three-run averages", "five-timed-run averages"),
]


def global_passes(d: Doc, N: dict, ref_paras: list) -> dict:
    stats = {"bold_runs": 0, "number_repl": {}, "awp_reattr": 0}
    ref_set = set(id(p) for p in ref_paras)
    for p in d.body.iter(qn("w:p")):
        if id(p) in ref_set:
            continue
        st = pstyle(p)
        in_cell = p.getparent() is not d.body and localname(p.getparent()) == "tc"
        if st in ("BodyText", "ListParagraph") and not in_cell:
            for r in p.iter(qn("w:r")):
                rp = r.find(qn("w:rPr"))
                if rp is None:
                    continue
                for tag in ("w:b", "w:bCs"):
                    for b in rp.findall(qn(tag)):
                        rp.remove(b)
                        stats["bold_runs"] += 1
    for p in d.body.iter(qn("w:p")):
        if id(p) in ref_set:
            continue
        for old, new in NUMBER_REPL:
            n = replace_in_para(p, old, new)
            if n:
                stats["number_repl"][old] = stats["number_repl"].get(old, 0) + n
    return stats


def toc_pass(d: Doc) -> dict:
    """Bring the static table of contents (PDF-export text) in line with renamed, removed and inserted headings."""
    stats = {"renamed": 0, "removed": 0, "inserted": 0, "missing": []}
    rename_map = {}
    for old, new in d.renames:
        rename_map[old] = new
        # chains: A -> B, then B -> C
        for k, v in list(rename_map.items()):
            if norm(v) == old:
                rename_map[k] = new

    def toc_paras():
        return [p for p in d.body.iter(qn("w:p")) if pstyle(p).startswith("TOC") and para_text(p).strip()]

    def split(p):
        m = re.match(r"^(.*?)(\d+)?\s*$", para_text(p).strip(), flags=re.S)
        return m.group(1).strip(), (m.group(2) or "")

    def loose(s: str) -> str:
        # the PDF-export TOC drops some punctuation ("vs AWP" for "vs. AWP"); compare without it
        return re.sub(r"[^a-z0-9]+", "", norm(s).lower())

    rename_loose = {loose(k): v for k, v in rename_map.items()}
    deleted = {loose(x) for x in d.deleted_headings} - {loose(v) for v in rename_map.values()}
    for p in toc_paras():
        title, page = split(p)
        nt = norm(title)
        lt = loose(title)
        if lt in rename_loose and loose(rename_loose[lt]) != lt:
            d.set_para(p, rename_loose[lt] + page)
            stats["renamed"] += 1
        elif lt in deleted:
            # keep any bookmarks (hyperlink anchors) alive by moving them to the previous TOC line,
            # so the entry can be removed instead of leaving a blank line
            prev = p.getprevious()
            if prev is not None and localname(prev) == "p":
                for bm in [e for e in p.iter() if localname(e) in ("bookmarkStart", "bookmarkEnd")]:
                    prev.append(bm)
            d.delete_or_clear(p)
            stats["removed"] += 1
    def find_toc(nt: str):
        """TOC line for a heading: exact title first; otherwise the PDF-export TOC may abbreviate a
        heading ("Practical implications" for "Practical implications and deployment scenarios"),
        so accept a TOC title that is a long prefix of the heading."""
        cands = {loose(nt), loose(rename_map.get(nt, ""))}
        cands.discard("")
        lines = [(p, loose(split(p)[0])) for p in toc_paras()]
        for p, t in lines:
            if t in cands:
                return p
        for p, t in lines:
            if len(t) >= 12 and any(c.startswith(t) for c in cands):
                return p
        return None

    stats["skipped_level"] = 0
    for prevs, text, kind in d.inserted_headings:
        hit = None
        if kind == "h2":
            # place after the enclosing Heading2 entry and after any of its level-3 entries
            enclosing = [n for n, st in prevs if st in ("Heading1", "Heading2")]
            hit = find_toc(enclosing[0]) if enclosing else None
            if hit is not None:
                while hit.getnext() is not None and pstyle(hit.getnext()) == "TOC7":
                    hit = hit.getnext()
        else:
            for n, st in prevs:
                if st == "Heading3":
                    hit = find_toc(n)
                    if hit is not None:
                        break
            if hit is None:
                enclosing = [n for n, st in prevs if st in ("Heading1", "Heading2")]
                h2 = find_toc(enclosing[0]) if enclosing else None
                if h2 is not None and (h2.getnext() is None or pstyle(h2.getnext()) != "TOC7"):
                    stats["skipped_level"] += 1  # this chapter is listed to level 2 only
                    continue
                hit = h2
        if hit is None:
            stats["missing"].append(text)
            continue
        st = pstyle(hit)
        if kind == "h2":
            style = "TOC6" if st in ("TOC3", "TOC6") else "TOC4"
        else:
            style = "TOC7"
        like = next((q for q in toc_paras() if pstyle(q) == style), hit)
        d.insert_after(hit, text, "p", like=like)
        stats["inserted"] += 1
    return stats


def replace_in_para(p, old: str, new: str) -> int:
    """Replace `old` by `new` in a paragraph even when the match spans several runs (PDF-export text)."""
    count = 0
    while True:
        ts = [t for t in p.iter(qn("w:t")) if t.text]
        full = "".join(t.text for t in ts)
        k = full.find(old)
        if k < 0:
            return count
        end = k + len(old)
        off = 0
        first = True
        for t in ts:
            a, b = off, off + len(t.text)
            off = b
            if b <= k or a >= end:
                continue
            lo, hi = max(k, a) - a, min(end, b) - a
            if first:
                t.text = t.text[:lo] + new + t.text[hi:]
                first = False
            else:
                t.text = t.text[:lo] + t.text[hi:]
                if t.text == "" and t.getparent() is not None:
                    t.text = ""
        count += 1


def leftover_scan(d: Doc) -> list[str]:
    pat = re.compile(r"2\.105|18\.711|8\.9×|31,?612|10\.4×|9\.4×|12\.28 s|1\.18 s|21\.40 s|2\.29 s|SRQ1|SC1\b|0\.583|three repeats|3 repeats|five independent|2\.913|21\.383")
    out = []
    for i, p in enumerate(d.body.iter(qn("w:p")), 1):
        t = para_text(p)
        m = pat.search(t)
        if m:
            out.append(f"{i:5d} {m.group(0)!r}: {t[:110]}")
    return out


# --------------------------------------------------------------------------- references
def load_mapping() -> tuple[dict, set]:
    old_to_new, dropped = {}, set()
    for line in MAPPING.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = re.split(r"[\s\t,>-]+", line)
        parts = [p for p in parts if p]
        if len(parts) >= 2 and parts[1].upper().startswith("DROP"):
            dropped.add(int(parts[0]))
        elif len(parts) >= 2 and parts[0].isdigit() and parts[1].isdigit():
            old_to_new[int(parts[0])] = int(parts[1])
    return old_to_new, dropped


def load_new_refs() -> dict[int, str]:
    src = tex_source("refs")
    out = {}
    for m in re.finditer(r"\\item\\phantomsection\\label\{ref:(\d+)\}\s*(.*?)(?=\n\s*\\item|\n\\end\{enumerate\})", src, flags=re.S):
        out[int(m.group(1))] = delatex(" ".join(m.group(2).split()))
    return out


CITE_RUN_RE = re.compile(r"^\[(\d+)\](?:,\[(\d+)\])*$")


def collect_cite_runs(d: Doc, ref_paras: list) -> list:
    ref_set = set(id(p) for p in ref_paras)
    runs = []
    for p in d.body.iter(qn("w:p")):
        if id(p) in ref_set:
            continue
        for r in p.iter(qn("w:r")):
            txt = "".join(t.text or "" for t in r.findall(qn("w:t")))
            if CITE_RUN_RE.match(txt):
                runs.append(r)
    return runs


def is_attached(el, root) -> bool:
    while el is not None:
        if el is root:
            return True
        el = el.getparent()
    return False


AWP_CTX = re.compile(r"AWP|Adaptive Weighted|logistic|time-decay|transfer-graph baseline|Do et al", re.I)


def renumber_references(d: Doc, old_runs: list, ref_heading, ref_paras: list) -> dict:
    old_to_new, dropped = load_mapping()
    new_refs = load_new_refs()
    n_new = max(new_refs)
    assert len(ref_paras) == 63, len(ref_paras)
    # which old numbers are still cited after the edits (runs still attached, not created by us)
    cited_old: dict[int, list] = {}
    for r in old_runs:
        if id(r) in NEW_CITE_RUNS or not is_attached(r, d.body):
            continue
        txt = "".join(t.text or "" for t in r.findall(qn("w:t")))
        for n in map(int, re.findall(r"\d+", txt)):
            cited_old.setdefault(n, []).append(r)
    tail = []
    for n in sorted(cited_old):
        if n not in old_to_new:
            tail.append(n)
    tail_map = {}
    nxt = n_new + 1
    for n in tail:
        tail_map[n] = nxt
        nxt += 1
    full = dict(old_to_new)
    full.update(tail_map)
    # rewrite citation runs
    reattr = 0
    for r in old_runs:
        if id(r) in NEW_CITE_RUNS or not is_attached(r, d.body):
            continue
        para = r.getparent()
        while para is not None and localname(para) != "p":
            para = para.getparent()
        ctx = para_text(para) if para is not None else ""
        parts = []
        txt = "".join(t.text or "" for t in r.findall(qn("w:t")))
        for n in map(int, re.findall(r"\d+", txt)):
            nn = full[n]
            if n == 16 and AWP_CTX.search(ctx) and "HodgeRank" not in ctx:
                nn = 3
                reattr += 1
            parts.append(f"[{nn}]")
        ts = r.findall(qn("w:t"))
        ts[0].text = ",".join(parts)
        for extra in ts[1:]:
            r.remove(extra)
    # rebuild list
    inv = {new: old for old, new in old_to_new.items()}
    template = ref_paras[0]
    parent = ref_paras[0].getparent()
    insert_after = ref_paras[0].getprevious()
    for p in ref_paras:
        parent.remove(p)
    created, moved, removed = 0, 0, 0
    ordered = []
    for k in range(1, n_new + 1):
        if k in inv and inv[k] <= len(ref_paras):  # old numbers > 63 were interim LaTeX-only entries
            ordered.append(ref_paras[inv[k] - 1])
            moved += 1
        else:
            p = deepcopy(template)
            for e in list(p.iter()):
                if localname(e) in ("bookmarkStart", "bookmarkEnd", "commentRangeStart", "commentRangeEnd"):
                    e.getparent().remove(e)
            d.set_para(p, new_refs[k])
            ordered.append(p)
            created += 1
    for n in tail:
        ordered.append(ref_paras[n - 1])
    for n in dropped:
        if n not in tail_map:
            removed += 1
    cur = insert_after
    for p in ordered:
        cur.addnext(p)
        cur = p
    # verify: every cited number exists, count uncited
    cited_new = set()
    for p in d.body.iter(qn("w:p")):
        if any(p is q for q in ordered):
            continue
        for m in re.finditer(r"\[(\d+)\]", para_text(p)):
            cited_new.add(int(m.group(1)))
    total = len(ordered)
    over = [n for n in cited_new if n > total]
    uncited = [n for n in range(1, total + 1) if n not in cited_new]
    d.comment_span(ordered[0], ordered[-1],
                   f"{AUTHOR} {TODAY}: References renumbered in order of first appearance (LaTeX mapping): {moved} entries reordered, {created} sources from "
                   f"2020-2026 added, {removed} uncited entries removed; {len(tail)} entries still cited only in unrevised passages kept at the end "
                   f"(nos. {n_new + 1}-{total}). Citations [n] in the body were rewritten accordingly; AWP citations re-attributed from Do and Do to "
                   f"Do, Do and Nguyen [3] in {reattr} places (comments 396, 2, 20).")
    return {"moved": moved, "created": created, "removed": removed, "tail": tail_map, "over": over, "uncited": uncited, "reattr": reattr, "total": total}


# --------------------------------------------------------------------------- replies (Word COM)
def replies(N: dict) -> dict[int, str]:
    fam = N["fam"]
    td = {r["label"]: r for r in N["tau_diff"]}
    d1 = td["EndorseRank allowance minus EndorseRank transfer"]
    d3 = td["EndorseRank allowance minus AWP allowance"]
    r10k = N["tier2_rows"][0]
    dr = {round(r["damping"], 2): r for r in N["damping_rows"]}
    return {
        1: f"Rewritten ({TODAY}). The abstract now gives the background, the identified problem, the design (matched cohort n = 5,521, Kendall's tau with a paired bootstrap, temporal holdout, one timing protocol), the numerical results with intervals, the benchmark against AWP, and the methodological, practical and societal significance. Same text as en/01-Intro/02-Abstract.tex.",
        3: "Citations removed from the abstract; the baseline is named in prose (Do, Do and Nguyen, 2023) and cited in Chapter 1.",
        6: "Bold removed here and in all body text (BodyText/ListParagraph runs). Only headings and table headers keep bold, as agreed at the 2026-09-09 meeting.",
        2: "Corrected. AWP is now attributed to Do, Do and Nguyen (2023, IEEE RIVF, doi:10.1109/RIVF60135.2023.10471809), which defines the value-weighted, logistically time-decayed transfer PageRank and the in-degree/in-value validation; Do and Do (2023, IJSI) is cited separately as the earlier PageRank/HodgeRank study. Re-attributed in the abstract, Chapters 1-3, 5-6 and the reference list (now [3] and [4]).",
        7: "Sentence removed. GF-PR, SRQ1 and SC1 are withdrawn from the main narrative (see the reply under the Abbreviations comment); the supplementary analysis was the candidate's own and now lives only in the archived appendix.",
        14: "Agreed. GF-PR, SRQ1 and SC1 are withdrawn: removed from Abbreviations, Chapter 1 (Table 1.2, RQ/claim table), Chapter 2 (one caveat paragraph 'What this research does not claim' states the circularity), Chapter 3, Chapter 4 (Table 4.2 row; Section 4.7 replaced by the temporal holdout), Chapters 5-6 and the claim map. Inverse-risk, liquidation and trading-success families are marked as archived. The matrices remain in the appendix archive for completeness only.",
        20: "Clusters split. Each sentence now carries the single source that supports it (Chapter 1 opening: [1], [2], [3], [4] individually); the same was done in 18 places of Chapter 2. References were renumbered in order of first appearance and uncited entries removed.",
        62: f"Demoted. The Motivation states that the gap is an expected consequence of graph sparsity under latest-allowance snapshots with an identical solver, not an algorithmic contribution; C1 is reported as an operational property and efficiency is no longer counted among the contributions. Runtimes are stated once (Table 4.2: {f3(N['er_rt'])} s vs {f3(N['awp_rt'])} s, |E| {ic(N['er_E'])} vs {ic(N['awp_E'])}).",
        72: "Added Section 'Research objectives' (O1-O4, each with a measurement and a criterion, mapped one-to-one to RQ1-RQ4) before the research questions, and Section 'Achievement of the research objectives' in Chapter 5 (Table 5.1) judging each objective against the evidence.",
        74: "RQ4 re-posed. It is now a temporal holdout: scores frozen at 28 February 2026 are tested against new owner-spender approvals in March-May 2026 on the spender cohort (n = 1,335), compared with AWP and with the same-window allowance check (Table 4.13). The RQ2 text states that same-window own-construct agreement is a construct-validity observation, not external validation.",
        77: "Contributions rewritten as three: (1) the latest-allowance edge construct, (2) a same-cohort comparison with bootstrap intervals and paired difference tests, (3) the temporal holdout of future new approvals. The text states that the originality lies in the construct, the inference design and the out-of-window test, not in the solver, and the new Research gap section (Chapter 2) shows that no reviewed method uses the allowance edge.",
        78: f"The contribution was restructured (see the reply above) and strengthened empirically: 95% intervals on every coefficient, six pre-specified difference tests, and a temporal holdout in which EndorseRank predicts future new approvals (tau 0.479 [0.426, 0.529]) while AWP does not (0.044, interval includes 0). A two-page plan for further methodological development will be submitted separately.",
        81: f"Added to Chapter 3, Reproducibility: public repository {REPO_URL}, commit {COMMIT}, versioned configuration config/margin_config.yaml and the machine-readable summary data/processed/eval_summary.json from which every table is exported. The pipeline is no longer listed as a contribution.",
        82: "Headline numbers are now stated once in Chapter 4 and referred to by table thereafter; they were removed from the Chapter 1 contributions, Chapter 5 and Chapter 6 (the abstract keeps them, as requested in the abstract comment).",
        129: f"Bands removed. Coefficients are reported with 95% percentile bootstrap intervals ({N['n_boot']} paired resamples, seed {N['seed']}; Table 4.15) and compared with paired-difference intervals (Table 4.14); no threshold is used.",
        128: "Bands deleted rather than referenced; see the reply to the adjacent comment.",
        237: f"Added. Every tau in Chapter 4 carries a 95% paired-bootstrap interval (Table 4.15 and the per-proxy tables), and six pre-specified differences are tested with the same resamples (Table 4.14): e.g. ER allowance minus ER transfer = {d1['delta_tau']:+.3f} {ci(d1['ci_low'], d1['ci_high'])} (not significant); ER allowance minus AWP allowance = {d3['delta_tau']:+.3f} {ci(d3['ci_low'], d3['ci_high'])}. The text no longer calls one tau larger than another unless the interval of the difference excludes zero.",
        240: f"Unified. All timings use one protocol: one untimed warm-up, {N['repeats']} timed solves, and per-session memoisation so that the same graph yields the same numbers wherever it is tabulated (Table 4.2, Table 4.4 d = 0.85 row, Table 8.1 n = 5,521 row, Table 4.3 full pool). Every '3 repeats' / 'three-run' wording was replaced.",
        264: "Wording made definite: the study was reviewed and the certificate is reproduced in Appendix 8.6. The certificate reference number and date are still to be inserted from the issued certificate (placeholder 'TBD' kept deliberately rather than invented).",
        283: f"Explained and fixed. The three figures came from separate timing sessions with different warm-up states. All benchmarks were re-run under one protocol (one warm-up, {N['repeats']} timed solves, memoised per graph): Table 4.2, Table 4.4 (d = 0.85) and Table 8.1 (n = 5,521) now report the identical {f3(N['er_rt'])} s / {f3(N['awp_rt'])} s ({N['speedup']:.1f}x). Table 8.4 belongs to the archived seven-method preset.",
        286: f"Reconciled. Table 4.3 and Table 4.6 are now produced from the same memoised measurement and agree (n = 10,000: {f3(r10k['endorserank']['runtime_sec_mean'])} s vs {f3(r10k['awp']['runtime_sec_mean'])} s, {r10k['er_speedup_ratio']:.1f}x). Per-run timings are retained in eval_summary.json (runtime_sec_runs).",
        288: f"Corrected and re-framed. Per-stage |V| and |E| are now reported for both methods (Tables 4.3 and 8.1). The {ic(N['pool_supp'])} supplemental pool addresses have no extracted edges (the second-tier extraction did not complete), so the pool stages vary node count only; the text calls this node-count sensitivity, not scaling, and lists edge growth as future work.",
        299: "Re-framed as 'sample-definition sensitivity'. The matched cohort (n = 5,521) is the primary sample and is presented with intervals; the expanded-pool rows are described as a different population whose decimal values are not comparable, and the text no longer calls the swing robustness.",
        310: f"Confronted directly. The allowance section now says that EndorseRank-allowance agreement is expected because the score is a global smoothing of allowance in-degree, that it is an intended-construct check rather than external validation, and that the within-method difference against transfer is not significant (delta tau {d1['delta_tau']:+.3f}, interval includes 0). Trading-success and inverse-risk families are withdrawn from the main narrative.",
        349: "Cut to a single paragraph without the finance-theory citation cluster (Chapter 5, 'Standardised scores as shared infrastructure'); the removed references were dropped from the list.",
        378: "Addressed in this revision: attribution fixed, GF-PR withdrawn, intervals and difference tests added, timings unified, repeated numbers removed, objectives added, bold removed, references renumbered and updated. The separate memo (Supervisory_Review_Taehong_Thesis) was not received; a two-page contribution plan and the Turnitin/Overleaf submission follow separately.",
        396: "Updated: 17 uncited or superseded entries removed and 17 sources from 2020-2026 added (DeFi SoKs 2022-2023, Layer-2 rollups 2024, MEV 2023, decentralized credit scoring 2024, wash trading 2022-2023, etc.). References are numbered in order of first appearance (63 entries; entries cited only in unrevised passages are appended at the end).",
    }


def word_reply_pass(path: Path, texts: dict[int, str], parent_texts: dict[int, str]) -> int:
    import pythoncom  # type: ignore
    import win32com.client  # type: ignore

    pythoncom.CoInitialize()
    word = win32com.client.DispatchEx("Word.Application")
    word.Visible = False
    word.DisplayAlerts = 0
    added = 0
    try:
        word.UserName = AUTHOR
        word.UserInitials = INITIALS
        doc = word.Documents.Open(str(path), ConfirmConversions=False, ReadOnly=False, AddToRecentFiles=False)
        try:
            i = 0
            while True:
                i += 1
                if i > doc.Comments.Count:  # replies join the collection, so re-read the count every step
                    break
                c = doc.Comments(i)
                try:
                    if c.Ancestor is not None:
                        continue
                except Exception:
                    pass
                if c.Author == AUTHOR:
                    continue
                if c.Replies.Count > 0:
                    continue
                key = norm(c.Range.Text)[:60]
                cid = None
                for k, t in parent_texts.items():
                    if norm(t)[:60] == key:
                        cid = k
                        break
                if cid is None or cid not in texts:
                    log(f"  [warn] no reply text for Word comment #{i} ({key[:40]!r})")
                    continue
                c.Replies.Add(c.Range, texts[cid])
                added += 1
            doc.Save()
        finally:
            doc.Close(SaveChanges=0)
    finally:
        word.Quit()
        pythoncom.CoUninitialize()
    return added


def force_authors(path: Path) -> tuple[int, int]:
    """After Word saved: make sure every non-supervisor comment is authored by AUTHOR/INITIALS."""
    with zipfile.ZipFile(path) as z:
        parts = {n: z.read(n) for n in z.namelist()}
        infos = z.infolist()
    root = etree.fromstring(parts["word/comments.xml"])
    fixed, total = 0, 0
    for c in root.iter(qn("w:comment")):
        total += 1
        a = c.get(qn("w:author")) or ""
        if a.startswith("Moulla") or a.startswith("Attipoe") or a.startswith("Dr. David"):
            continue
        if a != AUTHOR or c.get(qn("w:initials")) != INITIALS:
            c.set(qn("w:author"), AUTHOR)
            c.set(qn("w:initials"), INITIALS)
            fixed += 1
    people = etree.fromstring(parts["word/people.xml"])
    if not any(p.get(qn("w15:author")) == AUTHOR for p in people.iter(qn("w15:person"))):
        etree.SubElement(people, qn("w15:person")).set(qn("w15:author"), AUTHOR)
    parts["word/comments.xml"] = etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)
    parts["word/people.xml"] = etree.tostring(people, xml_declaration=True, encoding="UTF-8", standalone=True)
    tmp = path.with_name(path.name + ".__tmp")
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
        for info in infos:
            zout.writestr(info, parts[info.filename])
    shutil.move(str(tmp), str(path))
    return fixed, total


def verify(path: Path) -> dict:
    out = {}
    with zipfile.ZipFile(path) as z:
        out["testzip"] = z.testzip()
        docxml = z.read("word/document.xml")
        out["ns0"] = b"ns0:" in docxml
        etree.fromstring(docxml)
        out["has_w_document"] = b"<w:document" in docxml
        comments = etree.fromstring(z.read("word/comments.xml"))
        authors = {}
        for c in comments.iter(qn("w:comment")):
            authors[c.get(qn("w:author"))] = authors.get(c.get(qn("w:author")), 0) + 1
        out["authors"] = authors
        ex = etree.fromstring(z.read("word/commentsExtended.xml"))
        out["threads_with_parent"] = sum(1 for e in ex.iter(qn("w15:commentEx")) if e.get(qn("w15:paraIdParent")))
    return out


def update_readme() -> None:
    txt = README.read_text(encoding="utf-8")
    new = txt.replace(
        "| Moulla·Attipoe Word 코멘트가 달린 초안 (읽기 전용 원본) |",
        "| Moulla·Attipoe Word 코멘트가 달린 초안의 **2026-09 수정본** (git `ffae93c`가 리뷰 원본). `_apply_review_fixes.py`가 LaTeX 수정을 제자리 반영; 수정 부위마다 Taehong Kwon 코멘트, 27개 리뷰 코멘트마다 Taehong Kwon 답글 |",
    )
    new = new.replace(
        "원본 리뷰 DOCX는 덮어쓰지 않는다.",
        "리뷰 원본 DOCX는 git `ffae93c`에 있고, 현재 파일은 2026-09 수정본이다(`_apply_review_fixes.py`, `en/` LaTeX와 동일 문안).",
    )
    new = new.replace(
        "3. 정본 수정은 `2-Dissertation-Draft/en/` LaTeX에 한다. 작업본과 LaTeX는 일시적으로 어긋난다.",
        "3. 정본 수정은 `2-Dissertation-Draft/en/` LaTeX에 한다. DOCX 수정본은 `_apply_review_fixes.py`로 LaTeX에서 다시 생성한다(git `ffae93c` 원본을 입력으로).",
    )
    if new != txt:
        README.write_text(new, encoding="utf-8")
        log("README.md updated")


# --------------------------------------------------------------------------- main
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=None, help="write to this path instead of editing in place")
    ap.add_argument("--no-word", action="store_true")
    ap.add_argument("--log", type=Path, default=None)
    args = ap.parse_args()
    random.seed(20260912)
    global LABELS
    LABELS = load_labels()
    N = load_numbers()
    out = args.out or DOCX

    d = Doc(DOCX)
    log(f"loaded {DOCX.name}: {len(d.paras)} paragraphs, {d.next_cid - 1} max comment id")
    # reference list paragraphs (before any edit)
    ref_heading = d.heading("References", level="Heading1")
    ref_paras = []
    el = ref_heading.getnext()
    while el is not None and not (localname(el) == "p" and pstyle(el).startswith("Heading")):
        if localname(el) == "p" and pstyle(el) == "ListParagraph" and para_text(el).strip():
            ref_paras.append(el)
        el = el.getnext()
    log(f"reference entries found: {len(ref_paras)}")
    old_runs = collect_cite_runs(d, ref_paras)
    log(f"citation runs found: {len(old_runs)}")

    apply_edits(d, N)
    log(f"edits applied: {d.edit_count} paragraph operations, {len(d.new_comments)} TK comments so far")
    stats = global_passes(d, N, ref_paras)
    log(f"bold runs stripped: {stats['bold_runs']}; number replacements: {stats['number_repl']}")
    d.comment_para(d.heading("Abstract", level="Heading1"),
                   f"{AUTHOR} {TODAY}: Document-wide changes: bold removed from {stats['bold_runs']} body-text runs (headings and table headers keep bold; "
                   f"meeting 2026-09-09, comment 6); remaining old headline numbers replaced by the {TODAY} re-run values "
                   f"({', '.join(f'{k}->{v2}' for (k, v2) in NUMBER_REPL if k in stats['number_repl'])}); citations renumbered by first appearance. "
                   f"Table/section numbers in new text follow the revised LaTeX numbering. Unrevised passages that still mention archived material are marked as such.")
    ref_stats = renumber_references(d, old_runs, ref_heading, ref_paras)
    log(f"references: {ref_stats}")
    toc_stats = toc_pass(d)
    log(f"toc: {toc_stats}")
    h_toc = d.heading("Table of Contents", level="Heading1")
    d.comment_para(h_toc, f"{AUTHOR} {TODAY}: The table of contents, list of figures and list of tables are static text from the PDF export. "
                          f"TOC entries were renamed ({toc_stats['renamed']}), removed ({toc_stats['removed']}) and added ({toc_stats['inserted']}, without page numbers) "
                          f"to match the revised headings; page numbers are those of the reviewed PDF. Lists of figures/tables were not edited beyond number "
                          f"replacements. All three must be regenerated from the LaTeX build before submission.")
    left = leftover_scan(d)
    log(f"leftover old tokens: {len(left)}")
    for ln in left:
        log("   " + ln)
    if UNRESOLVED:
        log(f"unresolved LaTeX: {sorted(UNRESOLVED)}")
    d.save(out)
    log(f"saved {out}")
    log(f"TK comments (XML): {len(d.new_comments)}")

    if not args.no_word:
        import importlib.util
        spec = importlib.util.spec_from_file_location("_brd", HERE / "_build_replied_docx.py")
        brd = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(brd)  # for the parent-comment texts (id -> text)
        parent_texts = {}
        with zipfile.ZipFile(out) as z:
            croot = etree.fromstring(z.read("word/comments.xml"))
        for c in croot.iter(qn("w:comment")):
            a = c.get(qn("w:author")) or ""
            if a != AUTHOR:
                parent_texts[int(c.get(qn("w:id")))] = "".join(t.text or "" for t in c.iter(qn("w:t")))
        added = word_reply_pass(out, replies(N), parent_texts)
        log(f"Word replies added: {added}")
        fixed, total = force_authors(out)
        log(f"authors forced: {fixed} of {total} comments")
    v = verify(out)
    log(f"verify: {v}")
    if out == DOCX:
        update_readme()
    if args.log:
        args.log.write_text("\n".join(LOG), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
