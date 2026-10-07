"""
Move SMART Alignment after O5 (Computational Efficiency) and format as
unnumbered meta-section (O1–O5 alignment), not list item 6.
"""
from __future__ import annotations

import re
import shutil
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from lxml import etree

BASE = Path(__file__).resolve().parent
SRC = Path(r"D:\Github\phd_works\Proposal\Proposal-Final_Taehong Kwon.docx")
UNPACKED = BASE / "unpacked"
TEMPLATE = BASE / "repack_template.docx"
OUT = SRC

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
W14_NS = "http://schemas.microsoft.com/office/word/2010/wordml"
NSMAP = {"w": W_NS, "w14": W14_NS}

AUTHOR = "Taehong Kwon"
COMMENT_DATE = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def w(tag: str) -> str:
    return f"{{{W_NS}}}{tag}"


def para_text(p) -> str:
    return "".join(t.text or "" for t in p.xpath(".//w:t", namespaces=NSMAP)).strip()


def get_ppr(p):
    ppr = p.find("w:pPr", NSMAP)
    if ppr is None:
        ppr = etree.SubElement(p, w("pPr"))
    return ppr


def remove_numpr(ppr):
    for numpr in ppr.xpath("w:numPr", namespaces=NSMAP):
        ppr.remove(numpr)


def clear_list_indent(ppr):
    for tag in ("tabs", "ind"):
        for el in ppr.xpath(f"w:{tag}", namespaces=NSMAP):
            ppr.remove(el)


def format_smart_heading(p):
    ppr = get_ppr(p)
    remove_numpr(ppr)
    clear_list_indent(ppr)
    ps = ppr.find("w:pStyle", NSMAP)
    if ps is None:
        ps = etree.SubElement(ppr, w("pStyle"))
    ps.set(w("val"), "2")
    spacing = ppr.find("w:spacing", NSMAP)
    if spacing is None:
        spacing = etree.SubElement(ppr, w("spacing"))
    spacing.set(w("before"), "240")
    spacing.set(w("after"), "120")


def format_smart_body(p):
    ppr = get_ppr(p)
    remove_numpr(ppr)
    ps = ppr.find("w:pStyle", NSMAP)
    if ps is not None and ps.get(w("val")) == "2":
        ppr.remove(ps)
    clear_list_indent(ppr)


def collect_smart_block(body):
    smart_ps = []
    collecting = False
    for p in body.xpath("w:p", namespaces=NSMAP):
        t = para_text(p)
        if t == "SMART Alignment":
            collecting = True
        if not collecting:
            continue
        if t.startswith("Graph Construction"):
            break
        smart_ps.append(p)
    if not smart_ps:
        raise RuntimeError("SMART Alignment block not found")
    return smart_ps


def find_o53_paragraph(body):
    for p in body.xpath("w:p", namespaces=NSMAP):
        t = para_text(p)
        if t.startswith("O5.3") and "Convergence" in t:
            return p
    raise RuntimeError("O5.3 paragraph not found")


def unpack():
    if UNPACKED.exists():
        shutil.rmtree(UNPACKED)
    UNPACKED.mkdir(parents=True)
    with zipfile.ZipFile(SRC) as z:
        z.extractall(UNPACKED)
    shutil.copy2(SRC, TEMPLATE)


def next_comment_id(comments_path: Path) -> int:
    text = comments_path.read_text(encoding="utf-8")
    ids = [int(x) for x in re.findall(r'w:comment w:id="(\d+)"', text)]
    return max(ids) + 1 if ids else 0


def add_comment(comments_root, cid: int, text: str):
    c = etree.Element(
        w("comment"),
        {
            w("id"): str(cid),
            w("author"): AUTHOR,
            w("date"): COMMENT_DATE,
            w("initials"): "TK",
        },
        nsmap={None: W_NS, "w14": W14_NS},
    )
    cp = etree.SubElement(
        c,
        w("p"),
        {f"{{{W14_NS}}}paraId": f"SM{cid:04X}", f"{{{W14_NS}}}textId": "77777777"},
    )
    etree.SubElement(cp, w("r")).append(etree.Element(w("annotationRef")))
    r = etree.SubElement(cp, w("r"))
    etree.SubElement(r, w("t")).text = text
    comments_root.append(c)


