import xml.etree.ElementTree as ET
from pathlib import Path

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
root = ET.parse(Path(__file__).parent / "unpacked" / "word" / "document.xml").getroot()
paras = list(root.iter(f"{W}p"))


def pt(p):
    return "".join(t.text or "" for t in p.iter(f"{W}t")).strip()


for idx in range(60, 85):
    p = paras[idx]
    s = pt(p)
    if not s:
        continue
    num = p.find(f".//{W}numPr")
    n = None
    if num is not None:
        il = num.find(f"{W}ilvl")
        nid = num.find(f"{W}numId")
        n = (nid.get(f"{W}val"), il.get(f"{W}val"))
    ps = p.find(f".//{W}pStyle")
    st = ps.get(f"{W}val") if ps is not None else None
    Path(__file__).parent.joinpath("toc_lines.txt").open("a", encoding="utf-8").write(
        f"[{idx}] style={st} num={n} | {s}\n"
    )
