import zipfile
from lxml import etree

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W}
path = r"D:\Github\phd_works\Proposal\Proposal-Final_Taehong Kwon.docx"

with zipfile.ZipFile(path) as z:
    root = etree.fromstring(z.read("word/document.xml"))
body = root.find("w:body", NS)
out = open(__file__.replace(".py", ".txt"), "w", encoding="utf-8")
for i, p in enumerate(body.xpath("w:p", namespaces=NS)):
    t = "".join(x.text or "" for x in p.xpath(".//w:t", namespaces=NS)).strip()
    if "Dissertation" in t or "Introduction and research" in t or t in (
        "References",
        "References and appendices",
    ):
        out.write(f"{i}: {t[:90]}\n")
out.close()
