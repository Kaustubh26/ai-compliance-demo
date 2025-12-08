# orchestrator.py  (LOCAL ONEDRIVE VERSION)

import os
from pathlib import Path
from typing import Dict, List

from dotenv import load_dotenv
from docx import Document
from pypdf import PdfReader

from agents.compliance_agent import run_compliance_analysis
from agents.resolver_agent import resolve_cross_document_issues

# Always load .env from project root
ENV_PATH = Path(__file__).resolve().parent / ".env"
load_dotenv(ENV_PATH)

# Local OneDrive-synced folders (set in .env)
POLICIES_DIR = os.getenv("LOCAL_POLICIES_DIR")
STANDARDS_DIR = os.getenv("LOCAL_STANDARDS_DIR")
REPORTS_DIR = os.getenv("LOCAL_REPORTS_DIR")


def read_txt(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def read_docx(path: Path) -> str:
    doc = Document(str(path))
    return "\n".join(p.text for p in doc.paragraphs)


def read_pdf(path: Path) -> str:
    reader = PdfReader(str(path))
    parts: List[str] = []
    for page in reader.pages:
        try:
            txt = page.extract_text() or ""
        except Exception:
            txt = ""
        parts.append(txt)
    return "\n".join(parts)


def load_file_as_text(path: Path) -> str:
    name = path.name.lower()
    if name.endswith(".txt"):
        return read_txt(path)
    if name.endswith(".docx"):
        return read_docx(path)
    if name.endswith(".pdf"):
        return read_pdf(path)
    raise ValueError(f"Unsupported file type: {path.name}")


def list_supported_files(folder: Path) -> List[Path]:
    if not folder.exists():
        raise FileNotFoundError(f"Folder missing: {folder}")
    if not folder.is_dir():
        raise NotADirectoryError(f"Not a folder: {folder}")
    exts = {".txt", ".docx", ".pdf"}
    return sorted([p for p in folder.iterdir() if p.suffix.lower() in exts])


def orchestrator() -> None:
    print("Using LOCAL_POLICIES_DIR:", POLICIES_DIR)
    print("Using LOCAL_STANDARDS_DIR:", STANDARDS_DIR)
    print("Using LOCAL_REPORTS_DIR:", REPORTS_DIR)

    if not POLICIES_DIR or not STANDARDS_DIR or not REPORTS_DIR:
        raise RuntimeError("LOCAL_POLICIES_DIR, LOCAL_STANDARDS_DIR, LOCAL_REPORTS_DIR must be set in .env")

    policies_folder = Path(POLICIES_DIR)
    standards_folder = Path(STANDARDS_DIR)
    reports_folder = Path(REPORTS_DIR)
    reports_folder.mkdir(parents=True, exist_ok=True)

    print("\n🚀 Starting Multi-Agent Compliance System (Local OneDrive sync)")
    print("================================================================\n")

    # --- Load standards ---
    print("📥 Loading standards...")
    standard_files = list_supported_files(standards_folder)

    standard_blocks = []
    for std_path in standard_files:
        print(f"   - {std_path.name}")
        try:
            content = load_file_as_text(std_path)
            standard_blocks.append(f"==== STANDARD: {std_path.name} ====\n{content}")
        except Exception as e:
            print(f"⚠️ Failed reading {std_path.name}: {e}")

    combined_standards = "\n\n".join(standard_blocks)

    # --- Load policies & analyze ---
    print("\n📥 Loading policies...")
    policy_files = list_supported_files(policies_folder)

    policy_data: Dict[str, dict] = {}

    for policy_path in policy_files:
        print(f"\n📄 Running analysis: {policy_path.name}")
        try:
            text = load_file_as_text(policy_path)
        except Exception as e:
            print(f"⚠️ Skipping: {policy_path.name} -> {e}")
            continue

        analysis = run_compliance_analysis(
            policy_text=text,
            policy_name=policy_path.name,
            standards_text=combined_standards
        )

        policy_data[policy_path.name] = {
            "policy_text": text,
            "analysis": analysis
        }

    # --- Resolve cross-document issues ---
    print("\n🧠 Resolving cross-document issues...")
    resolved = resolve_cross_document_issues(policy_data, combined_standards)

    # --- Write final report ---
    report_path = reports_folder / "global_compliance_report.txt"
    report_path.write_text(resolved, encoding="utf-8")

    print("\n✅ Report generated and saved to OneDrive:", report_path)


if __name__ == "__main__":
    orchestrator()
