import zipfile
import re

path = r"D:\Github\phd_works\Proposal\Proposal-Final_Taehong Kwon.docx"
out = __file__.replace(".py", ".xml.txt")

with zipfile.ZipFile(path) as z:
    xml = z.read("word/document.xml").decode("utf-8")

# second occurrence = body outline
parts = xml.split("Dissertation/Thesis Outline")
chunk = parts[2] if len(parts) > 2 else parts[-1]
# up to Appendices heading in body
end = chunk.find(">Appendices<")
chunk = chunk[: min(end + 500 if end > 0 else 8000, 12000)]

# simplify: extract paragraph blocks
paras = re.findall(r"<w:p\b[^>]*>.*?</w:p>", chunk, re.DOTALL)
with open(out, "w", encoding="utf-8") as f:
    for i, p in enumerate(paras[:15]):
        text = re.findall(r"<w:t[^>]*>([^<]*)</w:t>", p)
        joined = "".join(text).strip()[:70]
        num = re.search(r'w:numId w:val="(\d+)"', p)
        ilvl = re.search(r'w:ilvl w:val="(\d+)"', p)
        style = re.search(r'w:pStyle w:val="([^"]+)"', p)
        f.write(
            f"{i}: style={style.group(1) if style else None} "
            f"num={num.group(1) if num else None}/{ilvl.group(1) if ilvl else None} "
            f"| {joined}\n"
        )
print("wrote", out, "paras", len(paras))
