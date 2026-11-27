"""Private local media storage primitive for a future authenticated service.

The store is not exposed as an HTTP endpoint. It writes validated image bytes under
server-generated opaque IDs, outside the web root, with restrictive permissions.
A production deployment must mount a persistent encrypted private volume and add
durable metadata/ownership records before enabling customer uploads.
"""
from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import re
import secrets
import stat

from app.media_validation import MAX_IMAGE_BYTES, ValidatedImage, validate_image_bytes


_ID_PATTERN = re.compile(r"^[a-f0-9]{32}$")
_FORMAT_EXTENSIONS = {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp"}
_FORMAT_CONTENT_TYPES = {
    "JPEG": "image/jpeg",
    "PNG": "image/png",
    "WEBP": "image/webp",
}


class MediaStorageError(RuntimeError):
    """Raised when private media storage cannot safely complete an operation."""


@dataclass(frozen=True)
class StoredMedia:
    media_id: str
    format: str
    width: int
    height: int
    byte_count: int
    content_type: str


class PrivateLocalMediaStore:
    """Store image originals in a private local directory; never derive paths from users."""

    def __init__(self, root: Path):
        root = Path(root)
        if root.exists() and root.is_symlink():
            raise MediaStorageError("Media storage root must not be a symbolic link.")
        root.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.root = root.resolve(strict=True)
        if not self.root.is_dir():
            raise MediaStorageError("Media storage root must be a directory.")
        try:
            self.root.chmod(0o700)
        except OSError as exc:
            raise MediaStorageError("Could not secure media storage directory permissions.") from exc

    def _path_for(self, media_id: str) -> Path:
        if not isinstance(media_id, str) or not _ID_PATTERN.fullmatch(media_id):
            raise MediaStorageError("Invalid media identifier.")
        matches = [self.root / f"{media_id}{extension}" for extension in _FORMAT_EXTENSIONS.values()]
        existing = [path for path in matches if path.exists() or path.is_symlink()]
        if len(existing) > 1:
            raise MediaStorageError("Media identifier maps to multiple stored files.")
        return existing[0] if existing else matches[0]

    def put_image(self, data: bytes) -> StoredMedia:
        validated: ValidatedImage = validate_image_bytes(data)
        extension = _FORMAT_EXTENSIONS[validated.format]
        media_id = secrets.token_hex(16)
        destination = self.root / f"{media_id}{extension}"
        temporary = self.root / f".{media_id}.{secrets.token_hex(8)}.tmp"
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        fd = None
        try:
            fd = os.open(temporary, flags, 0o600)
            with os.fdopen(fd, "wb") as stream:
                fd = None
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, destination)
            destination.chmod(0o600)
            # Persist the directory entry as well as file contents where supported.
            directory_fd = os.open(self.root, os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        except OSError as exc:
            if fd is not None:
                os.close(fd)
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass
            raise MediaStorageError("Could not write private media file.") from exc

        return StoredMedia(
            media_id=media_id,
            format=validated.format,
            width=validated.width,
            height=validated.height,
            byte_count=validated.byte_count,
            content_type=_FORMAT_CONTENT_TYPES[validated.format],
        )

    def read_image(self, media_id: str) -> bytes:
        path = self._path_for(media_id)
        flags = os.O_RDONLY
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        try:
            fd = os.open(path, flags)
            with os.fdopen(fd, "rb") as stream:
                metadata = os.fstat(stream.fileno())
                if not stat.S_ISREG(metadata.st_mode):
                    raise MediaStorageError("Stored media is not a regular file.")
                if metadata.st_size > MAX_IMAGE_BYTES:
                    raise MediaStorageError("Stored media exceeds the configured size limit.")
                data = stream.read(MAX_IMAGE_BYTES + 1)
            if len(data) > MAX_IMAGE_BYTES:
                raise MediaStorageError("Stored media exceeds the configured size limit.")
            validate_image_bytes(data)
            return data
        except FileNotFoundError as exc:
            raise MediaStorageError("Media file was not found.") from exc
        except OSError as exc:
            raise MediaStorageError("Could not safely read private media file.") from exc

    def delete_image(self, media_id: str) -> bool:
        path = self._path_for(media_id)
        if path.is_symlink():
            raise MediaStorageError("Refusing to delete a symbolic link.")
        if not path.exists():
            return False
        try:
            path.unlink()
            directory_fd = os.open(self.root, os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
            return True
        except OSError as exc:
            raise MediaStorageError("Could not delete private media file.") from exc
