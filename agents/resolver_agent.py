# resolver_agent.py

from azure_config import get_ai_client, LLM_MODEL
import json


def build_global_prompt(policy_data: dict, standards_text: str) -> str:
    policy_summaries = []

    for name, info in policy_data.items():
        policy_summaries.append(f"""
==== POLICY DOCUMENT: {name} ====
Full Text:
{info.get("policy_text", "")}

Analysis Summary:
{info.get("analysis", "")}
""")

    return f"""
You are a senior compliance officer specializing in ISO 27001, SOC 2, NIST CSF.

You are given:
- Full combined standards text:
{standards_text}

- Multiple policy documents with their full text and individual AI analysis:
{"".join(policy_summaries)}

Compare all policies against each other AND against the standards.
Identify:
1. Redundant or duplicate content across policies
2. Conflicting or missing control items
3. Which policy sections are covered by standards and which are gaps
4. A clear prioritized list of unresolved compliance gaps

Return response STRICTLY in formatted meaningful paragraphs, not JSON.

Format:

=== GLOBAL COMPLIANCE SUMMARY ===

=== STRONG AREAS ===
- bullet points

=== DUPLICATIONS ===
- document A vs B overlap

=== UNRESOLVED GAPS ===
- missing items vs standard

=== RECOMMENDED NEXT STEPS ===
- actions list
"""


def resolve_cross_document_issues(policy_data: dict, standards_text: str) -> str:
    client = get_ai_client()

    prompt = build_global_prompt(policy_data, standards_text)

    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2
    )

    return response.choices[0].message.content
