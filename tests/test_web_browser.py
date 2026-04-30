"""Tests for the web browser tool — no network required (mocked)."""
import pytest
from unittest.mock import patch, MagicMock
from tools.tool_web_browser import fetch_exchange_rates, search_employer_web, fetch_url


class TestFetchExchangeRates:
    def test_returns_required_keys(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"base_code": "LKR", "rates": {"USD": 0.003}}
        mock_resp.raise_for_status.return_value = None
        with patch("tools.tool_web_browser.httpx.get", return_value=mock_resp):
            r = fetch_exchange_rates("LKR")
        assert "base" in r and "rates" in r and "source" in r and "error" in r

    def test_returns_error_on_network_failure(self):
        with patch("tools.tool_web_browser.httpx.get", side_effect=Exception("timeout")):
            r = fetch_exchange_rates("LKR")
        assert r["error"] is not None
        assert r["rates"] == {}

    def test_error_field_is_none_on_success(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"base_code": "LKR", "rates": {"USD": 0.003}}
        mock_resp.raise_for_status.return_value = None
        with patch("tools.tool_web_browser.httpx.get", return_value=mock_resp):
            r = fetch_exchange_rates("LKR")
        assert r["error"] is None


class TestSearchEmployerWeb:
    def test_found_employer(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "Abstract": "Dialog Axiata is a leading telecom company.",
            "AbstractURL": "https://example.com",
        }
        mock_resp.raise_for_status.return_value = None
        with patch("tools.tool_web_browser.httpx.get", return_value=mock_resp):
            r = search_employer_web("Dialog Axiata PLC")
        assert r["found"] is True
        assert r["error"] is None

    def test_not_found_employer(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"Abstract": "", "AbstractURL": ""}
        mock_resp.raise_for_status.return_value = None
        with patch("tools.tool_web_browser.httpx.get", return_value=mock_resp):
            r = search_employer_web("Nonexistent Corp XYZ")
        assert r["found"] is False

    def test_network_error_returns_gracefully(self):
        with patch("tools.tool_web_browser.httpx.get", side_effect=Exception("timeout")):
            r = search_employer_web("Any Company")
        assert r["found"] is False
        assert r["error"] is not None

    def test_returns_required_keys(self):
        with patch("tools.tool_web_browser.httpx.get", side_effect=Exception("x")):
            r = search_employer_web("Test")
        for k in ("query","abstract","found","source_url","error"):
            assert k in r


class TestFetchUrl:
    def test_success(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = "OK response content"
        with patch("tools.tool_web_browser.httpx.get", return_value=mock_resp):
            r = fetch_url("https://example.com")
        assert r["status_code"] == 200
        assert r["error"] is None

    def test_failure(self):
        with patch("tools.tool_web_browser.httpx.get", side_effect=Exception("conn")):
            r = fetch_url("https://bad.url")
        assert r["error"] is not None
        assert r["status_code"] == 0
