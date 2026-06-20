import xml.etree.ElementTree as ET
from pathlib import Path

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
path = Path(__file__).parent / "unpacked" / "word" / "document.xml"
root = ET.parse(path).getroot()


def pt(p):
    parts = []
    for t in p.iter(f"{W}t"):
        if t.text:
            parts.append(t.text)
        if t.tail:
            parts.append(t.tail)
    return "".join(parts).strip()


paras = [p for p in root.iter(f"{W}p")]
lines = []
for i in range(545, 585):
    if i >= len(paras):
        break
    p = paras[i]
    s = pt(p)
    ps = p.find(f".//{W}pStyle")
    st = ps.get(f"{W}val") if ps is not None else None
    num = p.find(f".//{W}numPr")
    n = None
    if num is not None:
        il = num.find(f"{W}ilvl")
        nid = num.find(f"{W}numId")
        n = (nid.get(f"{W}val") if nid is not None else "?", il.get(f"{W}val") if il is not None else "?")
    lines.append(f"[{i}] style={st} num={n} | {s[:220]}")

Path(__file__).parent.joinpath("analysis2.txt").write_text("\n".join(lines), encoding="utf-8")
