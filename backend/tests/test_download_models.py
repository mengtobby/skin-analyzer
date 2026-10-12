"""Offline model integrity and bounded-download tests."""
import hashlib
import io

import pytest

from skin_analyzer import download_models


def test_pinned_digest() -> None:
    assert download_models.EXPECTED_SHA256 == (
        "64184e229b263107bc2b804c6625db1341ff2bb731874b0bcc2fe6544e0bc9ff")


@pytest.mark.parametrize("existing", [False, True])
def test_verified_download_and_cache(tmp_path, monkeypatch, caplog, existing):
    data = b"verified model fixture"
    target = tmp_path / "face_landmarker.task"
    if existing:
        target.write_bytes(b"corrupt")
    calls = []

    def response(*args, **kwargs):
        calls.append(args)
        return io.BytesIO(data)
    monkeypatch.setattr(download_models, "EXPECTED_SHA256", hashlib.sha256(data).hexdigest())
    monkeypatch.setattr(download_models.urllib.request, "urlopen", response)
    assert download_models.ensure_models(tmp_path) == target
    assert target.read_bytes() == data
    assert list(tmp_path.iterdir()) == [target]
    assert download_models.ensure_models(tmp_path) == target
    assert len(calls) == 1
    if existing:
        assert "failed SHA-256 verification" in caplog.text


def test_wrong_digest_removes_temp_and_preserves_existing(tmp_path, monkeypatch):
    target = tmp_path / "face_landmarker.task"
    target.write_bytes(b"old")
    monkeypatch.setattr(download_models.urllib.request, "urlopen",
                        lambda *a, **k: io.BytesIO(b"wrong"))
    with pytest.raises(RuntimeError, match="SHA-256 mismatch"):
        download_models.ensure_models(tmp_path)
    assert target.read_bytes() == b"old"
    assert list(tmp_path.iterdir()) == [target]


def test_oversized_download_removes_temp(tmp_path, monkeypatch):
    monkeypatch.setattr(download_models, "MAX_MODEL_BYTES", 4)
    monkeypatch.setattr(download_models.urllib.request, "urlopen",
                        lambda *a, **k: io.BytesIO(b"12345"))
    with pytest.raises(RuntimeError, match="size limit"):
        download_models.ensure_models(tmp_path)
    assert not list(tmp_path.iterdir())
