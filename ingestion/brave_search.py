"""Brave Search ingestion module

Provides a simple wrapper to query Brave Search (via their search endpoint) and fetch page content for selected URLs.

Note: Brave does not have a public REST API for search results like Google; this module uses the Brave Search HTML endpoint as a lightweight approach. In production, consider using a proper search API or a licensed data provider.
"""
from __future__ import annotations

import logging
import requests
from typing import List, Dict
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import os
import json
import time

# Rate limiting: minimum interval (seconds) between outbound Brave requests
_BRAVE_REQUEST_INTERVAL = float(os.getenv('BRAVE_REQUEST_INTERVAL', '1.0'))
_LAST_BRAVE_REQUEST_TS = 0.0


def _wait_for_rate_limit():
    """Ensure at least _BRAVE_REQUEST_INTERVAL seconds between requests."""
    global _LAST_BRAVE_REQUEST_TS
    if _BRAVE_REQUEST_INTERVAL <= 0:
        return
    now = time.monotonic()
    elapsed = now - _LAST_BRAVE_REQUEST_TS
    if elapsed < _BRAVE_REQUEST_INTERVAL:
        to_sleep = _BRAVE_REQUEST_INTERVAL - elapsed
        time.sleep(to_sleep)
    _LAST_BRAVE_REQUEST_TS = time.monotonic()

# Optional Playwright import (used only if the environment opts in)
try:
    from playwright.sync_api import sync_playwright
    _PLAYWRIGHT_AVAILABLE = True
except Exception:
    _PLAYWRIGHT_AVAILABLE = False

logger = logging.getLogger(__name__)

BRAVE_SEARCH_URL = "https://search.brave.com/search"


