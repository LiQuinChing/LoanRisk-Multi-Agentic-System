# ============================================================
#  tools/tool_web_browser.py — Web browsing tool
#
#  Provides agents with the ability to fetch live data from
#  the public internet using free, no-key-required APIs.
#
#  Used by:
#    Agent 2 — fetches current market interest rates
#    Agent 3 — verifies employer existence via web search
# ============================================================

import httpx
from typing import Any, Dict
import logging
logger = logging.getLogger("LoanRiskMAS")


TIMEOUT = 8.0   # seconds — keeps the pipeline responsive


def fetch_exchange_rates(base_currency: str = "LKR") -> Dict[str, Any]:
    """
    Fetch current foreign exchange rates from the Open Exchange Rate API.

    Uses the free, no-API-key endpoint at open.er-api.com to retrieve
    the latest conversion rates relative to *base_currency*.  Results
    are used by Agent 2 to contextualise loan amounts against USD.

    Args:
        base_currency: ISO 4217 currency code for the base (default
                       ``"LKR"`` for Sri Lankan Rupee).

    Returns:
        Dict with keys ``"base"``, ``"rates"`` (sub-dict of currency
        codes to float rates), and ``"source"`` (the URL fetched).
        On network failure returns a fallback dict with
        ``"error"`` key set.

    Raises:
        No exception is raised — all errors are captured and returned
        in the ``"error"`` field so the pipeline continues uninterrupted.
    """
    
    url = f"https://open.er-api.com/v6/latest/{base_currency}"
    logger.info(f"  Targeting URL for exchange rates: {url}")
    try:
        resp = httpx.get(url, timeout=TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        return {
            "source":   url,
            "base":     data.get("base_code", base_currency),
            "rates":    data.get("rates", {}),
            "error":    None,
        }
    except Exception as exc:
        return {
            "source": url,
            "base":   base_currency,
            "rates":  {},
            "error":  str(exc),
        }


def search_employer_web(employer_name: str) -> Dict[str, Any]:
    """
    Perform a web lookup for an employer using the DuckDuckGo Instant
    Answer API — free, no API key, no rate-limit registration required.

    Attempts to find publicly available information about the company to
    assist Agent 3 in verifying whether the declared employer is a
    legitimate, traceable business entity.

    Args:
        employer_name: The employer name string from the loan application.

    Returns:
        Dict with keys:
            ``"query"``      — the search term used,
            ``"abstract"``   — short DuckDuckGo abstract (may be empty),
            ``"found"``      — bool, True if any abstract was returned,
            ``"source_url"`` — URL of the result source,
            ``"error"``      — error string or None.

    Raises:
        No exception raised — errors returned in ``"error"`` field.
    """
    query = f"{employer_name} company Sri Lanka"
    url   = "https://api.duckduckgo.com/"
    params = {
        "q":              query,
        "format":         "json",
        "no_html":        "1",
        "skip_disambig":  "1",
    }
    try:
        resp = httpx.get(url, params=params, timeout=TIMEOUT)
        resp.raise_for_status()
        data     = resp.json()
        abstract = data.get("Abstract", "").strip()
        return {
            "query":      query,
            "abstract":   abstract,
            "found":      bool(abstract),
            "source_url": data.get("AbstractURL", ""),
            "error":      None,
        }
    except Exception as exc:
        return {
            "query":      query,
            "abstract":   "",
            "found":      False,
            "source_url": "",
            "error":      str(exc),
        }


def fetch_url(url: str) -> Dict[str, Any]:
    """
    Generic HTTP GET fetcher with a safe timeout.

    Used for ad-hoc web lookups where a specific free endpoint is
    known in advance.  Returns the raw response text so the calling
    agent can parse it as needed.

    Args:
        url: Fully qualified HTTPS URL to fetch.

    Returns:
        Dict with ``"url"``, ``"status_code"``, ``"text"`` (response
        body as string), and ``"error"`` (None on success).
    """
    try:
        resp = httpx.get(url, timeout=TIMEOUT, follow_redirects=True)
        return {
            "url":         url,
            "status_code": resp.status_code,
            "text":        resp.text[:2000],   # cap at 2 KB
            "error":       None,
        }
    except Exception as exc:
        return {
            "url":         url,
            "status_code": 0,
            "text":        "",
            "error":       str(exc),
        }
