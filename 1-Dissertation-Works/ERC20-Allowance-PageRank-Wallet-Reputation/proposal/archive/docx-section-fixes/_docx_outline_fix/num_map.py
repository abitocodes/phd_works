import xml.etree.ElementTree as ET
from pathlib import Path

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
root = ET.parse(Path(__file__).parent / "unpacked" / "word" / "numbering.xml").getroot()

lines = []
for an in root.findall(f"{W}abstractNum"):
    aid = an.get(f"{W}abstractNumId")
    texts = []
    for lvl in an.findall(f"{W}lvl"):
        lt = lvl.find(f"{W}lvlText")
        if lt is not None:
            texts.append((lvl.get(f"{W}ilvl"), repr(lt.get(f"{W}val"))))
    if any("%1.%2" in x[1] for x in texts):
        lines.append(f"abstract {aid}: {texts[:4]}")

lines.append("\nnum map (selected):")
for num in root.findall(f"{W}num"):
    nid = num.get(f"{W}numId")
    if nid in {"32", "44", "35", "18", "42"}:
        aid = num.find(f"{W}abstractNumId").get(f"{W}val")
        lines.append(f"  numId {nid} -> abstract {aid}")

Path(__file__).parent.joinpath("num_map_out.txt").write_text("\n".join(lines), encoding="utf-8")
