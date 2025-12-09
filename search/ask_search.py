# search/ask_search.py

import os
import sys
import textwrap
from typing import List

from dotenv import load_dotenv
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient

# ---------------------------------------------------
# Make project root importable so we can use azure_config
# ---------------------------------------------------
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from azure_config import get_ai_client, LLM_MODEL  # type: ignore

load_dotenv()

SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT")
SEARCH_KEY = os.getenv("AZURE_SEARCH_API_KEY")
SEARCH_INDEX = os.getenv("AZURE_SEARCH_INDEX")


def create_search_client() -> SearchClient:
    if not all([SEARCH_ENDPOINT, SEARCH_KEY, SEARCH_INDEX]):
        raise RuntimeError(
            "AZURE_SEARCH_ENDPOINT / AZURE_SEARCH_API_KEY / AZURE_SEARCH_INDEX must be set in .env"
        )

    return SearchClient(
        endpoint=SEARCH_ENDPOINT,
        index_name=SEARCH_INDEX,
        credential=AzureKeyCredential(SEARCH_KEY),
    )


def search_documents(query: str, top: int = 5) -> List[dict]:
    """
    Basic full-text search across 'content' and 'title' fields.
    Returns list of dicts with id/title/kind/content.
    """
    client = create_search_client()

    results = client.search(
        search_text=query,
        top=top,
        include_total_count=True,
    )

    docs: List[dict] = []
    for r in results:
        docs.append(
            {
                "id": r["id"],
                "title": r.get("title"),
                "kind": r.get("kind"),
                "content": r.get("content"),
            }
        )
    return docs


def build_prompt(query: str, docs: List[dict]) -> str:
    """
    Build a RAG-style prompt for Azure OpenAI using search results as context.
    """

    context_blocks: List[str] = []
    for d in docs:
        title = d.get("title") or d.get("id")
        kind = d.get("kind") or "unknown"
        content = d.get("content") or ""

        # Truncate so the prompt stays within a sane size
        short_content = content[:4000]

        block = f"""
==== SOURCE DOCUMENT ====
Title: {title}
Type: {kind}

Content:
{short_content}
"""
        context_blocks.append(block)

    context_text = "\n\n".join(context_blocks)

    prompt = f"""
You are a compliance assistant specializing in ISO 27001, SOC 2, and general information security governance.

You will be given:
- A user question
- A set of policy and standard documents from the organization (as text)

You MUST:
- Answer ONLY based on the information in the provided documents
- Clearly say if something is not covered by the documents
- Where relevant, reference which document you used (by title)
- Prefer precise, structured, and actionable answers

User question:
{query}

Context from policies & standards:
{context_text}

Now provide a clear, structured answer for the user. If there are gaps, call them out explicitly.
"""
    return textwrap.dedent(prompt).strip()


def answer_query(query: str) -> str:
    docs = search_documents(query, top=5)

    if not docs:
        return (
            "I couldn't find any relevant documents in the compliance index for this query. "
            "Check that your policies and standards are indexed correctly."
        )

    client = get_ai_client()
    prompt = build_prompt(query, docs)

    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": "You are a precise, no-nonsense compliance assistant."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
    )

    return response.choices[0].message.content


def main() -> None:
    print("🔎 Compliance Q&A over Azure Search index")
    print("Type your question (or 'exit' to quit).\n")

    while True:
        try:
            q = input("Q: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye.")
            break

        if not q:
            continue
        if q.lower() in {"exit", "quit"}:
            print("Bye.")
            break

        print("\nThinking...\n")
        answer = answer_query(q)
        print("=== ANSWER ===")
        print(answer)
        print("\n" + "=" * 60 + "\n")


if __name__ == "__main__":
    main()
