from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image

from app.media_storage import MediaStorageError, PrivateLocalMediaStore


def image_bytes(fmt="JPEG"):
    output = BytesIO()
    Image.new("RGB", (160, 120), (40, 90, 130)).save(output, format=fmt)
    return output.getvalue()


@pytest.mark.parametrize(
    ("fmt", "content_type"),
    [("JPEG", "image/jpeg"), ("PNG", "image/png"), ("WEBP", "image/webp")],
)
def test_store_read_and_delete_image(tmp_path, fmt, content_type):
    store = PrivateLocalMediaStore(tmp_path / "private-media")
    stored = store.put_image(image_bytes(fmt))

    assert len(stored.media_id) == 32
    assert stored.content_type == content_type
    assert store.read_image(stored.media_id) == image_bytes(fmt)
    assert store.delete_image(stored.media_id) is True
    assert store.delete_image(stored.media_id) is False


def test_storage_directory_and_files_have_private_permissions(tmp_path):
    store = PrivateLocalMediaStore(tmp_path / "private-media")
    stored = store.put_image(image_bytes())
    path = next((tmp_path / "private-media").glob(f"{stored.media_id}.*"))

    assert (tmp_path / "private-media").stat().st_mode & 0o777 == 0o700
    assert path.stat().st_mode & 0o777 == 0o600


@pytest.mark.parametrize("media_id", ["../secret", "a" * 31, "A" * 32, "", None])
def test_rejects_untrusted_or_malformed_media_ids(tmp_path, media_id):
    store = PrivateLocalMediaStore(tmp_path / "private-media")
    with pytest.raises(MediaStorageError, match="Invalid media identifier"):
        store.read_image(media_id)


def test_rejects_invalid_image_before_writing(tmp_path):
    store = PrivateLocalMediaStore(tmp_path / "private-media")
    with pytest.raises(ValueError):
        store.put_image(b"not an image")
    assert list((tmp_path / "private-media").iterdir()) == []


def test_missing_media_returns_not_found_error(tmp_path):
    store = PrivateLocalMediaStore(tmp_path / "private-media")
    with pytest.raises(MediaStorageError, match="not found"):
        store.read_image("a" * 32)


def test_rejects_storage_root_symlink(tmp_path):
    real = tmp_path / "real"
    real.mkdir()
    link = tmp_path / "link"
    link.symlink_to(real, target_is_directory=True)
    with pytest.raises(MediaStorageError, match="symbolic link"):
        PrivateLocalMediaStore(link)


def test_store_generates_unpredictable_distinct_ids(tmp_path):
    store = PrivateLocalMediaStore(tmp_path / "private-media")
    first = store.put_image(image_bytes())
    second = store.put_image(image_bytes())
    assert first.media_id != second.media_id


def test_read_refuses_media_symlink(tmp_path):
    store = PrivateLocalMediaStore(tmp_path / "private-media")
    outside = tmp_path / "outside.jpg"
    outside.write_bytes(image_bytes())
    media_id = "b" * 32
    (tmp_path / "private-media" / f"{media_id}.jpg").symlink_to(outside)
    with pytest.raises(MediaStorageError):
        store.read_image(media_id)


def test_read_refuses_non_regular_media_file(tmp_path):
    store = PrivateLocalMediaStore(tmp_path / "private-media")
    media_id = "c" * 32
    (tmp_path / "private-media" / f"{media_id}.jpg").mkdir()
    with pytest.raises(MediaStorageError):
        store.read_image(media_id)
