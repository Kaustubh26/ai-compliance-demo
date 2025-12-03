# azure_config.py

import os
from dotenv import load_dotenv
from openai import AzureOpenAI

load_dotenv()

ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION")
LLM_MODEL = os.getenv("AZURE_OPENAI_MODEL", "gpt-4o")

AZURE_SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT")
AZURE_SEARCH_API_KEY = os.getenv("AZURE_SEARCH_API_KEY")
AZURE_SEARCH_INDEX = os.getenv("AZURE_SEARCH_INDEX")


def get_ai_client():
    return AzureOpenAI(
        azure_endpoint=ENDPOINT,
        api_key=API_KEY,
        api_version=API_VERSION
    )
