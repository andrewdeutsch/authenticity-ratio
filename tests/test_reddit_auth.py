import os

import pytest


def make_response(status_code=200, json_data=None, text=""):
    class Resp:
        def __init__(self, status_code, json_data, text):
            self.status_code = status_code
            self._json = json_data
            self.text = text

        def json(self):
            if self._json is None:
                raise ValueError("no json")
            return self._json

    return Resp(status_code, json_data, text)


def test_obtain_token_success(monkeypatch, tmp_path):
    # Arrange: set env vars
    os.environ["REDDIT_CLIENT_ID"] = "cid"
    os.environ["REDDIT_CLIENT_SECRET"] = "csecret"
    os.environ["REDDIT_USER_AGENT"] = "test-agent"
    os.environ["REDDIT_USERNAME"] = "user"
    os.environ["REDDIT_PASSWORD"] = "pass"

    import ingestion.reddit_auth as ra

    def fake_post(url, data, headers, timeout):
        # Simulate successful password grant
        return make_response(200, {"access_token": "abcd", "token_type": "bearer"}, "ok")

    monkeypatch.setattr(ra.requests, "post", fake_post)

    token, resp = ra.obtain_token()
    assert token == "abcd"
    assert isinstance(resp, dict)


def test_obtain_token_failure_then_fallback(monkeypatch):
    # Simulate password grant rejected and client_credentials accepted
    import ingestion.reddit_auth as ra

    calls = {"n": 0}

    def fake_post(url, data, headers, timeout):
        calls["n"] += 1
        if data.get("grant_type") == "password":
            return make_response(401, {"error": "unauthorized_client"}, "unauth")
        return make_response(200, {"access_token": "apptoken"}, "ok")

    monkeypatch.setattr(ra.requests, "post", fake_post)
    # Clear username/password to force fallback path after first attempt
    os.environ.pop("REDDIT_USERNAME", None)
    os.environ.pop("REDDIT_PASSWORD", None)
    os.environ["REDDIT_CLIENT_ID"] = "cid"
    os.environ["REDDIT_CLIENT_SECRET"] = "csecret"
    os.environ["REDDIT_USER_AGENT"] = "test-agent"

    token, resp = ra.obtain_token()
    assert token == "apptoken"
