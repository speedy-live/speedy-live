from io import BytesIO

import pytest
from PIL import Image

from app.media_validation import (
    MAX_IMAGE_BYTES,
    ImageValidationError,
    validate_image_bytes,
)


def make_image(fmt="JPEG", size=(320, 240)):
    output = BytesIO()
    Image.new("RGB", size, (20, 80, 120)).save(output, format=fmt)
    return output.getvalue()


@pytest.mark.parametrize("fmt", ["JPEG", "PNG", "WEBP"])
def test_accepts_supported_decodable_image_formats(fmt):
    data = make_image(fmt)
    result = validate_image_bytes(data)
    assert result.format == fmt
    assert (result.width, result.height) == (320, 240)
    assert result.byte_count == len(data)
    assert result.frame_count == 1


def test_rejects_empty_or_non_image_bytes():
    for data in (b"", b"not an image"):
        with pytest.raises(ImageValidationError):
            validate_image_bytes(data)


def test_rejects_svg_and_other_unsupported_formats():
    with pytest.raises(ImageValidationError, match="Only JPEG"):
        validate_image_bytes(b"<svg></svg>")


def test_rejects_images_below_minimum_dimensions():
    with pytest.raises(ImageValidationError, match="64 by 64"):
        validate_image_bytes(make_image(size=(32, 200)))


def test_rejects_images_above_pixel_limit():
    # Header is sufficient for dimension rejection; no huge pixel buffer is created.
    output = BytesIO()
    Image.new("RGB", (1, 1)).save(output, format="PNG")
    data = bytearray(output.getvalue())
    # PNG IHDR width and height are bytes 16..24.
    data[16:20] = (6000).to_bytes(4, "big")
    data[20:24] = (5000).to_bytes(4, "big")
    import zlib
    # Rebuild valid IHDR CRC so the decoder reaches dimension validation.
    ihdr = bytes(data[12:29])
    data[29:33] = zlib.crc32(ihdr).to_bytes(4, "big")
    with pytest.raises(ImageValidationError, match="25-megapixel"):
        validate_image_bytes(bytes(data))


def test_rejects_oversized_upload_before_decoding():
    with pytest.raises(ImageValidationError, match="10 MiB"):
        validate_image_bytes(b"x" * (MAX_IMAGE_BYTES + 1))


def test_rejects_corrupted_image():
    data = bytearray(make_image("PNG"))
    data[-8:] = b"badbytes"
    with pytest.raises(ImageValidationError):
        validate_image_bytes(bytes(data))
