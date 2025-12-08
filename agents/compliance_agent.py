# agents/compliance_agent.py

import os
from dotenv import load_dotenv
from openai import AzureOpenAI

load_dotenv()

AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-05-01-preview")
AZURE_OPENAI_MODEL = os.getenv("AZURE_OPENAI_MODEL")  # e.g. "gpt-4o-mini"


if not AZURE_OPENAI_ENDPOINT or not AZURE_OPENAI_API_KEY or not AZURE_OPENAI_MODEL:
    raise RuntimeError(
        "Azure OpenAI config missing. Set AZURE_OPENAI_ENDPOINT, "
        "AZURE_OPENAI_API_KEY, and AZURE_OPENAI_MODEL in .env"
    )

client = AzureOpenAI(
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
    api_key=AZURE_OPENAI_API_KEY,
    api_version=AZURE_OPENAI_API_VERSION,
)


def run_compliance_analysis(
    policy_text: str,
    policy_name: str,
    standards_text: str,
) -> str:
    """
    Compare a single policy against the provided standards text.

    policy_text:    Full text of the policy from Google Drive.
    policy_name:    File name / logical name for the policy.
    standards_text: Combined text of all relevant standards documents
                    fetched from Google Drive (ISO, SOC2, NIST, etc.).

    Returns: A structured human-readable gap analysis as plain text.
    """

    system_msg = (
        "You are a strict information security and compliance analyst. "
        "You compare an organization's policy against formal standards "
        "such as ISO 27001, SOC 2, NIST, or internal standards.\n\n"
        "You must:\n"
        "- Identify where the policy aligns with the standards.\n"
        "- Identify gaps where required controls are missing, vague, or weak.\n"
        "- Give clear, actionable remediation suggestions.\n"
        "Be concise but specific. Avoid fluff."
    )

    user_msg = (
        f"POLICY NAME:\n{policy_name}\n\n"
        "POLICY TEXT:\n"
        "----------------\n"
        f"{policy_text}\n\n"
        "REFERENCE STANDARDS TEXT:\n"
        "-------------------------\n"
        f"{standards_text}\n\n"
        "TASK:\n"
        "Compare the policy to the standards. Focus on gaps.\n"
        "Return your answer in this structure:\n\n"
        "Summary:\n"
        "- 2–4 bullet points summarising overall alignment and risk.\n\n"
        "Aligned Controls:\n"
        "- Bullet list of places where the policy clearly matches key "
        "requirements from the standards.\n\n"
        "Gaps and Issues:\n"
        "- For each major gap, use this pattern:\n"
        "  * [Area] Short title – what is missing or weak, why it matters, "
        "and a short remediation suggestion.\n\n"
        "Overall Risk Rating:\n"
        "- One of: Low / Medium / High, with a one-line justification."
    )

    response = client.chat.completions.create(
        model=AZURE_OPENAI_MODEL,
        messages=[
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg},
        ],
        temperature=0.2,
    )

    return response.choices[0].message.content
