import os
from typing import Dict

from dotenv import load_dotenv

from agents.compliance_agent import run_compliance_analysis
from agents.resolver_agent import resolve_cross_document_issues
from services.driveconnector import DriveConnector

load_dotenv()

POLICIES_FOLDER_ID = os.getenv("GOOGLE_DRIVE_POLICIES_FOLDER_ID")
STANDARDS_FOLDER_ID = os.getenv("GOOGLE_DRIVE_STANDARDS_FOLDER_ID")
REPORTS_FOLDER_ID = os.getenv("GOOGLE_DRIVE_REPORTS_FOLDER_ID")


def orchestrator() -> None:
    """
    Drive + Azure pipeline:

    - Fetch *standards* documents from a Google Drive folder.
    - Fetch *policy* documents from a different Google Drive folder.
    - For each policy, call Azure OpenAI with both:
        policy_text + combined standards_text
      to produce a detailed gap analysis.
    - Resolve cross-policy issues using resolver_agent.
    - Upload a final report to the Google Drive reports folder.
    """

    print("Using POLICIES_FOLDER_ID:", POLICIES_FOLDER_ID)
    print("Using STANDARDS_FOLDER_ID:", STANDARDS_FOLDER_ID)
    print("Using REPORTS_FOLDER_ID:", REPORTS_FOLDER_ID)

    if not POLICIES_FOLDER_ID or not STANDARDS_FOLDER_ID or not REPORTS_FOLDER_ID:
        raise RuntimeError(
            "Set GOOGLE_DRIVE_POLICIES_FOLDER_ID, "
            "GOOGLE_DRIVE_STANDARDS_FOLDER_ID and "
            "GOOGLE_DRIVE_REPORTS_FOLDER_ID in .env"
        )

    drive = DriveConnector()

    print("🚀 Starting Multi-Agent Compliance System (Drive + Azure)...")
    print("===========================================================\n")

    # ------------------------------------------------------------------
    # 1. Load standards from Google Drive
    # ------------------------------------------------------------------
    print("📁 Fetching standards from Google Drive...")
    standards_files = drive.list_policy_files(STANDARDS_FOLDER_ID)
    if not standards_files:
        print("⚠️ No standards files found in the standards Drive folder.")
        print("   The model will fall back to generic best practices.")
        combined_standards_text = ""
    else:
        combined_parts: list[str] = []
        for std_file in standards_files:
            std_name = std_file["name"]
            print(f"   - Loading standard: {std_name}")
            try:
                std_text = drive.download_file_as_text(std_file)
                combined_parts.append(f"=== STANDARD DOC: {std_name} ===\n{std_text}")
            except ValueError as e:
                print(f"⚠️ Skipping standard '{std_name}': {e}")
        combined_standards_text = "\n\n".join(combined_parts)

    # ------------------------------------------------------------------
    # 2. Load policies from Google Drive
    # ------------------------------------------------------------------
    print("\n📁 Fetching policies from Google Drive...")
    policy_files = drive.list_policy_files(POLICIES_FOLDER_ID)

    if not policy_files:
        print("⚠️ No files found in the policies Drive folder.")
        print("   Check that the folder ID is correct and that it contains docs.")
        return

    issue_map: Dict[str, str] = {}

    for policy_file in policy_files:
        policy_name = policy_file["name"]
        print(f"\n📄 Analysing policy from Drive: {policy_name}")

        try:
            policy_text = drive.download_file_as_text(policy_file)
        except ValueError as e:
            print(f"⚠️ Skipping file '{policy_name}': {e}")
            continue

        # 3. Run Azure OpenAI compliance analysis using both policy + standards
        analysis = run_compliance_analysis(
            policy_text=policy_text,
            policy_name=policy_name,
            standards_text=combined_standards_text,
        )
        issue_map[policy_name] = analysis

    if not issue_map:
        print("\n⚠️ No policies were successfully processed. Nothing to report.")
        return

    # ------------------------------------------------------------------
    # 4. Cross-document resolver
    # ------------------------------------------------------------------
    print("\n🧠 Running cross-document resolver...")
    resolved_report = resolve_cross_document_issues(issue_map)

    # ------------------------------------------------------------------
    # 5. Upload final report to Google Drive
    # ------------------------------------------------------------------
    final_report_name = "global_compliance_report.txt"
    print(f"\n☁️ Uploading final report to Google Drive as: {final_report_name}")
    try:
        file_id = drive.upload_text_file(
            content=resolved_report,
            drive_name=final_report_name,
            folder_id=REPORTS_FOLDER_ID,
        )
        print(f"✅ Report uploaded to Google Drive. File ID: {file_id}")
    except Exception as e:
        print("❌ Failed to upload report to Google Drive:", e)

    print("\n🎉 Drive + Azure pipeline complete.")


if __name__ == "__main__":
    orchestrator()
