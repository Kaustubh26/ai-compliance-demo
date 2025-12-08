# services/driveconnector.py

import os
from pathlib import Path
from io import BytesIO

from dotenv import load_dotenv
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import google.auth.exceptions
import pickle

ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")

# You can restrict scopes later; drive.file is fine for now
SCOPES = ["https://www.googleapis.com/auth/drive"]


class DriveConnector:
    """
    Google Drive connector (OAuth, user-based):

    - Authenticates as the logged-in Google user (your account), not a service account.
    - Works with your normal My Drive / Shared drives exactly as you see them.
    - Lists ALL non-trashed files in a folder.
    - Downloads supported files as text (Google Docs or .txt).
    - Uploads reports as .txt.
    """

    def __init__(self) -> None:
        # Path to OAuth client secrets JSON
        client_secret_path = ROOT_DIR / "credentials" / "oauth-client.json"
        if not client_secret_path.exists():
            raise FileNotFoundError(
                f"OAuth client secret not found at: {client_secret_path}\n"
                f"Create an OAuth 2.0 Client ID (Desktop app) in Google Cloud and "
                f"download the JSON to this path."
            )

        creds = None
        token_path = ROOT_DIR / "credentials" / "token.pickle"

        # Load existing token if present
        if token_path.exists():
            try:
                with open(token_path, "rb") as token_file:
                    creds = pickle.load(token_file)
            except Exception:
                creds = None

        # If no valid creds, run the browser flow
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except google.auth.exceptions.RefreshError:
                    creds = None

            if not creds or not creds.valid:
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(client_secret_path),
                    SCOPES,
                )
                # This will open a browser window once, you log in and grant access
                creds = flow.run_local_server(port=0)

            # Save the credentials for next run
            token_path.parent.mkdir(parents=True, exist_ok=True)
            with open(token_path, "wb") as token_file:
                pickle.dump(creds, token_file)

        # At this point, we're authenticated as YOU, not the service account
        self.service = build("drive", "v3", credentials=creds)
        print("✅ Authenticated to Google Drive as an end user (OAuth).")

    # ---------- LISTING ----------

    def list_policy_files(self, folder_id: str) -> list[dict]:
        """
        List all non-trashed files in a folder.

        Returns list of dicts: { id, name, mimeType }.
        """
        if not folder_id:
            raise ValueError("Folder ID is required to list policy files.")

        # Sanity check: try to fetch folder metadata
        folder_meta = self.service.files().get(
            fileId=folder_id,
            fields="id, name, mimeType, driveId, parents",
            supportsAllDrives=True,
        ).execute()
        print(
            "ℹ️ Using folder: "
            f"'{folder_meta.get('name')}' "
            f"(id={folder_meta.get('id')}, "
            f"mimeType={folder_meta.get('mimeType')}, "
            f"driveId={folder_meta.get('driveId')})"
        )

        query = f"'{folder_id}' in parents and trashed=false"

        results = (
            self.service.files()
            .list(
                q=query,
                fields="files(id, name, mimeType, driveId, parents)",
                includeItemsFromAllDrives=True,
                supportsAllDrives=True,
                corpora="allDrives",
            )
            .execute()
        )

        files = results.get("files", [])

        if not files:
            print("ℹ️ Folder is accessible but contains no files.")
        else:
            print("ℹ️ Files found in policies folder:")
            for f in files:
                print(
                    f"   - {f['name']} "
                    f"(mimeType={f.get('mimeType')}, driveId={f.get('driveId')})"
                )

        return files

    # ---------- DOWNLOAD ----------

    def download_file_as_text(self, file: dict) -> str:
        """
        Download a Drive file as UTF-8 text.

        Supported:
        - Google Docs (application/vnd.google-apps.document) -> export as text/plain
        - Plain text (text/plain) -> direct download
        """
        file_id = file["id"]
        name = file["name"]
        mime_type = file.get("mimeType", "")

        if mime_type == "application/vnd.google-apps.document":
            # Google Doc -> export as plain text
            request = self.service.files().export_media(
                fileId=file_id,
                mimeType="text/plain",
            )
        elif mime_type == "text/plain":
            # Raw text file
            request = self.service.files().get_media(
                fileId=file_id,
                supportsAllDrives=True,
            )
        else:
            raise ValueError(
                f"File '{name}' has unsupported mimeType '{mime_type}'. "
                "Convert it to a Google Doc or upload as a plain .txt file "
                "in the policies folder."
            )

        fh = BytesIO()
        downloader = MediaIoBaseDownload(fh, request)

        done = False
        while not done:
            _, done = downloader.next_chunk()

        fh.seek(0)
        return fh.read().decode("utf-8")

    # ---------- UPLOAD ----------

    def upload_text_file(
        self,
        content: str,
        drive_name: str,
        folder_id: str | None = None,
    ) -> str:
        """
        Upload text content as a .txt file to Drive.
        Returns the new file ID.
        """
        file_metadata: dict[str, object] = {"name": drive_name}
        if folder_id:
            file_metadata["parents"] = [folder_id]

        media_body = MediaIoBaseUpload(
            BytesIO(content.encode("utf-8")),
            mimetype="text/plain",
            resumable=False,
        )

        created = (
            self.service.files()
            .create(
                body=file_metadata,
                media_body=media_body,
                fields="id",
                supportsAllDrives=True,
            )
            .execute()
        )

        return created["id"]
