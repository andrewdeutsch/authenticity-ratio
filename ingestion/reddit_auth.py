"""Helper for obtaining Reddit OAuth tokens (password grant preferred).

Provides a small helper that attempts password grant when username/password are
available, falls back to client_credentials, masks logs, and retries once on
server/transient errors.
"""
from __future__ import annotations

import base64
import logging
import os
import time
from typing import Optional, Tuple

import requests

logger = logging.getLogger(__name__)


def _mask(s: Optional[str]) -> str:
    if not s:
        return "<missing>"
    if len(s) <= 4:
        return "*" * len(s)
    return s[:2] + "*" * (len(s) - 4) + s[-2:]


def _basic_auth_header(client_id: str, client_secret: str) -> str:
    auth = f"{client_id}:{client_secret}".encode("utf-8")
    return "Basic " + base64.b64encode(auth).decode("ascii")


def obtain_token(retries: int = 1, backoff: float = 0.5) -> Tuple[Optional[str], dict]:
    """Attempt to obtain a Reddit OAuth token.

    Returns (access_token or None, raw_response_dict)
    """
    client_id = os.getenv("REDDIT_CLIENT_ID")
    client_secret = os.getenv("REDDIT_CLIENT_SECRET")
    user_agent = os.getenv("REDDIT_USER_AGENT", "ar-tool/0.1")
    username = os.getenv("REDDIT_USERNAME")
    password = os.getenv("REDDIT_PASSWORD")

    logger.info("Reddit auth: client_id=%s user_agent=%s", _mask(client_id), user_agent)

    token_url = "https://www.reddit.com/api/v1/access_token"

    headers = {"User-Agent": user_agent}

    attempts = 0
    while attempts <= retries:
        attempts += 1

        # Prefer password grant if credentials present
        if username and password:
            data = {"grant_type": "password", "username": username, "password": password}
            auth_header = _basic_auth_header(client_id or "", client_secret or "")
            headers_local = headers.copy()
            headers_local["Authorization"] = auth_header
            try:
                resp = requests.post(token_url, data=data, headers=headers_local, timeout=10)
            except Exception as e:
                logger.warning("Reddit auth request failed: %s", e)
                resp = None
        else:
            # App-only
            data = {"grant_type": "client_credentials"}
            auth_header = _basic_auth_header(client_id or "", client_secret or "")
            headers_local = headers.copy()
            headers_local["Authorization"] = auth_header
            try:
                resp = requests.post(token_url, data=data, headers=headers_local, timeout=10)
            except Exception as e:
                logger.warning("Reddit auth request failed: %s", e)
                resp = None

        if resp is None:
            if attempts <= retries:
                time.sleep(backoff)
                backoff *= 2
                continue
            return None, {"error": "request_failed"}

        try:
            body = resp.json()
        except Exception:
            body = {"status_code": resp.status_code, "text": resp.text}

        if resp.status_code == 200 and "access_token" in body:
            logger.info("Reddit auth successful: token acquired (masked)")
            return body.get("access_token"), body

        # Log masked diagnostics
        logger.warning(
            "Reddit auth attempt %s failed: status=%s body=%s",
            attempts,
            resp.status_code,
            {k: (v if k != 'access_token' else _mask(v)) for k, v in (body.items() if isinstance(body, dict) else [])},
        )

        if attempts <= retries:
            time.sleep(backoff)
            backoff *= 2

    return None, body if isinstance(body, dict) else {"error": "unknown"}
