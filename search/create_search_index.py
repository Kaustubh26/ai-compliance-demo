# search/create_search_index.py

import os
from dotenv import load_dotenv

from azure.core.credentials import AzureKeyCredential
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SimpleField,
    SearchableField,
    SearchFieldDataType,
)

load_dotenv()

SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT")
SEARCH_KEY = os.getenv("AZURE_SEARCH_API_KEY")
SEARCH_INDEX = os.getenv("AZURE_SEARCH_INDEX")

print("DEBUG: AZURE_SEARCH_ENDPOINT =", SEARCH_ENDPOINT)
print("DEBUG: AZURE_SEARCH_INDEX   =", SEARCH_INDEX)

if not all([SEARCH_ENDPOINT, SEARCH_KEY, SEARCH_INDEX]):
    raise RuntimeError("Missing AZURE_SEARCH_* env vars")

index_client = SearchIndexClient(
    endpoint=SEARCH_ENDPOINT,
    credential=AzureKeyCredential(SEARCH_KEY),
)

# Simple schema: id, title, content, kind
index = SearchIndex(
    name=SEARCH_INDEX,
    fields=[
        SimpleField(
            name="id",
            type=SearchFieldDataType.String,
            key=True,
            filterable=True,
        ),
        SearchableField(
            name="title",
            type=SearchFieldDataType.String,
            sortable=True,
            filterable=True,
        ),
        SearchableField(
            name="content",
            type=SearchFieldDataType.String,
        ),
        SimpleField(
            name="kind",
            type=SearchFieldDataType.String,
            filterable=True,
            facetable=True,
        ),
    ],
)

print(f"\nCreating / updating index: {SEARCH_INDEX}")
index_client.create_or_update_index(index)
print("✅ Index created/updated.")

print("\nCurrent indexes in this service:")
for idx in index_client.list_indexes():
    print(" -", idx.name)
