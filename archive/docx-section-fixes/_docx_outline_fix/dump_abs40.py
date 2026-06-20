import zipfile
from lxml import etree

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W}
path = r"D:\Github\phd_works\Proposal\Proposal-Final_Taehong Kwon.docx"
out = __file__.replace(".py", ".txt")

with zipfile.ZipFile(path) as z:
    nums = etree.fromstring(z.read("word/numbering.xml"))

abs40 = nums.xpath('//w:abstractNum[@w:abstractNumId="40"]', namespaces=NS)[0]
with open(out, "w", encoding="utf-8") as f:
    f.write(etree.tostring(abs40, pretty_print=True, encoding="unicode"))

print("ok")
