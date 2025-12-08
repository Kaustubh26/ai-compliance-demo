# services/onedriveconnector.py

import os
from typing import Dict, List

import requests
from dotenv import load_dotenv
import msal
from docx import Document  # python-docx
from pypdf import PdfReader
from io import BytesIO

load_dotenv()

# Delegated scopes – lets the signed-in user read/write OneDrive files
GRAPH_SCOPES = ["Files.ReadWrite.All"]


class OneDriveConnector:
    """
    OneDrive connector using delegated auth (device code flow) via Microsoft Graph.

    - Authenticates as YOU (your Microsoft personal account).
    - Uses folder *paths* relative to OneDrive root (e.g. "Documents/Standards").
    - Lists files in a folder.
    - Downloads text from .txt, .docx, .pdf.
    - Uploads reports as .txt.
    """

    def __init__(self) -> None:
        client_id = os.getenv("MS_CLIENT_ID")
        tenant_id = os.getenv("MS_TENANT_ID", "consumers")  # 'consumers' for personal accounts

        if not client_id:
            raise RuntimeError("MS_CLIENT_ID must be set in .env")

        authority = f"https://login.microsoftonline.com/{tenant_id}"

        # Token cache on disk so you don't have to log in every time
        self._token_cache_path = ".onedrive_token_cache.bin"
        token_cache = msal.SerializableTokenCache()
        if os.path.exists(self._token_cache_path):
            try:
                with open(self._token_cache_path, "r") as f:
                    token_cache.deserialize(f.read())
            except Exception:
                # If cache is corrupted, reset it
                token_cache = msal.SerializableTokenCache()

        app = msal.PublicClientApplication(
            client_id=client_id,
            authority=authority,
            token_cache=token_cache,
        )

        accounts = app.get_accounts()
        result = None
        if accounts:
            result = app.acquire_token_silent(GRAPH_SCOPES, account=accounts[0])

        if not result:
            # First time: device code flow (you log in in the browser)
            flow = app.initiate_device_flow(scopes=GRAPH_SCOPES)
            if "user_code" not in flow:
                raise RuntimeError(f"Failed to create device flow: {flow}")
            print("\n🔐 To sign in to OneDrive:")
            print("   1. Go to:", flow["verification_uri"])
            print("   2. Enter this code:", flow["user_code"])
            print("   3. Complete login, then return here.\n")
            result = app.acquire_token_by_device_flow(flow)

        if "access_token" not in result:
            raise RuntimeError(f"Could not obtain Graph token: {result}")

        # Save token cache for next runs
        try:
            with open(self._token_cache_path, "w") as f:
                f.write(token_cache.serialize())
        except Exception:
            pass

        self.access_token = result["access_token"]
        self.base_url = "https://graph.microsoft.com/v1.0"
        print("✅ Authenticated to OneDrive via Microsoft Graph (delegated).")

    # ------------------ helpers ------------------

    def _headers(self) -> Dict[str, str]:
        return {"Authorization": f"Bearer {self.access_token}"}

    # ------------------ listing ------------------

    def list_policy_files(self, folder_path: str) -> List[Dict]:
        """
        List files in a folder given a path like "Documents/Standards".

        Returns: list of driveItem dicts (id, name, file, etc.).
        """
        if not folder_path:
            raise ValueError("folder_path is required")

        # /me/drive/root:/Documents/Standards:/children
        url = f"{self.base_url}/me/drive/root:/{folder_path}:/children"

        resp = requests.get(url, headers=self._headers())
        if resp.status_code != 200:
            raise RuntimeError(
                f"Error listing OneDrive folder ({folder_path}): "
                f"{resp.status_code} {resp.text}"
            )

        data = resp.json()
        items = data.get("value", [])

        if not items:
            print(f"ℹ️ OneDrive folder '{folder_path}' is accessible but empty.")
        else:
            print(f"ℹ️ Files in OneDrive folder '{folder_path}':")
            for it in items:
                print(f"   - {it.get('name')} (id={it.get('id')})")

        # Keep only actual files (ignore subfolders)
        files = [it for it in items if "file" in it]
        return files

    # ------------------ internal download helpers ------------------

    def _download_bytes(self, item_id: str, name: str) -> bytes:
        content_url = f"{self.base_url}/me/drive/items/{item_id}/content"
        content_resp = requests.get(content_url, headers=self._headers())
        if content_resp.status_code != 200:
            raise RuntimeError(
                f"Error downloading file content ({name}): "
                f"{content_resp.status_code} {content_resp.text}"
            )
        return content_resp.content

    def _extract_text_from_txt(self, data: bytes) -> str:
        return data.decode("utf-8", errors="ignore")

    def _extract_text_from_docx(self, data: bytes) -> str:
        bio = BytesIO(data)
        doc = Document(bio)
        paragraphs = [p.text for p in doc.paragraphs]
        return "\n".join(paragraphs)

    def _extract_text_from_pdf(self, data: bytes) -> str:
        bio = BytesIO(data)
        reader = PdfReader(bio)
        texts: list[str] = []
        for page in reader.pages:
            try:
                txt = page.extract_text() or ""
            except Exception:
                txt = ""
            texts.append(txt)
        return "\n".join(texts)

    # ------------------ download (public API) ------------------

    def download_file_as_text(self, file: Dict) -> str:
        """
        Download a OneDrive file and return its contents as plain text.

        Supports:
        - .txt        (text/plain)
        - .docx       (application/vnd.openxmlformats-officedocument.wordprocessingml.document)
        - .pdf        (application/pdf)
        """
        item_id = file["id"]
        name = file.get("name", "unknown")

        meta_url = f"{self.base_url}/me/drive/items/{item_id}"
        meta_resp = requests.get(meta_url, headers=self._headers())
        if meta_resp.status_code != 200:
            raise RuntimeError(
                f"Error getting file metadata ({name}): "
                f"{meta_resp.status_code} {meta_resp.text}"
            )

        meta = meta_resp.json()
        mime_type = meta.get("file", {}).get("mimeType", "")
        lower_name = name.lower()

        # Download raw bytes once
        data = self._download_bytes(item_id, name)

        # Decide parser based on mimetype / extension
        if mime_type == "text/plain" or lower_name.endswith(".txt"):
            return self._extract_text_from_txt(data)

        if mime_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document" or lower_name.endswith(
            ".docx"
        ):
            return self._extract_text_from_docx(data)

        if mime_type == "application/pdf" or lower_name.endswith(".pdf"):
            return self._extract_text_from_pdf(data)

        raise ValueError(
            f"File '{name}' has unsupported mimeType '{mime_type}'. "
            "Supported: .txt, .docx, .pdf"
        )

    # ------------------ upload ------------------

    def upload_text_file(
        self,
        content: str,
        drive_name: str,
        folder_path: str | None = None,
    ) -> str:
        """
        Upload text content as a .txt file under the given folder path.

        folder_path: e.g. 'Documents/Reports' or None for root.
        Returns: new driveItem ID.
        """
        file_name = drive_name if drive_name.endswith(".txt") else drive_name + ".txt"

        if folder_path:
            # /me/drive/root:/Documents/Reports/report.txt:/content
            url = f"{self.base_url}/me/drive/root:/{folder_path}/{file_name}:/content"
        else:
            url = f"{self.base_url}/me/drive/root:/{file_name}:/content"

        resp = requests.put(
            url,
            headers=self._headers(),
            data=content.encode("utf-8"),
        )

        if resp.status_code not in (200, 201):
            raise RuntimeError(
                f"Error uploading file to OneDrive: {resp.status_code} {resp.text}"
            )

        item = resp.json()
        print(f"✅ Uploaded report to OneDrive: {item.get('name')} (id={item.get('id')})")
        return item["id"]
