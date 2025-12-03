# utils/text_extractors.py
import os

def extract_text(path):
    ext = os.path.splitext(path)[1].lower()

    if ext == ".txt":
        return open(path, "r", encoding="utf-8", errors="ignore").read()

    if ext == ".pdf":
        import pdfplumber
        with pdfplumber.open(path) as pdf:
            return "\n".join([p.extract_text() or "" for p in pdf.pages])

    if ext == ".docx":
        import docx
        doc = docx.Document(path)
        return "\n".join([p.text for p in doc.paragraphs])

    return ""

