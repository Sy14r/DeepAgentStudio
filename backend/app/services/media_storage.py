"""
Media Storage Service for handling multimodal outputs.

This service manages media files generated during agent execution:
- Stores images, audio, video, and other files in session workspaces
- Tracks media files in the database with metadata
- Generates API URLs for serving media files
"""
import os
import base64
import hashlib
import logging
import mimetypes
from pathlib import Path
from typing import Optional, Dict, Any, Tuple, List
from datetime import datetime

from sqlalchemy.orm import Session as DBSession

from ..models.session import Session, SessionMediaFile, MediaFileType, Message
from .workspace import WORKSPACE_BASE_PATH

logger = logging.getLogger(__name__)


# Configuration
MEDIA_SUBDIRECTORY = "_media"
MAX_MEDIA_FILE_SIZE_MB = int(os.environ.get("MAX_MEDIA_FILE_SIZE_MB", "50"))


# MIME type to media type mapping
MIME_TO_MEDIA_TYPE: Dict[str, MediaFileType] = {
    # Images
    "image/png": MediaFileType.IMAGE,
    "image/jpeg": MediaFileType.IMAGE,
    "image/gif": MediaFileType.IMAGE,
    "image/webp": MediaFileType.IMAGE,
    "image/svg+xml": MediaFileType.IMAGE,
    # Audio
    "audio/mpeg": MediaFileType.AUDIO,
    "audio/mp3": MediaFileType.AUDIO,
    "audio/wav": MediaFileType.AUDIO,
    "audio/ogg": MediaFileType.AUDIO,
    "audio/webm": MediaFileType.AUDIO,
    "audio/aac": MediaFileType.AUDIO,
    # Video
    "video/mp4": MediaFileType.VIDEO,
    "video/webm": MediaFileType.VIDEO,
    "video/ogg": MediaFileType.VIDEO,
    "video/quicktime": MediaFileType.VIDEO,
    # Default to file for anything else
}


def get_media_type_from_mime(mime_type: str) -> MediaFileType:
    """Get MediaFileType from MIME type string."""
    return MIME_TO_MEDIA_TYPE.get(mime_type, MediaFileType.FILE)


