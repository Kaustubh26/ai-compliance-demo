import os



from azure_config import get_ai_client
from azure_config import (
    AZURE_SEARCH_ENDPOINT,
    AZURE_SEARCH_API_KEY,
    AZURE_SEARCH_INDEX,
)
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SimpleField,
    SearchableField,
    SearchField,
    VectorSearch,
    VectorSearchProfile,
    HnswAlgorithmConfiguration
)
from azure.core.credentials import AzureKeyCredential
from services.file_loader import load_text_from_file
import json
import re

from utils.file_utils import make_safe_key

AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION")
AZURE_OPENAI_MODEL = os.getenv("AZURE_OPENAI_MODEL")

def extract_controls_with_llm(text, source_name):
    client = get_ai_client()

    prompt = f"""
Extract ISO 27001 / SOC2 controls.

Return ONLY valid JSON list:
[
  {{
    "control_id": "",
    "title": "",
    "description": "",
    "source": "{source_name}"
  }}
]

Do NOT add backticks or markdown formatting.

TEXT:
{text}
"""

    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )

    raw = resp.choices[0].message.content

    # Case A: Azure returns [{"type": "text", "text": "..."}]
    if isinstance(raw, list):
        raw = raw[0].text

    # Remove backticks IF the model still adds them
    cleaned = re.sub(r"```.*?\n", "", raw)     # remove ```json or ```text
    cleaned = cleaned.replace("```", "").strip()

    # Parse safely as JSON
    return json.loads(cleaned)



def ensure_index_exists():
    index_client = SearchIndexClient(
        endpoint=AZURE_SEARCH_ENDPOINT,
        credential=AzureKeyCredential(AZURE_SEARCH_API_KEY)
    )

    # FIXED: list_indexes() instead of get_indexes()
    existing = [idx.name for idx in index_client.list_indexes()]

    if AZURE_SEARCH_INDEX in existing:
        return

    # FIXED: VectorField → SearchField (correct vector definition)
    index = SearchIndex(
        name=AZURE_SEARCH_INDEX,
        fields=[
            SimpleField(name="id", type="Edm.String", key=True),
            SearchableField(name="control_id", type="Edm.String"),
            SearchableField(name="title", type="Edm.String"),
            SearchableField(name="description", type="Edm.String"),
            SearchableField(name="source", type="Edm.String"),

            # ✔ Correct Azure AI Search vector field syntax
            SearchField(
                name="embedding",
                type="Collection(Edm.Single)",      # vector uses float32 array
                vector_search_dimensions=1536,
                vector_search_profile_name="hnsw-profile"
            )
        ],
        vector_search=VectorSearch(
            profiles=[
                VectorSearchProfile(
                    name="hnsw-profile",
                    algorithm_configuration_name="hnsw-config"
                )
            ],
            algorithms=[
                HnswAlgorithmConfiguration(name="hnsw-config")
            ]
        )
    )

    index_client.create_index(index)


def upload_to_search(documents):
    client_search = SearchClient(
        endpoint=AZURE_SEARCH_ENDPOINT,
        credential=AzureKeyCredential(AZURE_SEARCH_API_KEY),
        index_name=AZURE_SEARCH_INDEX
    )

    client_search.upload_documents(documents)


def update_compliance_standards(STANDARDS_DIR):
    ensure_index_exists()

    print("📘 Updating compliance standards...")

    docs = []

    for filename in os.listdir(STANDARDS_DIR):
        path = os.path.join(STANDARDS_DIR, filename)
        text = load_text_from_file(path)

        controls = extract_controls_with_llm(text, filename)

        for c in controls:
            c["id"] = make_safe_key(c['control_id'], filename)

            # Embeddings are disabled for now
            c["embedding"] = [0.0] * 1536

            docs.append(c)

    upload_to_search(docs)
    print("✅ Standards updated in Azure Search.")
