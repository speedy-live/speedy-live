"""Strict in-memory image validation for a future authenticated upload service.

No file is written, stored, or served by this module. Call only after request-size
limits are enforced at the HTTP/proxy boundary.
"""
from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
import warnings

from PIL import Image, UnidentifiedImageError


MAX_IMAGE_BYTES = 10 * 1024 * 1024
MAX_IMAGE_PIXELS = 25_000_000
MIN_IMAGE_SIDE = 64
ALLOWED_FORMATS = frozenset({"JPEG", "PNG", "WEBP"})


class ImageValidationError(ValueError):
    """Raised when an uploaded image is unsafe or unsupported."""


@dataclass(frozen=True)
class ValidatedImage:
    format: str
    width: int
    height: int
    byte_count: int
    frame_count: int


def validate_image_bytes(data: bytes) -> ValidatedImage:
    """Decode and validate actual image content; never trust filename or MIME type."""
    if not isinstance(data, bytes) or not data:
        raise ImageValidationError("Image data is empty or invalid.")
    if len(data) > MAX_IMAGE_BYTES:
        raise ImageValidationError("Image exceeds the 10 MiB upload limit.")

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(data)) as image:
                image_format = image.format
                width, height = image.size
                frame_count = getattr(image, "n_frames", 1)

                if image_format not in ALLOWED_FORMATS:
                    raise ImageValidationError("Only JPEG, PNG, and WebP images are supported.")
                if width < MIN_IMAGE_SIDE or height < MIN_IMAGE_SIDE:
                    raise ImageValidationError("Image dimensions must be at least 64 by 64 pixels.")
                if width * height > MAX_IMAGE_PIXELS:
                    raise ImageValidationError("Image exceeds the 25-megapixel safety limit.")
                if frame_count != 1:
                    raise ImageValidationError("Animated or multi-frame images are not supported.")

                image.verify()

            # verify() checks file structure; reopen and fully decode the pixels too.
            with Image.open(BytesIO(data)) as decoded:
                decoded.load()
                if decoded.format != image_format or decoded.size != (width, height):
                    raise ImageValidationError("Image changed during validation.")

    except ImageValidationError:
        raise
    except (UnidentifiedImageError, OSError, SyntaxError, Image.DecompressionBombError,
            Image.DecompressionBombWarning) as exc:
        raise ImageValidationError("Image is malformed, truncated, or unsafe to decode.") from exc

    return ValidatedImage(
        format=image_format,
        width=width,
        height=height,
        byte_count=len(data),
        frame_count=frame_count,
    )
