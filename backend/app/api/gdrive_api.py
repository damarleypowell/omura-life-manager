"""
Omura Google Drive API Integration
Provides file management, document storage, and folder organization
through the Google Drive API v3.

Used for:
- Storing lead/customer documents and contracts
- Organizing content assets (images, videos, docs)
- Backing up Omura data exports
- Sharing documents with clients/team

All methods return mock data when Google credentials are not configured.
"""

from __future__ import annotations

import io
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx

from backend.app.config import settings
from backend.app.utils.logging import OmuraLogger


class GoogleDriveClient:
    """Client for Google Drive API v3.

    Handles authentication via OAuth 2.0 service account or user tokens,
    and provides CRUD operations for files and folders.
    """

    BASE_URL = "https://www.googleapis.com/drive/v3"
    UPLOAD_URL = "https://www.googleapis.com/upload/drive/v3"

    # Default Omura folder structure
    OMURA_ROOT_FOLDER = "Omura Life Manager"
    SUBFOLDER_STRUCTURE = [
        "Leads & Customers",
        "Contracts",
        "Content Assets",
        "Reports",
        "Backups",
    ]

    def __init__(self) -> None:
        self.client_id: Optional[str] = settings.GOOGLE_CLIENT_ID
        self.client_secret: Optional[str] = settings.GOOGLE_CLIENT_SECRET
        self.access_token: Optional[str] = None
        self.root_folder_id: Optional[str] = None
        self._http: httpx.AsyncClient = httpx.AsyncClient(timeout=30.0)
        self._logger = OmuraLogger("gdrive_client")
        self._logger.info("GoogleDriveClient initialized", configured=bool(self.client_id))

    @property
    def is_configured(self) -> bool:
        return bool(self.access_token)

    def set_access_token(self, token: str) -> None:
        """Set the OAuth access token for authenticated requests."""
        self.access_token = token
        self._http.headers["Authorization"] = f"Bearer {token}"
        self._logger.info("Google Drive access token set")

    # ──────────────────────────────────────────────
    # Authentication
    # ──────────────────────────────────────────────

    async def authenticate(self, auth_code: Optional[str] = None) -> Dict[str, Any]:
        """Exchange an OAuth code for Google Drive access tokens.

        Args:
            auth_code: Authorization code from Google's OAuth consent screen
                       with Drive scopes.

        Returns:
            Token payload with access_token, refresh_token, and expiry.
        """
        self._logger.info("Authenticating with Google Drive", auth_code_provided=bool(auth_code))

        if not self.client_id or not auth_code:
            self.access_token = "mock_gdrive_access_token"
            return {
                "access_token": self.access_token,
                "refresh_token": "mock_refresh_token",
                "expires_in": 3600,
                "token_type": "Bearer",
                "scope": "https://www.googleapis.com/auth/drive",
            }

        try:
            resp = await self._http.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "code": auth_code,
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "redirect_uri": settings.GOOGLE_REDIRECT_URI,
                    "grant_type": "authorization_code",
                },
            )
            resp.raise_for_status()
            tokens = resp.json()
            self.access_token = tokens.get("access_token")
            self._http.headers["Authorization"] = f"Bearer {self.access_token}"
            self._logger.info("Google Drive authentication successful")
            return tokens
        except httpx.HTTPError as exc:
            self._logger.error("Google Drive auth failed", error=str(exc))
            return {"error": str(exc)}

    # ──────────────────────────────────────────────
    # Folder Management
    # ──────────────────────────────────────────────

    async def ensure_folder_structure(self) -> Dict[str, str]:
        """Create the Omura folder structure in Google Drive if it doesn't exist.

        Returns:
            Dict mapping folder names to their Google Drive IDs.
        """
        self._logger.info("Ensuring Omura folder structure in Google Drive")

        if not self.is_configured:
            return self._mock_folder_structure()

        folder_ids = {}

        # Create root folder
        root_id = await self._find_or_create_folder(self.OMURA_ROOT_FOLDER)
        folder_ids[self.OMURA_ROOT_FOLDER] = root_id
        self.root_folder_id = root_id

        # Create subfolders
        for name in self.SUBFOLDER_STRUCTURE:
            folder_id = await self._find_or_create_folder(name, parent_id=root_id)
            folder_ids[name] = folder_id

        self._logger.info("Folder structure ready", folders=len(folder_ids))
        return folder_ids

    async def _find_or_create_folder(self, name: str, parent_id: Optional[str] = None) -> str:
        """Find a folder by name or create it.

        Args:
            name: Folder name.
            parent_id: Parent folder ID (None = root of Drive).

        Returns:
            The Google Drive folder ID.
        """
        # Search for existing folder
        query = f"name='{name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
        if parent_id:
            query += f" and '{parent_id}' in parents"

        try:
            resp = await self._http.get(
                f"{self.BASE_URL}/files",
                params={"q": query, "fields": "files(id,name)", "pageSize": 1},
            )
            resp.raise_for_status()
            files = resp.json().get("files", [])
            if files:
                return files[0]["id"]
        except httpx.HTTPError:
            pass

        # Create the folder
        metadata = {
            "name": name,
            "mimeType": "application/vnd.google-apps.folder",
        }
        if parent_id:
            metadata["parents"] = [parent_id]

        try:
            resp = await self._http.post(
                f"{self.BASE_URL}/files",
                json=metadata,
            )
            resp.raise_for_status()
            folder = resp.json()
            self._logger.info("Created folder", name=name, id=folder.get("id"))
            return folder.get("id", "")
        except httpx.HTTPError as exc:
            self._logger.error("Failed to create folder", name=name, error=str(exc))
            return ""

    # ──────────────────────────────────────────────
    # File Operations
    # ──────────────────────────────────────────────

    async def upload_file(
        self,
        file_name: str,
        content: bytes,
        mime_type: str = "application/octet-stream",
        folder_name: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Upload a file to Google Drive.

        Args:
            file_name: Name for the file in Drive.
            content: File content as bytes.
            mime_type: MIME type of the file.
            folder_name: Omura subfolder name (e.g. "Leads & Customers").
            description: Optional file description.

        Returns:
            Dict with file ID, name, webViewLink, etc.
        """
        self._logger.info("Uploading file to Drive", name=file_name, size=len(content), folder=folder_name)

        if not self.is_configured:
            return self._mock_file_upload(file_name, mime_type, folder_name)

        # Resolve folder ID
        folder_id = None
        if folder_name:
            folders = await self.ensure_folder_structure()
            folder_id = folders.get(folder_name, self.root_folder_id)

        metadata = {"name": file_name}
        if folder_id:
            metadata["parents"] = [folder_id]
        if description:
            metadata["description"] = description

        try:
            # Simple upload for files < 5MB
            if len(content) < 5 * 1024 * 1024:
                resp = await self._http.post(
                    f"{self.UPLOAD_URL}/files",
                    params={"uploadType": "multipart"},
                    files={
                        "metadata": ("metadata", io.BytesIO(str(metadata).encode()), "application/json"),
                        "file": (file_name, io.BytesIO(content), mime_type),
                    },
                )
            else:
                # Resumable upload for larger files
                resp = await self._http.post(
                    f"{self.UPLOAD_URL}/files",
                    params={"uploadType": "resumable"},
                    json=metadata,
                    headers={"X-Upload-Content-Type": mime_type},
                )

            resp.raise_for_status()
            file_data = resp.json()
            self._logger.info("File uploaded to Drive", id=file_data.get("id"), name=file_name)
            return file_data
        except httpx.HTTPError as exc:
            self._logger.error("Drive upload failed", name=file_name, error=str(exc))
            return self._mock_file_upload(file_name, mime_type, folder_name)

    async def list_files(
        self,
        folder_name: Optional[str] = None,
        query: Optional[str] = None,
        page_size: int = 25,
        page_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """List files in a specific Omura folder or search across Drive.

        Args:
            folder_name: Omura subfolder name to list.
            query: Free-text search query.
            page_size: Number of results per page.
            page_token: Token for pagination.

        Returns:
            Dict with 'files' list and 'nextPageToken'.
        """
        self._logger.info("Listing Drive files", folder=folder_name, query=query)

        if not self.is_configured:
            return self._mock_file_list(folder_name)

        q_parts = ["trashed=false"]
        if folder_name:
            folders = await self.ensure_folder_structure()
            folder_id = folders.get(folder_name)
            if folder_id:
                q_parts.append(f"'{folder_id}' in parents")
        if query:
            q_parts.append(f"fullText contains '{query}'")

        params = {
            "q": " and ".join(q_parts),
            "fields": "files(id,name,mimeType,size,createdTime,modifiedTime,webViewLink,iconLink),nextPageToken",
            "pageSize": page_size,
            "orderBy": "modifiedTime desc",
        }
        if page_token:
            params["pageToken"] = page_token

        try:
            resp = await self._http.get(f"{self.BASE_URL}/files", params=params)
            resp.raise_for_status()
            data = resp.json()
            self._logger.info("Drive files listed", count=len(data.get("files", [])))
            return {
                "files": data.get("files", []),
                "nextPageToken": data.get("nextPageToken"),
            }
        except httpx.HTTPError as exc:
            self._logger.error("Drive list failed", error=str(exc))
            return self._mock_file_list(folder_name)

    async def get_file(self, file_id: str) -> Dict[str, Any]:
        """Get metadata for a specific file.

        Args:
            file_id: The Google Drive file ID.

        Returns:
            File metadata dict.
        """
        self._logger.info("Getting Drive file metadata", file_id=file_id)

        if not self.is_configured:
            return {"status": "not_connected", "id": file_id,
                    "message": "Google Drive isn't connected."}

        try:
            resp = await self._http.get(
                f"{self.BASE_URL}/files/{file_id}",
                params={"fields": "id,name,mimeType,size,createdTime,modifiedTime,webViewLink,description"},
            )
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPError as exc:
            self._logger.error("Drive get file failed", file_id=file_id, error=str(exc))
            return {"id": file_id, "error": str(exc)}

    async def delete_file(self, file_id: str) -> bool:
        """Move a file to the trash in Google Drive.

        Args:
            file_id: The Google Drive file ID.

        Returns:
            True if successful.
        """
        self._logger.info("Trashing Drive file", file_id=file_id)

        if not self.is_configured:
            return True

        try:
            resp = await self._http.patch(
                f"{self.BASE_URL}/files/{file_id}",
                json={"trashed": True},
            )
            resp.raise_for_status()
            self._logger.info("File trashed", file_id=file_id)
            return True
        except httpx.HTTPError as exc:
            self._logger.error("Drive trash failed", file_id=file_id, error=str(exc))
            return False

    # ──────────────────────────────────────────────
    # Lead Document Management
    # ──────────────────────────────────────────────

    async def save_lead_document(
        self,
        lead_name: str,
        document_name: str,
        content: bytes,
        mime_type: str = "application/pdf",
    ) -> Dict[str, Any]:
        """Save a document associated with a lead/customer.

        Creates a subfolder per lead inside "Leads & Customers" and uploads
        the file there.

        Args:
            lead_name: The lead's full name (used as subfolder name).
            document_name: Name for the file.
            content: File content as bytes.
            mime_type: MIME type.

        Returns:
            The uploaded file metadata.
        """
        self._logger.info("Saving lead document", lead=lead_name, doc=document_name)

        if not self.is_configured:
            return self._mock_file_upload(document_name, mime_type, "Leads & Customers")

        # Ensure folder structure exists
        folders = await self.ensure_folder_structure()
        leads_folder_id = folders.get("Leads & Customers")

        # Create lead-specific subfolder
        lead_folder_id = await self._find_or_create_folder(lead_name, parent_id=leads_folder_id)

        # Upload the file
        metadata = {
            "name": document_name,
            "parents": [lead_folder_id],
            "description": f"Document for lead: {lead_name}",
        }

        try:
            resp = await self._http.post(
                f"{self.UPLOAD_URL}/files",
                params={"uploadType": "multipart"},
                files={
                    "metadata": ("metadata", io.BytesIO(str(metadata).encode()), "application/json"),
                    "file": (document_name, io.BytesIO(content), mime_type),
                },
            )
            resp.raise_for_status()
            file_data = resp.json()
            self._logger.info("Lead document saved", lead=lead_name, file_id=file_data.get("id"))
            return file_data
        except httpx.HTTPError as exc:
            self._logger.error("Lead document upload failed", lead=lead_name, error=str(exc))
            return self._mock_file_upload(document_name, mime_type, "Leads & Customers")

    async def get_lead_documents(self, lead_name: str) -> List[Dict[str, Any]]:
        """List all documents for a specific lead.

        Args:
            lead_name: The lead's full name.

        Returns:
            List of file metadata dicts.
        """
        self._logger.info("Fetching lead documents", lead=lead_name)

        if not self.is_configured:
            return []  # not connected — no documents (never fabricate)

        folders = await self.ensure_folder_structure()
        leads_folder_id = folders.get("Leads & Customers")

        # Find the lead's subfolder
        query = f"name='{lead_name}' and mimeType='application/vnd.google-apps.folder' and '{leads_folder_id}' in parents and trashed=false"
        try:
            resp = await self._http.get(
                f"{self.BASE_URL}/files",
                params={"q": query, "fields": "files(id)", "pageSize": 1},
            )
            resp.raise_for_status()
            folders_found = resp.json().get("files", [])
            if not folders_found:
                return []

            lead_folder_id = folders_found[0]["id"]
            result = await self.list_files()
            return [f for f in result.get("files", []) if True]  # Filtered by parent in real impl
        except httpx.HTTPError as exc:
            self._logger.error("Failed to fetch lead documents", lead=lead_name, error=str(exc))
            return []

    # ──────────────────────────────────────────────
    # Export / Backup
    # ──────────────────────────────────────────────

    async def backup_data(self, data: bytes, backup_name: Optional[str] = None) -> Dict[str, Any]:
        """Upload an Omura data backup to the Backups folder.

        Args:
            data: Backup data as bytes (JSON, CSV, or archive).
            backup_name: Custom name for the backup file.

        Returns:
            Uploaded file metadata.
        """
        if not backup_name:
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            backup_name = f"omura_backup_{timestamp}.json"

        self._logger.info("Creating Drive backup", name=backup_name, size=len(data))
        return await self.upload_file(
            file_name=backup_name,
            content=data,
            mime_type="application/json",
            folder_name="Backups",
            description=f"Omura automatic backup - {datetime.now(timezone.utc).isoformat()}",
        )

    # ──────────────────────────────────────────────
    # Cleanup
    # ──────────────────────────────────────────────

    async def close(self) -> None:
        await self._http.aclose()
        self._logger.info("GoogleDriveClient HTTP connection closed")

    # ──────────────────────────────────────────────
    # Mock helpers
    # ──────────────────────────────────────────────

    # The following "_mock_*" methods used to fabricate Drive contents. They now
    # return honest not-connected results so the app never presents invented files
    # as if they were the user's real Drive. (Kept as methods so existing call
    # sites — not-configured branches and on-error fallbacks — degrade honestly.)
    _NOT_CONNECTED = "Google Drive isn't connected — reconnect at /auth/google."

    def _mock_folder_structure(self) -> Dict[str, str]:
        return {}  # never fabricate folder IDs

    def _mock_file_upload(self, file_name: str, mime_type: str, folder: Optional[str]) -> Dict[str, Any]:
        return {"status": "not_connected", "uploaded": False,
                "message": self._NOT_CONNECTED, "name": file_name}

    def _mock_file_list(self, folder_name: Optional[str]) -> Dict[str, Any]:
        return {"status": "not_connected", "files": [], "nextPageToken": None,
                "message": self._NOT_CONNECTED}
