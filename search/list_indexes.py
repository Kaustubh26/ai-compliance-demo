# search/list_indexes.py
import os
from dotenv import load_dotenv
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.indexes import SearchIndexClient

load_dotenv()

endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
key = os.getenv("AZURE_SEARCH_API_KEY")

print("Using endpoint:", endpoint)

client = SearchIndexClient(endpoint=endpoint, credential=AzureKeyCredential(key))

print("Indexes on this service:")
for idx in client.list_indexes():
    print(" -", idx.name)
