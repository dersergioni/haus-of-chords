# PNG renders of every page, for checking the layout by eye. Usage: python3 preview.py [file.pdf] [out_dir]
import os, sys
import pypdfium2 as pdfium
import data
data.require_valid()
from book import PROJ, PDF_NAME

pdf = sys.argv[1] if len(sys.argv) > 1 else os.path.join(PROJ, "dist", PDF_NAME)
out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(PROJ, "build", "preview")
os.makedirs(out, exist_ok=True)
doc = pdfium.PdfDocument(pdf)
for i in range(len(doc)):
    doc[i].render(scale=70 / 72).to_pil().save(os.path.join(out, f"page-{i + 1:02d}.png"))
print("ok", len(doc), "pages ->", out)