class MediaStorageService:
    """
    Service for storing and retrieving media files from agent outputs.

    Media files are stored in the session workspace under a _media subdirectory.
    Each file gets a database record for tracking and a generated API URL.

    Usage:
        storage = MediaStorageService(db)
        media_file = storage.save_media_file(
            session_id=123,
            file_content=image_bytes,
            file_name="generated_image.png",
            mime_type="image/png"
        )
    """

    def __init__(self, db: DBSession):
        """Initialize media storage service with database session."""
        self.db = db
        self.base_path = Path(WORKSPACE_BASE_PATH)
        self.max_file_size = MAX_MEDIA_FILE_SIZE_MB * 1024 * 1024

    def _get_media_path(self, session_id: int) -> Path:
        """Get the filesystem path for a session's media directory."""
        return self.base_path / str(session_id) / MEDIA_SUBDIRECTORY

    def _generate_unique_filename(self, original_name: str, content: bytes) -> str:
        """
        Generate a unique filename based on content hash.

        Uses a short hash prefix to avoid collisions while keeping
        the original filename for readability.
        """
        # Get hash of content for uniqueness
        content_hash = hashlib.md5(content).hexdigest()[:8]

        # Split original name
        name_parts = original_name.rsplit('.', 1)
        if len(name_parts) == 2:
            base_name, extension = name_parts
            return f"{base_name}_{content_hash}.{extension}"
        else:
            return f"{original_name}_{content_hash}"

    def _ensure_media_directory(self, session_id: int) -> Path:
        """Ensure the media directory exists for a session."""
        media_path = self._get_media_path(session_id)
        media_path.mkdir(parents=True, exist_ok=True)
        return media_path

    def save_media_file(
        self,
        session_id: int,
        file_content: bytes,
        file_name: str,
        mime_type: str,
        message_id: Optional[int] = None,
        file_metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[SessionMediaFile]:
        """
        Save a media file to the session workspace.

        Args:
            session_id: Session ID to associate the file with
            file_content: Raw bytes of the file
            file_name: Original or desired filename
            mime_type: MIME type of the file
            message_id: Optional message ID to associate with
            file_metadata: Optional metadata dict (dimensions, duration, etc.)

        Returns:
            SessionMediaFile record if successful, None on failure
        """
        try:
            # Validate file size
            if len(file_content) > self.max_file_size:
                logger.error(f"File too large: {len(file_content)} bytes > {self.max_file_size} bytes")
                return None

            # Verify session exists
            session = self.db.query(Session).filter(Session.id == session_id).first()
            if not session:
                logger.error(f"Session not found: {session_id}")
                return None

            # Ensure media directory exists
            media_path = self._ensure_media_directory(session_id)

            # Generate unique filename
            unique_filename = self._generate_unique_filename(file_name, file_content)
            file_path = media_path / unique_filename

            # Write the file
            file_path.write_bytes(file_content)

            # Determine media type
            media_type = get_media_type_from_mime(mime_type)

            # Generate API URL
            relative_path = f"{MEDIA_SUBDIRECTORY}/{unique_filename}"
            url = f"/api/v1/sessions/{session_id}/media/{relative_path}"

            # Create database record
            media_file = SessionMediaFile(
                session_id=session_id,
                message_id=message_id,
                file_name=file_name,
                file_path=relative_path,
                media_type=media_type.value,
                mime_type=mime_type,
                file_size_bytes=len(file_content),
                url=url,
                file_metadata=file_metadata or {}
            )

            self.db.add(media_file)
            self.db.commit()
            self.db.refresh(media_file)

            logger.info(f"Saved media file: {unique_filename} ({len(file_content)} bytes) for session {session_id}")

            return media_file

        except Exception as e:
            logger.error(f"Failed to save media file for session {session_id}: {e}")
            self.db.rollback()
            return None

    def save_base64_media(
        self,
        session_id: int,
        base64_content: str,
        file_name: str,
        mime_type: str,
        message_id: Optional[int] = None,
        file_metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[SessionMediaFile]:
        """
        Save a base64-encoded media file.

        Args:
            session_id: Session ID
            base64_content: Base64-encoded file content (optionally with data URL prefix)
            file_name: Filename
            mime_type: MIME type
            message_id: Optional message ID
            file_metadata: Optional metadata

        Returns:
            SessionMediaFile record if successful, None on failure
        """
        try:
            # Handle data URL format (data:image/png;base64,...)
            if base64_content.startswith('data:'):
                # Extract the base64 part after the comma
                parts = base64_content.split(',', 1)
                if len(parts) == 2:
                    base64_content = parts[1]

                    # Also extract MIME type if not provided
                    if mime_type == 'application/octet-stream' and ';' in parts[0]:
                        mime_type = parts[0].split(':')[1].split(';')[0]

            # Decode base64
            file_content = base64.b64decode(base64_content)

            return self.save_media_file(
                session_id=session_id,
                file_content=file_content,
                file_name=file_name,
                mime_type=mime_type,
                message_id=message_id,
                file_metadata=file_metadata
            )

        except Exception as e:
            logger.error(f"Failed to decode and save base64 media: {e}")
            return None

    def save_from_url_response(
        self,
        session_id: int,
        content: bytes,
        original_url: str,
        file_name: Optional[str] = None,
        mime_type: Optional[str] = None,
        message_id: Optional[int] = None,
        file_metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[SessionMediaFile]:
        """
        Save media content downloaded from a URL.

        Args:
            session_id: Session ID
            content: Raw bytes from URL response
            original_url: Original URL for reference
            file_name: Optional filename (extracted from URL if not provided)
            mime_type: Optional MIME type (guessed from filename if not provided)
            message_id: Optional message ID
            file_metadata: Optional metadata

        Returns:
            SessionMediaFile record if successful, None on failure
        """
        # Extract filename from URL if not provided
        if not file_name:
            url_path = original_url.split('?')[0]  # Remove query params
            file_name = url_path.split('/')[-1] or 'downloaded_file'

        # Guess MIME type if not provided
        if not mime_type:
            mime_type, _ = mimetypes.guess_type(file_name)
            mime_type = mime_type or 'application/octet-stream'

        # Add original URL to metadata
        metadata = file_metadata or {}
        metadata['original_url'] = original_url

        return self.save_media_file(
            session_id=session_id,
            file_content=content,
            file_name=file_name,
            mime_type=mime_type,
            message_id=message_id,
            file_metadata=metadata
        )

    def get_media_file(self, session_id: int, file_path: str) -> Tuple[Optional[bytes], Optional[str]]:
        """
        Get a media file's content and MIME type.

        Args:
            session_id: Session ID
            file_path: Relative path within session workspace

        Returns:
            Tuple of (file_bytes, mime_type) or (None, None) on failure
        """
        try:
            # Validate path (prevent directory traversal)
            if '..' in file_path:
                logger.warning(f"Path traversal attempt blocked: {file_path}")
                return None, None

            # Build full path
            full_path = self.base_path / str(session_id) / file_path

            # Verify it's within the workspace
            try:
                full_path = full_path.resolve()
                workspace_path = (self.base_path / str(session_id)).resolve()
                if not str(full_path).startswith(str(workspace_path)):
                    logger.warning(f"Path outside workspace: {file_path}")
                    return None, None
            except Exception:
                return None, None

            if not full_path.exists():
                logger.warning(f"Media file not found: {full_path}")
                return None, None

            # Read file content
            content = full_path.read_bytes()

            # Determine MIME type
            mime_type, _ = mimetypes.guess_type(str(full_path))
            mime_type = mime_type or 'application/octet-stream'

            return content, mime_type

        except Exception as e:
            logger.error(f"Failed to get media file {file_path} for session {session_id}: {e}")
            return None, None

    def get_media_files_for_session(self, session_id: int) -> List[SessionMediaFile]:
        """Get all media files for a session."""
        return self.db.query(SessionMediaFile).filter(
            SessionMediaFile.session_id == session_id
        ).order_by(SessionMediaFile.created_at.desc()).all()

    def get_media_files_for_message(self, message_id: int) -> List[SessionMediaFile]:
        """Get all media files associated with a message."""
        return self.db.query(SessionMediaFile).filter(
            SessionMediaFile.message_id == message_id
        ).order_by(SessionMediaFile.created_at).all()

    def delete_media_file(self, media_file_id: int) -> bool:
        """
        Delete a media file from storage and database.

        Args:
            media_file_id: ID of the SessionMediaFile record

        Returns:
            True if successful, False otherwise
        """
        try:
            media_file = self.db.query(SessionMediaFile).filter(
                SessionMediaFile.id == media_file_id
            ).first()

            if not media_file:
                return False

            # Delete physical file
            full_path = self.base_path / str(media_file.session_id) / media_file.file_path
            if full_path.exists():
                full_path.unlink()

            # Delete database record
            self.db.delete(media_file)
            self.db.commit()

            logger.info(f"Deleted media file {media_file_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete media file {media_file_id}: {e}")
            self.db.rollback()
            return False

    def cleanup_session_media(self, session_id: int) -> int:
        """
        Clean up all media files for a session.

        Args:
            session_id: Session ID to clean up

        Returns:
            Number of files deleted
        """
        try:
            # Get all media files for session
            media_files = self.get_media_files_for_session(session_id)
            count = len(media_files)

            # Delete each file
            for media_file in media_files:
                full_path = self.base_path / str(session_id) / media_file.file_path
                if full_path.exists():
                    full_path.unlink()
                self.db.delete(media_file)

            self.db.commit()

            # Remove media directory if empty
            media_dir = self._get_media_path(session_id)
            if media_dir.exists() and not any(media_dir.iterdir()):
                media_dir.rmdir()

            logger.info(f"Cleaned up {count} media files for session {session_id}")
            return count

        except Exception as e:
            logger.error(f"Failed to cleanup media for session {session_id}: {e}")
            self.db.rollback()
            return 0


def get_media_storage_service(db: DBSession) -> MediaStorageService:
    """Get media storage service instance."""
    return MediaStorageService(db)
