"""Tests de core/hydraulics/pumping_library.py — mockea requests, nunca
toca la red real."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from core.hydraulics.pumping_library import (
    LibraryConfig,
    delete_case,
    get_library_config,
    get_owner_key,
    list_cases,
    save_case,
)


def _fake_streamlit_secrets(monkeypatch, url="https://x.supabase.co", key="anon-key"):
    import core.hydraulics.pumping_library as lib

    fake_secrets = {"SUPABASE_URL": url, "SUPABASE_ANON_KEY": key} if url else {}
    monkeypatch.setattr(lib.st, "secrets", fake_secrets, raising=False)


def test_get_library_config_returns_none_without_secrets(monkeypatch):
    _fake_streamlit_secrets(monkeypatch, url=None, key=None)
    assert get_library_config() is None


def test_get_library_config_reads_secrets(monkeypatch):
    _fake_streamlit_secrets(monkeypatch)
    config = get_library_config()
    assert config == LibraryConfig(url="https://x.supabase.co", api_key="anon-key")


def test_get_owner_key_generates_and_persists_in_query_params(monkeypatch):
    import core.hydraulics.pumping_library as lib

    fake_params = {}
    monkeypatch.setattr(lib.st, "query_params", fake_params, raising=False)
    owner = get_owner_key()
    assert fake_params["owner"] == owner
    # segunda llamada reusa el mismo owner, no genera uno nuevo
    assert get_owner_key() == owner


def test_save_case_without_config_fails_cleanly(monkeypatch):
    _fake_streamlit_secrets(monkeypatch, url=None, key=None)
    ok, message = save_case("owner-1", "Caso", {"a": 1}, 10.0, 20.0, 5.0)
    assert not ok
    assert "no configurada" in message.lower()


def test_save_case_posts_expected_payload(monkeypatch):
    _fake_streamlit_secrets(monkeypatch)
    mock_resp = MagicMock(status_code=201, text="")
    with patch("core.hydraulics.pumping_library.requests.post", return_value=mock_resp) as mock_post:
        ok, message = save_case("owner-1", "Caso X", {"a": 1}, 10.0, 20.0, 5.0)
    assert ok
    args, kwargs = mock_post.call_args
    assert args[0] == "https://x.supabase.co/rest/v1/pumping_cases"
    assert kwargs["json"]["owner_key"] == "owner-1"
    assert kwargs["json"]["project_name"] == "Caso X"
    assert kwargs["json"]["case_json"] == {"a": 1}
    assert kwargs["headers"]["apikey"] == "anon-key"


def test_save_case_reports_http_error(monkeypatch):
    _fake_streamlit_secrets(monkeypatch)
    mock_resp = MagicMock(status_code=401, text="unauthorized")
    with patch("core.hydraulics.pumping_library.requests.post", return_value=mock_resp):
        ok, message = save_case("owner-1", "Caso", {}, None, None, None)
    assert not ok
    assert "401" in message


def test_list_cases_filters_by_owner(monkeypatch):
    _fake_streamlit_secrets(monkeypatch)
    mock_resp = MagicMock(status_code=200)
    mock_resp.json.return_value = [{"id": "1", "project_name": "Caso"}]
    with patch("core.hydraulics.pumping_library.requests.get", return_value=mock_resp) as mock_get:
        cases, error = list_cases("owner-1")
    assert error is None
    assert cases == [{"id": "1", "project_name": "Caso"}]
    assert mock_get.call_args.kwargs["params"]["owner_key"] == "eq.owner-1"


def test_list_cases_without_config_returns_empty_no_error(monkeypatch):
    _fake_streamlit_secrets(monkeypatch, url=None, key=None)
    cases, error = list_cases("owner-1")
    assert cases == []
    assert error is None


def test_delete_case_scopes_to_owner(monkeypatch):
    _fake_streamlit_secrets(monkeypatch)
    mock_resp = MagicMock(status_code=204)
    with patch("core.hydraulics.pumping_library.requests.delete", return_value=mock_resp) as mock_delete:
        ok, message = delete_case("owner-1", "case-123")
    assert ok
    params = mock_delete.call_args.kwargs["params"]
    assert params["id"] == "eq.case-123"
    assert params["owner_key"] == "eq.owner-1"
