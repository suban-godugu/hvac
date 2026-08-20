from pypdf import PdfReader

path = r"C:\Users\subha\Downloads\150317hvacguide.pdf"
r = PdfReader(path)
print("pages", len(r.pages))
md = r.metadata
print("meta", getattr(md, "title", None), getattr(md, "author", None))
hits = []
for i, p in enumerate(r.pages):
    t = p.extract_text() or ""
    low = t.lower()
    if "pump" in low and (
        "chill" in low
        or "secondary" in low
        or "differential pressure" in low
        or "variable speed" in low
        or "vfd" in low
    ):
        hits.append(i + 1)
print("hits", hits)
out_path = r"c:\hvac\scratch\o14_guide_extract.txt"
chunks = []
for n in [1, 2, 3, 4, 5] + hits:
    t = r.pages[n - 1].extract_text() or ""
    chunks.append(f"\n======== PAGE {n} ========\n{t}")
with open(out_path, "w", encoding="utf-8") as f:
    f.write("\n".join(chunks))
print("wrote", out_path, "chars", sum(len(c) for c in chunks))
