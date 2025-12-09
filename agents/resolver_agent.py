# resolver_agent.py

from azure_config import get_ai_client, LLM_MODEL

def build_global_prompt(policy_data: dict, standards_text: str) -> str:
    formatted_policies = []

    for policy_name, policy_info in policy_data.items():
        formatted_policies.append(
f"""
========================
POLICY DOCUMENT: {policy_name}
========================

FULL TEXT:
{policy_info.get("policy_text", "").strip()}

AI ANALYSIS SUMMARY:
{policy_info.get("analysis", "").strip()}
"""
        )

    policies_section = "\n".join(formatted_policies)

    prompt = f"""
You are an advanced compliance auditor specializing in ISO 27001:2022 Annex A,
SOC 2 Trust Services Criteria, and NIST CSF.

You will compare multiple organizational security policies against the complete
standards text provided below.

============================
FULL STANDARDS REFERENCE
============================
{standards_text}

============================
POLICY DOCUMENT SET
============================
{policies_section}

-----------------------------
YOUR TASK
-----------------------------
Perform a detailed cross-document compliance evaluation. You MUST:
1. Compare the policies against each other to identify duplications, overlap,
   conflicts, or missing components.
2. Map policies to ISO Annex A, SOC 2, and NIST CSF control requirements.
3. Identify compliance strengths and evidence references.
4. Identify unresolved gaps that the standards require but the policies lack.
5. Provide implementation guidance and next steps.

-----------------------------
REPORT FORMAT (MANDATORY)
-----------------------------

=== GLOBAL COMPLIANCE SUMMARY ===
High-level evaluation overview

=== STRONG AREAS ===
• bullet list referencing which policies demonstrate compliance and why

=== DUPLICATIONS ===
• policy A vs policy B overlap
• policy sets that repeat similar content

=== UNRESOLVED GAPS ===
• missing control areas, mapped to ISO 27001 Annex A control numbers
• which policies should be created or expanded

=== CONTROL MAPPING TABLE ===
Control | Present In Policies | Missing From | Notes
A.X.X | [...] | [...] | ...

=== RECOMMENDED NEXT STEPS ===
• prioritized list of actionable improvements with ownership guidance

Write professionally, factually, and precisely with deep technical context.
DO NOT return JSON, bullet dump, or superficial summary.
Return a complete written report suitable for compliance audit submission.
    """

    return prompt


def resolve_cross_document_issues(policy_data: dict, standards_text: str) -> str:
    client = get_ai_client()

    prompt = build_global_prompt(policy_data, standards_text)

    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": "You are a highly experienced ISO auditor."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.15,
        max_tokens=6000,
    )

    return response.choices[0].message.content.strip()
