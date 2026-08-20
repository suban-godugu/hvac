from pypdf import PdfReader

path = r"C:\Users\subha\Downloads\150317hvacguide.pdf"
r = PdfReader(path)
out = []
# Printed pages 71-74 were PDF ~79-84 from prior extract; dump a range
for n in range(78, 90):
    t = r.pages[n - 1].extract_text() or ""
    out.append(f"\n======== PAGE {n} ========\n{t}")
with open(r"c:\hvac\scratch\o15_guide_extract.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(out))
print("wrote", sum(len(x) for x in out))
