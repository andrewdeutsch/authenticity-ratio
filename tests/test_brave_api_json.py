import json
from unittest import mock

from ingestion import brave_search


def make_resp(json_obj):
    class DummyResp:
        status_code = 200
        def json(self):
            return json_obj
        @property
        def text(self):
            # Import inside to avoid any test-level shadowing of the json name
            import json as _json
            return _json.dumps(self.json())
    return DummyResp()


def test_brave_parses_web_results(monkeypatch):
    body = {
        'web': {
            'results': [
                {'url': 'http://example.com/1', 'title': 'One', 'description': 'first'},
                {'url': 'http://example.com/2', 'title': 'Two', 'description': 'second'},
            ]
        }
    }

    monkeypatch.setattr('ingestion.brave_search.requests.get', lambda *a, **k: make_resp(body))
    # Ensure API key present so API path is used
    import os
    os.environ['BRAVE_API_KEY'] = 'dummy'
    res = brave_search.search_brave('q', size=5)
    assert isinstance(res, list)
    assert res[0]['url'] == 'http://example.com/1'


def test_brave_parses_top_level_results(monkeypatch):
    body = {'results': [{'url': 'http://x.com', 'title': 'X'}]}
    monkeypatch.setattr('ingestion.brave_search.requests.get', lambda *a, **k: make_resp(body))
    import os
    os.environ['BRAVE_API_KEY'] = 'dummy'
    res = brave_search.search_brave('q', size=3)
    assert res and res[0]['url'] == 'http://x.com'
