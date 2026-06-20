import zipfile
from lxml import etree

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W}
path = r"D:\Github\phd_works\Proposal\Proposal-Final_Taehong Kwon.docx"

with zipfile.ZipFile(path) as z:
    root = etree.fromstring(z.read("word/document.xml"))
body = root.find("w:body", NS)
paras = body.xpath("w:p", namespaces=NS)
out = open(__file__.replace(".py", ".txt"), "w", encoding="utf-8")
for i in range(140, 185):
    p = paras[i]
    t = "".join(x.text or "" for x in p.xpath(".//w:t", namespaces=NS)).strip()
    num = p.find(".//w:numPr", namespaces=NS)
    nid = il = None
    if num is not None:
        nid = num.find("w:numId", NS).get(f"{{{W}}}val")
        iln = num.find("w:ilvl", NS)
        il = iln.get(f"{{{W}}}val") if iln is not None else "0"
    ps = p.find(".//w:pStyle", NS)
    st = ps.get(f"{{{W}}}val") if ps is not None else None
    out.write(f"[{i}] style={st} num={nid}/{il} | {t[:95]}\n")
out.close()
