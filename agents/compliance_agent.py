from azure_config import get_ai_client, LLM_MODEL

def run_compliance_analysis(text, filename):
    client = get_ai_client()

    prompt = f"""
You are a Compliance Auditor for ISO 27001 and SOC2.

Analyze the document: {filename}

Return strict JSON:
{{
  "file": "{filename}",
  "issues": [
      {{"section": "", "issue": "", "severity": "", "recommendation": ""}}
  ]
}}
TEXT:
{text}
"""

    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[{"role": "user", "content": prompt}]
    )

    # Correct access
    return response.choices[0].message.content
