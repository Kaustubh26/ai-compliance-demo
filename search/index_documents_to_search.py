# search/index_documents_to_search.py

import os
import re
from pathlib import Path
from typing import List

from dotenv import load_dotenv
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
from docx import Document
from pypdf import PdfReader

load_dotenv()

SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT")
SEARCH_KEY = os.getenv("AZURE_SEARCH_API_KEY")
SEARCH_INDEX = os.getenv("AZURE_SEARCH_INDEX")

POLICIES_DIR = Path(os.getenv("LOCAL_POLICIES_DIR")).expanduser()
STANDARDS_DIR = Path(os.getenv("LOCAL_STANDARDS_DIR")).expanduser()


def read_txt(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def read_docx(path: Path) -> str:
    doc = Document(str(path))
    return "\n".join(p.text for p in doc.paragraphs)


def read_pdf(path: Path) -> str:
    reader = PdfReader(str(path))
    chunks: List[str] = []
    for page in reader.pages:
        try:
            txt = page.extract_text() or ""
        except Exception:
            txt = ""
        chunks.append(txt)
    return "\n".join(chunks)


def file_to_text(path: Path) -> str:
    lower = path.suffix.lower()
    if lower == ".txt":
        return read_txt(path)
    if lower == ".docx":
        return read_docx(path)
    if lower == ".pdf":
        return read_pdf(path)
    raise ValueError(f"Unsupported file type: {path}")


def gather_files(folder: Path) -> List[Path]:
    if not folder.exists():
        print(f"⚠️ Folder does not exist, skipping: {folder}")
        return []
    exts = {".txt", ".docx", ".pdf"}
    return [p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in exts]


def make_document_id(kind: str, path: Path) -> str:
    """
    Build a safe document key:
    - Start with kind (policy/standard) + stem (filename without extension)
    - Replace any char NOT in [A-Za-z0-9_-=] with '_'
    """
    base = f"{kind}-{path.stem}"
    safe = re.sub(r"[^A-Za-z0-9_\-=]", "_", base)
    return safe


def main():
    if not all([SEARCH_ENDPOINT, SEARCH_KEY, SEARCH_INDEX]):
        raise RuntimeError("Search env vars missing (AZURE_SEARCH_*)")

    search_client = SearchClient(
        endpoint=SEARCH_ENDPOINT,
        index_name=SEARCH_INDEX,
        credential=AzureKeyCredential(SEARCH_KEY),
    )

    docs_to_upload = []

    # standards
    for path in gather_files(STANDARDS_DIR):
        content = file_to_text(path)
        doc_id = make_document_id("standard", path)
        docs_to_upload.append(
            {
                "id": doc_id,
                "title": path.name,
                "content": content,
                "kind": "standard",
            }
        )

    # policies
    for path in gather_files(POLICIES_DIR):
        content = file_to_text(path)
        doc_id = make_document_id("policy", path)
        docs_to_upload.append(
            {
                "id": doc_id,
                "title": path.name,
                "content": content,
                "kind": "policy",
            }
        )

    if not docs_to_upload:
        print("⚠️ No documents found to upload. Check your LOCAL_POLICIES_DIR and LOCAL_STANDARDS_DIR.")
        return

    print(f"Uploading {len(docs_to_upload)} documents to Azure Search...")
    result = search_client.upload_documents(documents=docs_to_upload)
    succeeded = sum(1 for r in result if r.succeeded)
    print(f"Done. {succeeded}/{len(docs_to_upload)} documents succeeded.")


if __name__ == "__main__":
    main()
