import zipfile
from lxml import etree

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W}
p = r"D:\Github\phd_works\Proposal\Proposal-Final_Taehong Kwon.docx"

with zipfile.ZipFile(p) as z:
    print("testzip", z.testzip())
    h = z.read("word/document.xml")[:120].decode()
    print("header ok", "<w:document" in h and "ns0:" not in h)
    n = etree.fromstring(z.read("word/numbering.xml"))
    for nid in ["48", "49"]:
        x = n.xpath(f'//w:num[@w:numId="{nid}"]', namespaces=NS)
        if x:
            aid = x[0].find("w:abstractNumId", NS).get(f"{{{W}}}val")
            print("num", nid, "abstract", aid)
    c = etree.fromstring(z.read("word/comments.xml"))
    for cm in c.xpath("//w:comment", namespaces=NS)[-2:]:
        txt = "".join(t.text or "" for t in cm.xpath(".//w:t", namespaces=NS))
        print("comment", cm.get(f"{{{W}}}id"), cm.get(f"{{{W}}}author"), txt[:70])
    root = etree.fromstring(z.read("word/document.xml"))
    for para in root.xpath("//w:p", namespaces=NS):
        t = "".join(x.text or "" for x in para.xpath(".//w:t", namespaces=NS)).strip()
        if t == "Privacy and Anonymity":
            num = para.find(".//w:numId", NS)
            print("ethics Privacy numId", num.get(f"{{{W}}}val") if num is not None else None)
            break
