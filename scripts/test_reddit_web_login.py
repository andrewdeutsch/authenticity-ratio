"""Attempt a reddit.com web login using credentials from .env.

This script tries to POST to the reddit login endpoint and reports whether a session cookie
was issued. It masks sensitive values in logs. Use only for quick diagnostics; it is not a full
browser automation and may fail if Reddit requires dynamic tokens or additional flows.
"""
from __future__ import annotations

import os
import sys
import time
from typing import Dict

import requests
from dotenv import load_dotenv


def mask(s: str | None) -> str:
    if not s:
        return "<missing>"
    if len(s) <= 4:
        return "*" * len(s)
    return s[:2] + "*" * (len(s) - 4) + s[-2:]


def load_env() -> Dict[str, str | None]:
    load_dotenv()
    return {
        "username": os.getenv("REDDIT_USERNAME"),
        "password": os.getenv("REDDIT_PASSWORD"),
        "user_agent": os.getenv("REDDIT_USER_AGENT", "ar-analyst-test/0.1 by unknown"),
    }


def try_web_login(username: str, password: str, user_agent: str) -> int:
    """Attempt to log into reddit.com via the legacy web endpoint.

    Returns HTTP status code of the final response. Note: reddit uses dynamic tokens and
    may block non-browser clients; this is only a heuristic check for credential validity.
    """
    session = requests.Session()
    session.headers.update({"User-Agent": user_agent})

    # Get the login page first to obtain any cookies and tokens
    login_page = session.get("https://www.reddit.com/login/", timeout=20)
    if login_page.status_code != 200:
        print(f"Could not fetch login page: {login_page.status_code}")
        return login_page.status_code

    # Reddit's login form uses a hidden 'csrf_token' value embedded in the HTML; try to extract it.
    html = login_page.text
    csrf_token = None
    # naive extraction; this may fail if markup changes
    for marker in ["csrf_token\" value=\"", "csrf_token\":\""]:
        idx = html.find(marker)
        if idx != -1:
            start = idx + len(marker)
            # value ends with a quote
            end = html.find('"', start)
            if end != -1:
                csrf_token = html[start:end]
                break

    data = {
        "username": username,
        "password": password,
    }
    if csrf_token:
        data["csrf_token"] = csrf_token

    # The real reddit login POST URL is /login, but requests from non-browser clients may
    # be blocked. We still attempt it as a diagnostic.
    time.sleep(0.5)
    resp = session.post("https://www.reddit.com/login/", data=data, timeout=20)

    # Check for reddit_session cookie as a sign of successful login
    cookies = session.cookies.get_dict()
    has_session = any(k.startswith("reddit_session") for k in cookies.keys())

    print("--- Web login diagnostic ---")
    print("Status:", resp.status_code)
    print("Attempted username:", mask(username))
    print("Password present:", bool(password))
    print("CSRF token extracted:", bool(csrf_token))
    print("Response headers (masked):")
    for k, v in resp.headers.items():
        if k.lower() in ("set-cookie",):
            print(f"  {k}: <cookie(s) present>")
        else:
            print(f"  {k}: {v}")
    print("Cookies returned (masked keys):", [k for k in cookies.keys()])
    print("Login session cookie present:", has_session)

    return resp.status_code


def main() -> int:
    env = load_env()
    username = env["username"]
    password = env["password"]
    user_agent = env["user_agent"]

    if not username or not password:
        print("REDDIT_USERNAME and REDDIT_PASSWORD must be set in .env")
        return 2

    try:
        code = try_web_login(username, password, user_agent)
        if code == 200:
            print("HTTP 200 received from login POST; check 'Login session cookie present' above.")
        else:
            print("Login POST returned non-200 status; this can still mean credentials are invalid or additional javascript checks are required.")
        return 0
    except Exception as e:
        print("Exception during web login test:", type(e).__name__, str(e))
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
