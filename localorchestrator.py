import queue
import os
from agents.scanner_agent import start_scanner_agent
from agents.compliance_agent import run_compliance_analysis
from agents.resolver_agent import resolve_cross_document_issues
from agents.standards_updater_agent import update_compliance_standards
from services.file_loader import load_text_from_file

DATA_DIR = "./data"
STANDARDS_DIR = "./standards"
REPORT_PATH = "./reports/compliance_reportt.txt"

def orchestrator():
    # 1. Update standards into Azure Search (your RAG knowledge base)
    update_compliance_standards(STANDARDS_DIR)

    # 2. Start monitoring all documents
    file_queue = queue.Queue()

    print("🚀 Starting Multi-Agent Compliance System...")
    print("============================================")

    # start scanner agent in parallel thread
    import threading
    threading.Thread(target=start_scanner_agent, args=(DATA_DIR, file_queue), daemon=True).start()

    issue_map = {}

    while True:
        if not file_queue.empty():
            filepath = file_queue.get()
            filename = os.path.basename(filepath)

            print(f"\n📄 File changed: {filename}")

            text = load_text_from_file(filepath)
            
            # 3. Run compliance analysis agent
            analysis = run_compliance_analysis(text, filename)
            issue_map[filename] = analysis

            print("🧠 Running cross-document resolver...")
            resolved = resolve_cross_document_issues(issue_map)

            # 4. Store the final result
            with open(REPORT_PATH, "w", encoding="utf-8") as rep:
                rep.write(resolved)

            print("✅ Report updated:", REPORT_PATH)

if __name__ == "__main__":
    orchestrator()
