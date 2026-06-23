import xml.etree.ElementTree as ET
from pathlib import Path

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
root = ET.parse(Path(__file__).parent / "unpacked" / "word" / "document.xml").getroot()
paras = list(root.iter(f"{W}p"))
for idx in [551, 556, 557, 558, 559]:
    p = paras[idx]
    Path(__file__).parent.joinpath(f"para_{idx}.xml").write_text(
        ET.tostring(p, encoding="unicode")[:3500], encoding="utf-8"
    )
