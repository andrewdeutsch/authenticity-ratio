"""
Test Reddit OAuth token endpoint using client_id/client_secret from environment.
Prints status and a masked JSON response to avoid echoing secrets.

Run with: ./.venv/bin/python scripts/test_reddit_token.py
"""
import os
import sys
import base64
import json
import requests
from dotenv import load_dotenv

# Load .env explicitly
load_dotenv('.env')

client_id = os.getenv('REDDIT_CLIENT_ID')
client_secret = os.getenv('REDDIT_CLIENT_SECRET')
username = os.getenv('REDDIT_USERNAME')
password = os.getenv('REDDIT_PASSWORD')
user_agent = os.getenv('REDDIT_USER_AGENT', 'AR-Tool/1.0')

if not client_id or not client_secret:
    print("Missing REDDIT_CLIENT_ID or REDDIT_CLIENT_SECRET in environment (.env).")
    sys.exit(2)

def _print_masked(resp):
    try:
        j = resp.json()
    except Exception:
        j = {'text': resp.text}
    masked = {}
    if isinstance(j, dict):
        for k, v in j.items():
            if k in ('access_token', 'refresh_token'):
                masked[k] = '<REDACTED>'
            else:
                masked[k] = v
    else:
        masked = j
    print('Response:', json.dumps(masked, indent=2))

def attempt_client_credentials():
    print('\n--- Attempting client_credentials grant (app-only) ---')
    creds = f"{client_id}:{client_secret}".encode('utf-8')
    auth = base64.b64encode(creds).decode('utf-8')
    headers = {'Authorization': f'Basic {auth}', 'User-Agent': user_agent}
    data = {'grant_type': 'client_credentials'}
    try:
        resp = requests.post('https://www.reddit.com/api/v1/access_token', headers=headers, data=data, timeout=10)
        print('HTTP', resp.status_code)
        _print_masked(resp)
        return resp.status_code == 200
    except Exception as e:
        print('ERROR during client_credentials attempt:', str(e))
        return False

def attempt_password_grant():
    print('\n--- Attempting password grant (client+username+password) ---')
    if not username or not password:
        print('No REDDIT_USERNAME/REDDIT_PASSWORD found in .env; skipping password grant')
        return False
    headers = {'User-Agent': user_agent}
    try:
        resp = requests.post('https://www.reddit.com/api/v1/access_token', headers=headers, auth=(client_id, client_secret), data={'grant_type': 'password', 'username': username, 'password': password}, timeout=10)
        print('HTTP', resp.status_code)
        _print_masked(resp)
        return resp.status_code == 200
    except Exception as e:
        print('ERROR during password grant attempt:', str(e))
        return False

# Try password grant first (preferred for script apps), then fall back to client_credentials
ok = False
if username and password:
    ok = attempt_password_grant()
    if not ok:
        print('Password grant failed; trying client_credentials as fallback...')
        ok = attempt_client_credentials()
else:
    ok = attempt_client_credentials()

if ok:
    print('\nSUCCESS: obtained token (masked above)')
    sys.exit(0)
else:
    print('\nFAILED: could not obtain token with available methods')
    sys.exit(1)
