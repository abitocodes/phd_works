"""Fix Ethics Considerations list formatting in Proposal-Final docx."""
from __future__ import annotations

import re
import shutil
import zipfile
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree as ET

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
W14 = "http://schemas.microsoft.com/office/word/2010/wordml"
NS = {"w": W, "w14": W14}

ET.register_namespace("w", W)
ET.register_namespace("wpc", "http://schemas.microsoft.com/office/word/2010/wordprocessingCanvas")
ET.register_namespace("mc", "http://schemas.openxmlformats.org/markup-compatibility/2006")
ET.register_namespace("w14", W14)
ET.register_namespace("w15", "http://schemas.microsoft.com/office/word/2012/wordml")
ET.register_namespace("w16", "http://schemas.microsoft.com/office/word/2018/wordml")
ET.register_namespace("w16cex", "http://schemas.microsoft.com/office/word/2018/wordml/cex")
ET.register_namespace("w16cid", "http://schemas.microsoft.com/office/word/2016/wordml/cid")
ET.register_namespace("r", "http://schemas.openxmlformats.org/officeDocument/2006/relationships")

BASE = Path(__file__).resolve().parent
UNPACKED = BASE / "unpacked"
DOC_XML = UNPACKED / "word" / "document.xml"
COMMENTS_XML = UNPACKED / "word" / "comments.xml"
OUT_DOCX = BASE.parent / "Proposal-Final_Taehong Kwon.docx"
AUTHOR = "Taehong Kwon"
COMMENT_DATE = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def para_text(p: ET.Element) -> str:
    parts = []
    for t in p.iter(f"{{{W}}}t"):
        if t.text:
            parts.append(t.text)
        if t.tail:
            parts.append(t.tail)
    return "".join(parts).strip()


def find_p(paras: list[ET.Element], prefix: str) -> ET.Element:
    for p in paras:
        if para_text(p).startswith(prefix):
            return p
    raise ValueError(f"Paragraph not found: {prefix[:60]}...")


def get_ppr(p: ET.Element) -> ET.Element:
    ppr = p.find("w:pPr", NS)
    if ppr is None:
        ppr = ET.SubElement(p, f"{{{W}}}pPr")
    return ppr


def remove_numpr(ppr: ET.Element) -> None:
    numpr = ppr.find("w:numPr", NS)
    if numpr is not None:
        ppr.remove(numpr)


def remove_pstyle(ppr: ET.Element) -> None:
    ps = ppr.find("w:pStyle", NS)
    if ps is not None:
        ppr.remove(ps)


def set_ilvl(p: ET.Element, ilvl: str) -> None:
    ppr = get_ppr(p)
    numpr = ppr.find("w:numPr", NS)
    if numpr is None:
        numpr = ET.SubElement(ppr, f"{{{W}}}numPr")
    il = numpr.find("w:ilvl", NS)
    if il is None:
        il = ET.SubElement(numpr, f"{{{W}}}ilvl")
    il.set(f"{{{W}}}val", ilvl)


def ensure_numid(p: ET.Element, num_id: str = "18") -> None:
    ppr = get_ppr(p)
    numpr = ppr.find("w:numPr", NS)
    if numpr is None:
        numpr = ET.SubElement(ppr, f"{{{W}}}numPr")
    nid = numpr.find("w:numId", NS)
    if nid is None:
        nid = ET.SubElement(numpr, f"{{{W}}}numId")
    nid.set(f"{{{W}}}val", num_id)


def apply_intro_ppr(p: ET.Element) -> None:
    """Match unnumbered body paragraphs (Ethics clearance style)."""
    ppr = get_ppr(p)
    remove_numpr(ppr)
    remove_pstyle(ppr)
    for tag in ("tabs", "ind"):
        el = ppr.find(f"w:{tag}", NS)
        if el is not None:
            ppr.remove(el)
    spacing = ppr.find("w:spacing", NS)
    if spacing is None:
        spacing = ET.SubElement(ppr, f"{{{W}}}spacing")
    spacing.set(f"{{{W}}}before", "120")
    spacing.set(f"{{{W}}}line", "276")
    spacing.set(f"{{{W}}}lineRule", "auto")
    jc = ppr.find("w:jc", NS)
    if jc is None:
        jc = ET.SubElement(ppr, f"{{{W}}}jc")
    jc.set(f"{{{W}}}val", "both")
    rpr = ppr.find("w:rPr", NS)
    if rpr is not None:
        for bold in list(rpr):
            if bold.tag in (f"{{{W}}}b", f"{{{W}}}bCs"):
                rpr.remove(bold)


def apply_numbered_heading_ppr(p: ET.Element, template: ET.Element) -> None:
    """Apply ilvl-0 numbered heading properties from template paragraph."""
    ppr = get_ppr(p)
    tpl_ppr = get_ppr(template)
    remove_numpr(ppr)
    remove_pstyle(ppr)
    for child in list(ppr):
        ppr.remove(child)
    for child in tpl_ppr:
        ppr.append(deepcopy(child))
    # strip bold defaults on heading line
    rpr = ppr.find("w:rPr", NS)
    if rpr is not None:
        for bold in list(rpr):
            if bold.tag in (f"{{{W}}}b", f"{{{W}}}bCs"):
                rpr.remove(bold)


