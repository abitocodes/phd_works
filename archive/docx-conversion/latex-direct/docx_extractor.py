"""Extract structured blocks from docx for comparison and conversion."""

from __future__ import annotations

import re
import zipfile
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

from lxml import etree

from numbering_engine import NumberingEngine, split_toc_page_suffix

NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "m": "http://schemas.openxmlformats.org/officeDocument/2006/math",
}
W = f"{{{NS['w']}}}"


STYLE_NAMES = {
    "1": "heading 1",
    "2": "heading 2",
    "ad": "caption",
    "ac": "List Paragraph",
}


@dataclass
class DocxBlock:
    index: int
    kind: str
    text: str
    plain_text: str
    style_id: str
    style_name: str
    num_id: str
    ilvl: int | None
    label: str
    page_ref: str | None
    bold: bool
    align: str
    max_size: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _local_name(el: etree._Element) -> str:
    return etree.QName(el).localname if isinstance(el.tag, str) else ""


def _child_text(el: etree._Element) -> str:
    return "".join(el.xpath(".//w:t/text() | .//m:t/text()", namespaces=NS)).strip()


def _para_style(p: etree._Element) -> str:
    vals = p.xpath("./w:pPr/w:pStyle/@w:val", namespaces=NS)
    return vals[0] if vals else ""


def _get_num(p: etree._Element) -> tuple[str, int] | None:
    num_id = p.xpath("./w:pPr/w:numPr/w:numId/@w:val", namespaces=NS)
    if not num_id:
        return None
    ilvl = p.xpath("./w:pPr/w:numPr/w:ilvl/@w:val", namespaces=NS)
    return num_id[0], int(ilvl[0]) if ilvl else 0


def _alignment(p: etree._Element) -> str:
    vals = p.xpath("./w:pPr/w:jc/@w:val", namespaces=NS)
    return vals[0] if vals else ""


def _max_size(p: etree._Element) -> int:
    sizes = []
    for value in p.xpath(".//w:rPr/w:sz/@w:val", namespaces=NS):
        try:
            sizes.append(int(value))
        except ValueError:
            pass
    return max(sizes) if sizes else 0


def _has_bold(p: etree._Element) -> bool:
    return bool(p.xpath(".//w:rPr/w:b[not(@w:val='0') and not(@w:val='false')]", namespaces=NS))


def _classify_role(
    text: str,
    style: str,
    num: tuple[str, int] | None,
    bold: bool,
    max_size: int,
    in_toc: bool,
    kind: str,
) -> str:
    if kind == "table":
        return "table"
    if text == "Table of Contents":
        return "toc_title"
    if in_toc and num and num[0] == "44":
        return "toc_entry"
    if is_outline_level0(text, style, num, bold, max_size):
        return "section"
    if is_outline_level1(text, style, num):
        return "subsection"
    if style == "1" and num and num[0] in {"32", "22"}:
        return "subsection"
    if style == "2" and num and num[0] in {"31", "19", "18", "17", "20", "21"} and num[1] == 0:
        return "subsection"
    if style == "ad" or re.match(r"^Table\s+\d+\s*:", text):
        return "caption"
    if bold and max_size >= 40 and len(text) <= 80 and not num:
        return "section"
    if style == "2" and num and num[0] != "45":
        return "subsection"
    if num is not None:
        return "list_item"
    return "body"


def is_outline_level0(text: str, style: str, num: tuple[str, int] | None, bold: bool, max_size: int) -> bool:
    if not text or num is not None:
        return False
    return bold and max_size >= 40 and len(text) <= 80


def is_outline_level1(text: str, style: str, num: tuple[str, int] | None) -> bool:
    if not text or num is not None or style != "1":
        return False
    return text not in {"Abstract", "Table of Contents"}


def extract_docx_blocks(docx_path: Path | str) -> list[DocxBlock]:
    docx_path = Path(docx_path)
    engine = NumberingEngine.from_docx(docx_path)
    counters: dict[str, NumberingEngine] = {}
    outline = NumberingEngine.from_docx(docx_path)

    def get_label(num_id: str, ilvl: int, text: str) -> tuple[str, str, str | None]:
        if num_id not in counters:
            counters[num_id] = NumberingEngine.from_docx(docx_path)
        inst = counters[num_id]
        if num_id == "44":
            return inst.label_with_suffix(num_id, ilvl, text)
        label = inst.advance(num_id, ilvl)
        return label, text, None

    def outline_label(ilvl: int) -> str:
        return outline.advance("44", ilvl)

    blocks: list[DocxBlock] = []
    in_toc = False

    with zipfile.ZipFile(docx_path) as zf:
        document = etree.fromstring(zf.read("word/document.xml"))
        body = document.xpath("./w:body/*", namespaces=NS)

        for index, el in enumerate(body):
            tag = _local_name(el)
            if tag == "sectPr":
                continue
            if tag == "tbl":
                blocks.append(
                    DocxBlock(
                        index=index,
                        kind="table",
                        text="[table]",
                        plain_text="[table]",
                        style_id="",
                        style_name="",
                        num_id="",
                        ilvl=None,
                        label="",
                        page_ref=None,
                        bold=False,
                        align="",
                        max_size=0,
                    )
                )
                continue
            if tag != "p":
                continue

            text = _child_text(el)
            style = _para_style(el)
            num = _get_num(el)
            bold = _has_bold(el)
            max_size = _max_size(el)
            align = _alignment(el)

            if text == "Table of Contents":
                in_toc = True
            elif in_toc and text and not (num and num[0] == "44"):
                in_toc = False
                outline = NumberingEngine.from_docx(docx_path)

            label = ""
            page_ref = None
            plain_text = text
            if not text and num is not None:
                if num[0] == "32" and num[1] == 1:
                    outline.advance("44", 1)
                get_label(num[0], num[1], text)
            elif num is not None:
                if num[0] == "32" and num[1] == 1:
                    outline.advance("44", 1)
                label, plain_text, page_ref = get_label(num[0], num[1], text)
            elif is_outline_level0(text, style, num, bold, max_size):
                label = outline_label(0)
            elif is_outline_level1(text, style, num):
                label = outline_label(1)

            role = _classify_role(text, style, num, bold, max_size, in_toc, "paragraph")
            blocks.append(
                DocxBlock(
                    index=index,
                    kind=role,
                    text=text,
                    plain_text=plain_text,
                    style_id=style,
                    style_name=STYLE_NAMES.get(style, style or "(none)"),
                    num_id=num[0] if num else "",
                    ilvl=num[1] if num else None,
                    label=label,
                    page_ref=page_ref,
                    bold=bold,
                    align=align,
                    max_size=max_size,
                )
            )

    return blocks