def wrap_comment(p, cid: int):
    if p.find(w("commentRangeStart"), NSMAP) is not None:
        return
    p.insert(0, etree.Element(w("commentRangeStart"), {w("id"): str(cid)}))
    p.append(etree.Element(w("commentRangeEnd"), {w("id"): str(cid)}))
    ref_r = etree.Element(w("r"))
    rpr = etree.SubElement(ref_r, w("rPr"))
    etree.SubElement(rpr, w("rStyle")).set(w("val"), "ab")
    etree.SubElement(ref_r, w("commentReference")).set(w("id"), str(cid))
    p.append(ref_r)


def main():
    unpack()
    doc_path = UNPACKED / "word" / "document.xml"
    comments_path = UNPACKED / "word" / "comments.xml"

    parser = etree.XMLParser(remove_blank_text=False)
    doc = etree.parse(str(doc_path), parser)
    body = doc.getroot().find("w:body", NSMAP)

    smart_ps = collect_smart_block(body)
    for p in smart_ps:
        body.remove(p)

    anchor = find_o53_paragraph(body)
    idx = list(body).index(anchor) + 1
    for i, p in enumerate(smart_ps):
        body.insert(idx + i, p)

    for i, p in enumerate(smart_ps):
        if i == 0:
            format_smart_heading(p)
        else:
            format_smart_body(p)

    doc.write(str(doc_path), xml_declaration=True, encoding="UTF-8", standalone=True)

    cdoc = etree.parse(str(comments_path), parser)
    croot = cdoc.getroot()
    cid = next_comment_id(comments_path)
    add_comment(
        croot,
        cid,
        "2.2 Objectives: SMART Alignment을 O5(Computational Efficiency) 다음으로 이동하고, "
        "번호 목록 6번이 아닌 O1–O5 정렬·검증용 비번호 소제목으로 서식 조정했습니다.",
    )
    wrap_comment(smart_ps[0], cid)
    cdoc.write(str(comments_path), xml_declaration=True, encoding="UTF-8", standalone=True)

    from safe_repack import repack_from_folder

    try:
        repack_from_folder(UNPACKED, TEMPLATE, OUT)
        written = OUT
    except PermissionError:
        written = OUT.with_suffix(".repack.tmp.docx")
        repack_from_folder(UNPACKED, TEMPLATE, written)
        print("LOCKED: wrote", written)

    head = (UNPACKED / "word" / "document.xml").read_text(encoding="utf-8")[:200]
    assert "ns0:" not in head and "<w:document" in head
    with zipfile.ZipFile(written) as z:
        assert z.testzip() is None

    # verify order
    with zipfile.ZipFile(written) as z2:
        root = etree.fromstring(z2.read("word/document.xml"))
    body = root.find("w:body", NSMAP)
    in_obj = False
    order = []
    for p in body.xpath("w:p", namespaces=NSMAP):
        t = para_text(p)
        if p.find(".//w:pStyle", NSMAP) is not None:
            ps = p.find(".//w:pStyle", NSMAP)
            if ps.get(f"{{{W_NS}}}val") == "1" and t == "Objectives":
                in_obj = True
        if not in_obj:
            continue
        if t == "Expected Results" or (t.startswith("Expected Results") and "2.3" not in t):
            break
        if t in (
            "SMART Alignment",
            "Graph Construction",
            "Computational Efficiency and Scalability Analysis",
        ) or t.startswith("O5.3"):
            num = p.find(".//w:numPr", NSMAP)
            order.append((t[:50], num is not None))
    print("Order check:", order)
    ce_idx = next(i for i, (t, _) in enumerate(order) if t.startswith("Computational Efficiency"))
    smart_idx = next(i for i, (t, _) in enumerate(order) if t.startswith("SMART Alignment"))
    assert ce_idx < smart_idx
    assert order[smart_idx][1] is False
    print("OK:", written)


if __name__ == "__main__":
    main()
