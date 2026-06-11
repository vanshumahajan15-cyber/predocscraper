"""HTTP helpers with exponential backoff retry and SSL fallback."""

from __future__ import annotations

import logging
import ssl
import time
import urllib.error
import urllib.request
from typing import Dict

import certifi
import requests

from config import (
    HTTP_MAX_RETRIES,
    HTTP_RETRY_BASE_DELAY,
    REQUEST_TIMEOUT,
    SSL_VERIFY,
    USER_AGENT,
)

logger = logging.getLogger(__name__)

DEFAULT_HEADERS: Dict[str, str] = {"User-Agent": USER_AGENT}


def fetch_html(url: str, headers: Dict[str, str] | None = None) -> str:
    """Fetch page HTML with retries, falling back to urllib on SSL errors."""
    request_headers = {**DEFAULT_HEADERS, **(headers or {})}
    last_error: Exception | None = None

    for attempt in range(HTTP_MAX_RETRIES):
        try:
            return _fetch_with_requests(url, request_headers)
        except requests.exceptions.SSLError:
            logger.warning(
                "SSL verification failed for %s (attempt %d/%d); using urllib fallback.",
                url,
                attempt + 1,
                HTTP_MAX_RETRIES,
            )
            try:
                return _fetch_with_urllib(url, request_headers, verify=False)
            except Exception as urllib_exc:
                last_error = urllib_exc
        except requests.RequestException as exc:
            last_error = exc
            if attempt < HTTP_MAX_RETRIES - 1:
                delay = HTTP_RETRY_BASE_DELAY * (2**attempt)
                logger.warning(
                    "Request failed for %s (attempt %d/%d): %s. Retrying in %.1fs.",
                    url,
                    attempt + 1,
                    HTTP_MAX_RETRIES,
                    exc,
                    delay,
                )
                time.sleep(delay)
            else:
                logger.error(
                    "Request failed for %s after %d attempts: %s",
                    url,
                    HTTP_MAX_RETRIES,
                    exc,
                )

    if last_error:
        raise last_error
    raise RuntimeError(f"Failed to fetch {url}")


def _fetch_with_requests(url: str, headers: Dict[str, str]) -> str:
    response = requests.get(
        url,
        headers=headers,
        timeout=REQUEST_TIMEOUT,
        verify=certifi.where() if SSL_VERIFY else False,
    )
    response.raise_for_status()
    response.encoding = response.apparent_encoding or "utf-8"
    return response.text


def _fetch_with_urllib(
    url: str,
    headers: Dict[str, str],
    verify: bool | None = None,
) -> str:
    """Fallback fetch path when the local certificate store is incomplete."""
    should_verify = SSL_VERIFY if verify is None else verify
    last_error: Exception | None = None

    for attempt in range(HTTP_MAX_RETRIES):
        context = ssl.create_default_context()
        if should_verify:
            try:
                context.load_verify_locations(certifi.where())
            except Exception:
                context.check_hostname = False
                context.verify_mode = ssl.CERT_NONE
        else:
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE

        request = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(
                request, context=context, timeout=REQUEST_TIMEOUT
            ) as response:
                raw = response.read()
                charset = response.headers.get_content_charset() or "utf-8"
                return raw.decode(charset, errors="replace")
        except urllib.error.URLError as exc:
            last_error = exc
            if attempt < HTTP_MAX_RETRIES - 1:
                delay = HTTP_RETRY_BASE_DELAY * (2**attempt)
                logger.warning(
                    "urllib fallback failed for %s (attempt %d/%d): %s. Retrying in %.1fs.",
                    url,
                    attempt + 1,
                    HTTP_MAX_RETRIES,
                    exc,
                    delay,
                )
                time.sleep(delay)

    if last_error:
        raise last_error
    raise RuntimeError(f"Failed to fetch {url} via urllib")