def search_brave(query: str, size: int = 10) -> List[Dict[str, str]]:
    """Search Brave and return a list of result dicts {title, url, snippet}"""
    # If user has provided a Brave API key, prefer the API endpoint
    api_key = os.getenv('BRAVE_API_KEY')
    api_endpoint = os.getenv('BRAVE_API_ENDPOINT', 'https://api.search.brave.com/res/v1/web/search')
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    if api_key:
        # Use a single auth method to avoid multiple attempts per logical search.
        # Configure via BRAVE_API_AUTH: 'x-api-key' (default), 'bearer', 'both', 'query-param', or 'subscription-token'
        api_auth = os.getenv('BRAVE_API_AUTH', 'subscription-token')
        params = {"q": query, "count": size}
        try:
            hdrs = headers.copy()
            if api_auth == 'bearer':
                hdrs['Authorization'] = f'Bearer {api_key}'
            elif api_auth == 'x-api-key':
                hdrs['x-api-key'] = api_key
            elif api_auth == 'subscription-token':
                # Brave uses X-Subscription-Token for the provided key in many cases
                hdrs['X-Subscription-Token'] = api_key
            elif api_auth == 'both':
                hdrs['Authorization'] = f'Bearer {api_key}'
                hdrs['x-api-key'] = api_key

            # Prepare request (if query-param auth, append below)
            _wait_for_rate_limit()
            if api_auth == 'query-param':
                params_with_key = params.copy()
                params_with_key['apikey'] = api_key
                resp = requests.get(api_endpoint, params=params_with_key, headers=hdrs, timeout=10)
            else:
                resp = requests.get(api_endpoint, params=params, headers=hdrs, timeout=10)

            if resp.status_code == 200:
                try:
                    body = resp.json()
                except json.JSONDecodeError:
                    logger.warning('Brave API returned non-JSON response; falling back to HTML parsing')
                    body = None

                results = []
                if isinstance(body, dict):
                    # Preferred: Brave API uses body['web']['results'] for web search results
                    web_results = None
                    if 'web' in body and isinstance(body['web'], dict):
                        web_results = body['web'].get('results')

                    if isinstance(web_results, list):
                        for item in web_results[:size]:
                            if not isinstance(item, dict):
                                continue
                            url = item.get('url') or (item.get('meta_url') or {}).get('url') or item.get('link')
                            title = item.get('title') or item.get('name') or item.get('headline') or ''
                            snippet = item.get('description') or item.get('snippet') or ''
                            if url and url.startswith('http'):
                                results.append({'title': title, 'url': url, 'snippet': snippet})
                        if results:
                            return results

                    # Fallback heuristics: look for top-level lists
                    for key in ('results', 'organic', 'items', 'data'):
                        if key in body and isinstance(body[key], list):
                            for item in body[key][:size]:
                                if not isinstance(item, dict):
                                    continue
                                url = item.get('url') or item.get('link') or item.get('href') or item.get('target')
                                title = item.get('title') or item.get('name') or ''
                                snippet = item.get('snippet') or item.get('description') or ''
                                if url and url.startswith('http'):
                                    results.append({'title': title, 'url': url, 'snippet': snippet})
                            if results:
                                return results

                logger.debug('Brave API response did not contain usable results')
            else:
                body_text = getattr(resp, 'text', '')[:1000]
                logger.warning('Brave API request failed: %s %s', resp.status_code, body_text)
        except Exception as e:
            logger.warning('Brave API request error: %s; falling back to HTML scraping', e)
        # If API key exists, do not fallback to HTML scraping unless explicitly enabled.
        allow_html = os.getenv('BRAVE_ALLOW_HTML_FALLBACK', '0') == '1'
        if not allow_html:
            # Return whatever results we have (possibly empty) and avoid HTML scraping
            return results

    # Fallback to HTML scraping (only when API key is not present or fallback explicitly enabled)
    params = {"q": query, "source": "web", "count": size}
    _wait_for_rate_limit()
    resp = requests.get(BRAVE_SEARCH_URL, params=params, headers=headers, timeout=10)
    if resp.status_code != 200:
        logger.error("Brave Search request failed: %s", resp.status_code)
        return []

    # Parse HTML results (best-effort)
    soup = BeautifulSoup(resp.text, "html.parser")
    results = []

    # Try multiple selectors to be robust against layout changes
    candidate_selectors = [
        ".result",
        "div[data-test=search-result]",
        "div.result__body",
        "div.result__content",
        "li.result",
        "article",
    ]

    for sel in candidate_selectors:
        for item in soup.select(sel)[:size]:
            # Several possible title anchor selectors
            a = (
                item.select_one("a.result-title")
                or item.select_one("a.result__title")
                or item.select_one("h3 a")
                or item.select_one("a")
            )
            if not a:
                continue
            title = a.get_text(strip=True)
            url = a.get("href")

            # Try alternate attributes that some search UIs use to store real target
            if (not url or url in ("/", "/settings")):
                url = a.get('data-href') or a.get('data-url') or a.get('data-redirect') or url

            # If still not a valid http URL, attempt to parse onclick handlers
            if not url or not url.startswith('http'):
                onclick = a.get('onclick')
                if onclick:
                    import re

                    m = re.search(r"location(?:\.href)?\s*=\s*['\"]([^'\"]+)['\"]", onclick)
                    if m:
                        url = m.group(1)

            # Normalize relative URLs
            snippet_el = item.select_one("p.snippet") or item.select_one("div.result__snippet")
            snippet = snippet_el.get_text(strip=True) if snippet_el else ""

            # Resolve relative URLs against Brave search base
            if url and url.startswith("/"):
                url = urljoin(BRAVE_SEARCH_URL, url)

            # Log suspicious or internal-only hrefs for debugging
            if url in ("/", "/settings") or not url:
                logger.debug("Brave result had internal href or missing URL: title=%s href=%s html_snippet=%s", title, url, str(item)[:400])

            # Skip anchors that are not HTTP(S)
            if not url or not url.startswith("http"):
                logger.debug("Skipping non-http href: %s (title=%s)", url, title)
                continue

            results.append({"title": title, "url": url, "snippet": snippet})

        if results:
            break

    # Fallback: look for simple anchors (filtering non-http links)
    if not results:
        for a in soup.find_all("a", href=True)[:size * 3]:
            href = a.get('href')
            if not href:
                continue
            if href.startswith("/"):
                href = urljoin(BRAVE_SEARCH_URL, href)
            if not href.startswith("http"):
                continue
            title = a.get_text(strip=True) or href
            results.append({"title": title, "url": href, "snippet": ""})

    # If still no results, dump a short snippet of HTML into the logs to help debugging
    if not results:
        snippet = resp.text[:1000].replace("\n", " ")
        logger.debug("Brave search returned status %s but parsing found no results. HTML snippet: %s", resp.status_code, snippet)

    return results

    # Optional Playwright fallback: render the page with a headless browser and extract links
    use_playwright = os.getenv('BRAVE_USE_PLAYWRIGHT', '0') == '1'
    if not results and use_playwright:
        if not _PLAYWRIGHT_AVAILABLE:
            logger.warning('Playwright fallback requested (BRAVE_USE_PLAYWRIGHT=1) but Playwright is not installed.')
        else:
            logger.info('Attempting Playwright-rendered Brave search (BRAVE_USE_PLAYWRIGHT=1)')
            try:
                with sync_playwright() as pw:
                    browser = pw.chromium.launch(headless=True)
                    page = browser.new_page(user_agent=headers.get('User-Agent'))
                    # Build URL explicitly to avoid double-encoding
                    search_url = f"{BRAVE_SEARCH_URL}?q={query}&source=web&count={size}"
                    page.goto(search_url, timeout=20000)
                    # Wait for anchors to appear
                    page.wait_for_selector('a', timeout=8000)
                    anchors = page.query_selector_all('a')
                    for a in anchors:
                        try:
                            href = a.get_attribute('href')
                            text = a.inner_text().strip()
                            if href and href.startswith('/'):
                                href = urljoin(BRAVE_SEARCH_URL, href)
                            if href and href.startswith('http'):
                                results.append({'title': text or href, 'url': href, 'snippet': ''})
                                if len(results) >= size:
                                    break
                        except Exception:
                            continue
                    browser.close()
            except Exception as e:
                logger.warning('Playwright-based fetch failed: %s', e)

    return results


def fetch_page(url: str, timeout: int = 10) -> Dict[str, str]:
    """Fetch a URL and return a simple content dict {title, body, url}"""
    headers = {"User-Agent": "ar-tool/1.0"}
    try:
        resp = requests.get(url, headers=headers, timeout=timeout)
        if resp.status_code != 200:
            logger.warning("Fetching %s returned %s", url, resp.status_code)
            return {"title": "", "body": "", "url": url}

        soup = BeautifulSoup(resp.text, "html.parser")
        title = soup.title.string.strip() if soup.title and soup.title.string else ""
        # Extract main article/body heuristically
        article = soup.find("article")
        if article:
            body = article.get_text(separator=" \n ", strip=True)
        else:
            # fallback: gather paragraph text
            paragraphs = soup.find_all("p")
            body = "\n\n".join(p.get_text(strip=True) for p in paragraphs)

        return {"title": title, "body": body, "url": url}
    except Exception as e:
        logger.error("Error fetching page %s: %s", url, e)
        return {"title": "", "body": "", "url": url}