def strip_run_bold(p: ET.Element) -> None:
    for r in p.findall("w:r", NS):
        rpr = r.find("w:rPr", NS)
        if rpr is None:
            continue
        for bold in list(rpr):
            if bold.tag in (f"{{{W}}}b", f"{{{W}}}bCs"):
                rpr.remove(bold)


def make_comment_text_runs(text: str) -> list[ET.Element]:
    runs = []
    for chunk in text.split(" "):
        if not chunk:
            continue
        r = ET.Element(f"{{{W}}}r")
        t = ET.SubElement(r, f"{{{W}}}t")
        t.text = chunk
        t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
        runs.append(r)
    return runs


def add_comment(comments_root: ET.Element, comment_id: int, text: str) -> None:
    c = ET.Element(
        f"{{{W}}}comment",
        {
            f"{{{W}}}id": str(comment_id),
            f"{{{W}}}author": AUTHOR,
            f"{{{W}}}date": COMMENT_DATE,
            f"{{{W}}}initials": "TK",
        },
    )
    cp = ET.SubElement(
        c,
        f"{{{W}}}p",
        {
            f"{{{W14}}}paraId": f"{comment_id:08X}"[:8],
            f"{{{W14}}}textId": "77777777",
            f"{{{W}}}rsidR": "00ETHICS1",
            f"{{{W}}}rsidRDefault": "00ETHICS1",
        },
    )
    ref = ET.SubElement(cp, f"{{{W}}}r")
    ET.SubElement(ref, f"{{{W}}}annotationRef")
    for r in make_comment_text_runs(text):
        cp.append(r)
    comments_root.append(c)


def wrap_paragraph_comment(p: ET.Element, comment_id: int) -> None:
    if p.find("w:commentRangeStart", NS) is not None:
        return
    start = ET.Element(f"{{{W}}}commentRangeStart", {f"{{{W}}}id": str(comment_id)})
    end = ET.Element(f"{{{W}}}commentRangeEnd", {f"{{{W}}}id": str(comment_id)})
    ref_r = ET.Element(f"{{{W}}}r")
    rpr = ET.SubElement(ref_r, f"{{{W}}}rPr")
    ET.SubElement(rpr, f"{{{W}}}rStyle", {f"{{{W}}}val": "ab"})
    ET.SubElement(rpr, f"{{{W}}}sz", {f"{{{W}}}val": "22"})
    ET.SubElement(rpr, f"{{{W}}}szCs", {f"{{{W}}}val": "22"})
    ET.SubElement(ref_r, f"{{{W}}}commentReference", {f"{{{W}}}id": str(comment_id)})
    children = list(p)
    p.insert(0, start)
    p.append(end)
    p.append(ref_r)


def next_comment_id(comments_path: Path) -> int:
    text = comments_path.read_text(encoding="utf-8")
    ids = [int(x) for x in re.findall(r'w:comment w:id="(\d+)"', text)]
    return max(ids) + 1 if ids else 0


def main() -> None:
    tree = ET.parse(DOC_XML)
    root = tree.getroot()
    body = root.find("w:body", NS)
    paras = list(body.iter(f"{{{W}}}p"))

    intro = find_p(paras, "Although this research relies")
    clearance = find_p(paras, "Ethics clearance process:")
    privacy = find_p(paras, "Privacy and Anonymity")
    data_usage = find_p(paras, "Data Usage and Compliance")

    # 1) Section intro: unnumbered body text (not list item 1)
    apply_intro_ppr(intro)
    apply_intro_ppr(clearance)

    # 2) First numbered item: Privacy and Anonymity (same as Data Usage heading)
    apply_numbered_heading_ppr(privacy, data_usage)
    strip_run_bold(privacy)

    comments_tree = ET.parse(COMMENTS_XML)
    comments_root = comments_tree.getroot()
    cid = next_comment_id(COMMENTS_XML)

    add_comment(
        comments_root,
        cid,
        "Ethics Considerations 서식 정렬: 섹션 도입 문단(공개 데이터·UNISA 윤리 원칙)은 번호 목록에서 제외하고, "
        "번호 항목은 Privacy and Anonymity부터 2번 이후 항목과 동일한 짧은 제목 형식으로 통일했습니다.",
    )
    wrap_paragraph_comment(intro, cid)

    cid2 = cid + 1
    add_comment(
        comments_root,
        cid2,
        "Privacy and Anonymity를 하위 글머리(•)가 아닌 1번 주제 제목(ilvl 0)으로 올려 "
        "Data Usage and Compliance 등 다른 항목과 번호·서식을 맞췄습니다.",
    )
    wrap_paragraph_comment(privacy, cid2)

    tree.write(DOC_XML, encoding="UTF-8", xml_declaration=True)
    comments_tree.write(COMMENTS_XML, encoding="UTF-8", xml_declaration=True)

    # Repack docx
    shutil.copy2(BASE.parent / "Proposal-Final_Taehong Kwon.docx", BASE / "pre_ethics_format.docx.bak")
    temp_zip = BASE / "repacked.zip"
    with zipfile.ZipFile(temp_zip, "w", zipfile.ZIP_DEFLATED) as zout:
        for file_path in UNPACKED.rglob("*"):
            if file_path.is_file():
                arc = file_path.relative_to(UNPACKED).as_posix()
                zout.write(file_path, arc)
    shutil.copy2(temp_zip, OUT_DOCX)
    print("Updated:", OUT_DOCX)
    print("Comments added:", cid, cid2)


if __name__ == "__main__":
    main()
