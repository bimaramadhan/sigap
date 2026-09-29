"""Extract text from PDF using pdfplumber."""
import pdfplumber, sys, os

pdf_path = sys.argv[1] if len(sys.argv) > 1 else ""
if not pdf_path or not os.path.exists(pdf_path):
    print("Usage: python extract_pdf.py <path_to_pdf>")
    sys.exit(1)

out_path = pdf_path.replace(".pdf", "_extracted.txt")

with pdfplumber.open(pdf_path) as pdf:
    print(f"Pages: {len(pdf.pages)}")
    with open(out_path, "w", encoding="utf-8") as f:
        for i, page in enumerate(pdf.pages):
            text = page.extract_text()
            if text:
                f.write(f"\n--- HALAMAN {i+1} ---\n")
                f.write(text)

print(f"Saved: {out_path}")
print(f"Size: {os.path.getsize(out_path):,} bytes")
