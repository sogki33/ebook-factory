"""License checks against a mocked Gumroad API (no network)."""
import io
import json
import time

import pytest

from ebookfactory import licensing as lic


class FakeResp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def fake_gumroad(payload):
    def _open(req, timeout=0):
        return FakeResp(json.dumps(payload).encode())
    return _open


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.delenv("EBOOKFACTORY_KEY", raising=False)


def test_no_key_is_preview():
    assert lic.is_pro() is False


def test_activate_valid_key(monkeypatch):
    monkeypatch.setattr(lic.urllib.request, "urlopen", fake_gumroad({"success": True, "purchase": {"email": "a@b.c"}}))
    ok, msg = lic.activate("KEY-1")
    assert ok and msg == "a@b.c"
    assert lic.is_pro() is True


def test_refunded_key_rejected(monkeypatch):
    monkeypatch.setattr(lic.urllib.request, "urlopen", fake_gumroad({"success": True, "purchase": {"refunded": True}}))
    ok, msg = lic.activate("KEY-2")
    assert not ok and "refunded" in msg
    assert lic.is_pro() is False


def test_invalid_key_rejected(monkeypatch):
    monkeypatch.setattr(lic.urllib.request, "urlopen", fake_gumroad({"success": False, "message": "That license does not exist."}))
    ok, _ = lic.activate("NOPE")
    assert not ok


def test_offline_grace(monkeypatch):
    lic._save_cache({"key": "KEY-3", "verified_at": time.time() - 5 * 24 * 3600})

    def down(req, timeout=0):
        raise OSError("offline")
    monkeypatch.setattr(lic.urllib.request, "urlopen", down)
    assert lic.is_pro() is True  # verified 5 days ago, inside the 30-day grace
    lic._save_cache({"key": "KEY-3", "verified_at": time.time() - 40 * 24 * 3600})
    assert lic.is_pro() is False  # grace expired
