"""Word OOXML numbering.xml counter simulator."""

from __future__ import annotations

import re
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

from lxml import etree

NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
W = f"{{{NS['w']}}}"


@dataclass
class LevelDef:
    fmt: str
    lvl_text: str
    start: int = 1


@dataclass
class NumberingScheme:
    num_id: str
    abstract_id: str
    levels: dict[int, LevelDef] = field(default_factory=dict)


ROMAN_ONES = (
    (1000, "m"),
    (900, "cm"),
    (500, "d"),
    (400, "cd"),
    (100, "c"),
    (90, "xc"),
    (50, "l"),
    (40, "xl"),
    (10, "x"),
    (9, "ix"),
    (5, "v"),
    (4, "iv"),
    (1, "i"),
)


def _attr(el: etree._Element, name: str) -> str | None:
    return el.get(f"{W}{name}")


def _format_counter(value: int, fmt: str) -> str:
    if fmt in {"decimal", "decimalZero"}:
        return str(value).zfill(2) if fmt == "decimalZero" else str(value)
    if fmt == "lowerLetter":
        n = max(1, value)
        result = ""
        while n > 0:
            n, rem = divmod(n - 1, 26)
            result = chr(ord("a") + rem) + result
        return result
    if fmt == "upperLetter":
        return _format_counter(value, "lowerLetter").upper()
    if fmt == "lowerRoman":
        n = max(1, value)
        out = []
        for threshold, numeral in ROMAN_ONES:
            while n >= threshold:
                out.append(numeral)
                n -= threshold
        return "".join(out)
    if fmt == "upperRoman":
        return _format_counter(value, "lowerRoman").upper()
    if fmt == "bullet":
        return ""
    return str(value)


def split_toc_page_suffix(text: str) -> tuple[str, str | None]:
    """Split TOC text like 'Introduction and background1' -> title, page."""
    match = re.match(r"^(.*?)(\d+)$", text)
    if not match:
        return text, None
    title, page = match.group(1), match.group(2)
    if not title:
        return text, None
    return title, page


class NumberingEngine:
    """Simulate Word list counters per numId."""

    def __init__(self, schemes: dict[str, NumberingScheme]) -> None:
        self.schemes = schemes
        self._counters: dict[str, list[int]] = {}

    @classmethod
    def from_docx(cls, docx_path: Path | str) -> "NumberingEngine":
        with zipfile.ZipFile(docx_path) as zf:
            if "word/numbering.xml" not in zf.namelist():
                return cls({})
            root = etree.fromstring(zf.read("word/numbering.xml"))
        abstract: dict[str, dict[int, LevelDef]] = {}
        for absn in root.xpath(".//w:abstractNum", namespaces=NS):
            aid = _attr(absn, "abstractNumId")
            if aid is None:
                continue
            levels: dict[int, LevelDef] = {}
            for lvl in absn.xpath("./w:lvl", namespaces=NS):
                ilvl = int(_attr(lvl, "ilvl") or 0)
                fmt = (lvl.xpath("./w:numFmt/@w:val", namespaces=NS) or ["decimal"])[0]
                lvl_text = (lvl.xpath("./w:lvlText/@w:val", namespaces=NS) or [""])[0]
                start_raw = (lvl.xpath("./w:start/@w:val", namespaces=NS) or ["1"])[0]
                try:
                    start = int(start_raw)
                except ValueError:
                    start = 1
                levels[ilvl] = LevelDef(fmt, lvl_text, start)
            abstract[aid] = levels

        schemes: dict[str, NumberingScheme] = {}
        for num in root.xpath(".//w:num", namespaces=NS):
            num_id = _attr(num, "numId")
            aid = (num.xpath("./w:abstractNumId/@w:val", namespaces=NS) or [None])[0]
            if num_id is None or aid is None:
                continue
            schemes[num_id] = NumberingScheme(num_id, aid, dict(abstract.get(aid, {})))
        return cls(schemes)

    def reset(self, num_id: str) -> None:
        self._counters.pop(num_id, None)

    def _ensure_counters(self, num_id: str) -> list[int]:
        if num_id not in self._counters:
            scheme = self.schemes[num_id]
            self._counters[num_id] = [
                scheme.levels.get(i, LevelDef("decimal", "%1", 1)).start - 1 for i in range(9)
            ]
        return self._counters[num_id]

    def advance(self, num_id: str, ilvl: int) -> str:
        scheme = self.schemes.get(num_id)
        if scheme is None:
            return ""
        counters = self._ensure_counters(num_id)
        level_def = scheme.levels.get(ilvl, LevelDef("decimal", "%1", 1))

        counters[ilvl] += 1
        for deeper in range(ilvl + 1, 9):
            start = scheme.levels.get(deeper, LevelDef("decimal", "%1", 1)).start
            counters[deeper] = start - 1

        return self._format_label(scheme, counters, ilvl)

    def peek(self, num_id: str, ilvl: int) -> str:
        """Preview label without advancing (after hypothetical advance)."""
        scheme = self.schemes.get(num_id)
        if scheme is None:
            return ""
        counters = self._ensure_counters(num_id)
        trial = counters.copy()
        trial[ilvl] += 1
        for deeper in range(ilvl + 1, 9):
            start = scheme.levels.get(deeper, LevelDef("decimal", "%1", 1)).start
            trial[deeper] = start - 1
        return self._format_label(scheme, trial, ilvl)

    def _format_label(self, scheme: NumberingScheme, counters: list[int], ilvl: int) -> str:
        level_def = scheme.levels.get(ilvl, LevelDef("decimal", "%1", 1))
        if level_def.fmt == "bullet":
            bullet = level_def.lvl_text or "•"
            return bullet

        template = level_def.lvl_text or "%1"
        label = template
        for level in range(9):
            placeholder = f"%{level + 1}"
            if placeholder not in label:
                continue
            lvl_def = scheme.levels.get(level, LevelDef("decimal", "%1", 1))
            value = counters[level]
            if value < lvl_def.start:
                value = lvl_def.start
            formatted = _format_counter(value, lvl_def.fmt)
            label = label.replace(placeholder, formatted)
        return label

    def label_with_suffix(self, num_id: str, ilvl: int, text: str) -> tuple[str, str, str | None]:
        """Return (label, clean_title, page_suffix) for TOC entries."""
        label = self.advance(num_id, ilvl)
        if num_id == "44":
            title, page = split_toc_page_suffix(text)
            return label, title, page
        return label, text, None
