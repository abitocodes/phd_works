import zipfile
from lxml import etree

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W}
path = r"D:\Github\phd_works\Proposal\Proposal-Final_Taehong Kwon.docx"

with zipfile.ZipFile(path) as z:
    root = etree.fromstring(z.read("word/document.xml"))
body = root.find("w:body", NS)
i = 0
for p in body.xpath("w:p", namespaces=NS):
    i += 1
    t = "".join(x.text or "" for x in p.xpath(".//w:t", namespaces=NS)).strip()
    num = p.find(".//w:numPr", namespaces=NS)
    if num is not None:
        nid = num.find("w:numId", NS).get(f"{{{W}}}val")
        il = num.find("w:ilvl", NS)
        ilv = il.get(f"{{{W}}}val") if il is not None else "0"
        if nid == "35" and ilv == "0":
            open(__file__.replace(".py", ".txt"), "a", encoding="utf-8").write(
                f"p{i} ilvl0: {t[:80]}\n"
            )
    if t.startswith("Introduction and research problem"):
        break
