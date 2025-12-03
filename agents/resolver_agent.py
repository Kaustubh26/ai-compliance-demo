from azure_config import get_ai_client, LLM_MODEL

def resolve_cross_document_issues(issue_map):
    client = get_ai_client()

    prompt = f"""
You are a Compliance Issue Resolver.

Here is the map of issues across all documents:
{issue_map}

Compare all documents and identify:
1. Duplicates
2. Issues resolved by another document
3. Final unresolved issues

Return strict JSON:
{{
  "resolved_issues": [],
  "unresolved_issues": [],
  "cross_references": []
}}
"""

    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[{"role": "user", "content": prompt}]
    )

    # Corrected access
    return response.choices[0].message.content
