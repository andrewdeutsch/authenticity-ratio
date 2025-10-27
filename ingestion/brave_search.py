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
from urllib.parse import urlparse
import urllib.robotparser as robotparser
import os
import json
import time
import threading
import re
from pathlib import Path

# Rate limiting: minimum interval (seconds) between outbound Brave requests
_BRAVE_REQUEST_INTERVAL = float(os.getenv('BRAVE_REQUEST_INTERVAL', '1.2'))
_LAST_BRAVE_REQUEST_TS = 0.0
_BRAVE_RATE_LOCK = threading.Lock()


def _wait_for_rate_limit():
    """Ensure at least _BRAVE_REQUEST_INTERVAL seconds between requests."""
    global _LAST_BRAVE_REQUEST_TS
    if _BRAVE_REQUEST_INTERVAL <= 0:
        return
    with _BRAVE_RATE_LOCK:
        now = time.monotonic()
        elapsed = now - _LAST_BRAVE_REQUEST_TS
        if elapsed < _BRAVE_REQUEST_INTERVAL:
            to_sleep = _BRAVE_REQUEST_INTERVAL - elapsed
            time.sleep(to_sleep)
        # Update the timestamp to now after sleeping
        _LAST_BRAVE_REQUEST_TS = time.monotonic()
    # end _wait_for_rate_limit


# Module-level robots.txt cache to share across functions
_ROBOTS_CACHE: Dict[str, robotparser.RobotFileParser] = {}


def _is_allowed_by_robots(url: str, user_agent: str | None = None) -> bool:
    """Check robots.txt for the given URL and user agent. Returns True if fetching is allowed.

    Uses a module-level cache to avoid repeated robots.txt fetches. If robots.txt cannot be
    fetched or parsed, defaults to permissive (True).
    """
    try:
        parsed = urlparse(url)
        netloc = parsed.netloc
        scheme = parsed.scheme or 'https'
        key = f"{scheme}://{netloc}"
        ua = user_agent or os.getenv('AR_USER_AGENT', 'Mozilla/5.0 (compatible; ar-bot/1.0)')
        if key in _ROBOTS_CACHE:
            rp = _ROBOTS_CACHE[key]
            try:
                return rp.can_fetch(ua, parsed.path or '/')
            except Exception:
                return True

        robots_url = f"{key}/robots.txt"
        rp = robotparser.RobotFileParser()
        try:
            _wait_for_rate_limit()
            r = requests.get(robots_url, headers={'User-Agent': ua}, timeout=5)
            if r.status_code == 200 and r.text:
                rp.parse(r.text.splitlines())
            else:
                rp.parse([])
        except Exception:
            try:
                rp.parse([])
            except Exception:
                pass
        _ROBOTS_CACHE[key] = rp
        try:
            return rp.can_fetch(ua, parsed.path or '/')
        except Exception:
            return True
    except Exception:
        return True

# Optional Playwright import (used only if the environment opts in)
try:
    from playwright.sync_api import sync_playwright
    _PLAYWRIGHT_AVAILABLE = True
except Exception:
    _PLAYWRIGHT_AVAILABLE = False

logger = logging.getLogger(__name__)

BRAVE_SEARCH_URL = "https://search.brave.com/search"


def _extract_footer_links(html: str, base_url: str) -> Dict[str, str]:
    """Parse HTML and attempt to find Terms and Privacy links.

    Returns a dict with keys 'terms' and 'privacy' whose values are absolute URLs or
    empty strings when not found.
    """
    terms_url = ""
    privacy_url = ""
    try:
        s = BeautifulSoup(html or "", "html.parser")
        footer = s.find('footer')
        anchors = footer.find_all('a', href=True) if footer else []
        # If footer anchors are not present, fall back to scanning all anchors
        if not anchors:
            anchors = s.find_all('a', href=True)

        for a in anchors:
            try:
                href = a.get('href', '').strip()
                if not href:
                    continue
                text = (a.get_text(" ", strip=True) or "").lower()
                href_l = href.lower()
                full = urljoin(base_url, href)

                # Common heuristics for privacy/terms links
                if ('privacy' in href_l) or ('privacy' in text) or ('cookie' in text):
                    if not privacy_url:
                        privacy_url = full
                if ('term' in href_l) or ('term' in text) or ('conditions' in text):
                    if not terms_url:
                        terms_url = full

                if terms_url and privacy_url:
                    break
            except Exception:
                continue
    except Exception:
        pass
    return {"terms": terms_url, "privacy": privacy_url}


def search_brave(query: str, size: int = 10) -> List[Dict[str, str]]:
    """Search Brave and return a list of result dicts {title, url, snippet}"""
    # If user has provided a Brave API key, prefer the API endpoint
    api_key = os.getenv('BRAVE_API_KEY')
    api_endpoint = os.getenv('BRAVE_API_ENDPOINT', 'https://api.search.brave.com/res/v1/web/search')
    headers = {
        "User-Agent": os.getenv('BRAVE_USER_AGENT', "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"),
        # Default Accept for the module is browser-like; this will be overridden to 'application/json'
        # when calling the Brave API endpoint (the API validates the Accept header strictly).
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }

    if api_key:
        # Use a single auth method to avoid multiple attempts per logical search.
        # Configure via BRAVE_API_AUTH: 'x-api-key' (default), 'bearer', 'both', 'query-param', or 'subscription-token'
        api_auth = os.getenv('BRAVE_API_AUTH', 'subscription-token')
        # Some Brave API plans limit the maximum 'count' per request. Allow an env override
        # but default to a conservative 10 results per API call to avoid 422 validation errors.
        try:
            max_api_count = int(os.getenv('BRAVE_API_MAX_COUNT', '10'))
        except Exception:
            max_api_count = 10
        params = {"q": query, "count": min(size, max_api_count)}
        # Prepare a results container so we can return it even if the API path fails
        results = []
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

            logger.info('Using Brave API endpoint for query=%s (api_auth=%s)', query, api_auth)
            # Prepare request (if query-param auth, append below)
            _wait_for_rate_limit()
            # Use helper-style retry for robustness
            if api_auth == 'query-param':
                params_with_key = params.copy()
                params_with_key['apikey'] = api_key
                # API expects JSON response; ensure Accept header is suitable for the API path
                hdrs['Accept'] = hdrs.get('Accept', '*/*') if hdrs.get('Accept') == '*/*' else 'application/json'
                resp = requests.get(api_endpoint, params=params_with_key, headers=hdrs, timeout=10)
            else:
                hdrs['Accept'] = hdrs.get('Accept', '*/*') if hdrs.get('Accept') == '*/*' else 'application/json'
                resp = requests.get(api_endpoint, params=params, headers=hdrs, timeout=10)

            if resp.status_code == 200:
                try:
                    body = resp.json()
                except Exception:
                    # resp.json() may raise AttributeError if the fake response doesn't implement it
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
        # If API key exists, do not fallback to HTML scraping unless explicitly enabled
        # This enforces an API-only flow when a subscription key is configured.
        allow_html = os.getenv('BRAVE_ALLOW_HTML_FALLBACK', '0') == '1'
        if not allow_html:
            # Return whatever results we have (possibly empty) and avoid HTML scraping
            return results

    logger.info('Falling back to Brave HTML scraping for query=%s', query)
    # Fallback to HTML scraping (only when API key is not present or fallback explicitly enabled)
    params = {"q": query, "source": "web", "count": size}
    _wait_for_rate_limit()
    # Use simple retries/backoff for the public HTML scrape path
    def _http_get_with_retries(url, params=None, headers=None, timeout=10, retries=3, backoff_factor=0.7):
        attempt = 0
        while attempt < retries:
            attempt += 1
            try:
                resp = requests.get(url, params=params, headers=headers, timeout=timeout)
                return resp
            except requests.RequestException as e:
                logger.debug('Brave HTML fetch attempt %s/%s failed: %s', attempt, retries, e)
                if attempt >= retries:
                    raise
                time.sleep(backoff_factor * (2 ** (attempt - 1)))

    try:
        resp = _http_get_with_retries(BRAVE_SEARCH_URL, params=params, headers=headers, timeout=10, retries=int(os.getenv('BRAVE_HTML_RETRIES','3')))
    except Exception as e:
        logger.error('Brave Search request failed after retries: %s', e)
        return []
    if resp.status_code != 200:
        logger.error("Brave Search request failed: %s %s", resp.status_code, getattr(resp, 'text', '')[:400])
        # Dump raw HTML for debugging
        try:
            dump_dir = Path(os.getenv('AR_FETCH_DEBUG_DIR', '/tmp/ar_fetch_debug'))
            dump_dir.mkdir(parents=True, exist_ok=True)
            safe = re.sub(r'[^a-zA-Z0-9_.-]', '_', query)[:80]
            (dump_dir / f'brave_search_{safe}.html').write_text(resp.text or '', encoding='utf-8')
            logger.debug('Wrote Brave search raw HTML to %s', dump_dir)
        except Exception:
            pass
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
    headers = {
        "User-Agent": os.getenv('AR_USER_AGENT', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }

    retries = int(os.getenv('AR_FETCH_RETRIES', '3'))
    backoff = float(os.getenv('AR_FETCH_BACKOFF', '0.6'))

    resp = None
    for attempt in range(1, retries + 1):
        try:
            _wait_for_rate_limit()
            resp = requests.get(url, headers=headers, timeout=timeout)
            break
        except Exception as e:
            # Handle both requests.RequestException and generic exceptions from monkeypatches
            logger.debug('Fetch attempt %s/%s for %s failed: %s', attempt, retries, url, e)
            if attempt == retries:
                logger.error('Error fetching page %s after %s attempts: %s', url, retries, e)
                # No resp to dump; just return empty
                return {"title": "", "body": "", "url": url}
            time.sleep(backoff * (2 ** (attempt - 1)))

    try:
        if resp is None:
            return {"title": "", "body": "", "url": url}

        if resp.status_code != 200:
            logger.warning("Fetching %s returned %s", url, resp.status_code)
            # If Playwright fallback is enabled and allowed by robots.txt, try rendering
            use_playwright = os.getenv('BRAVE_USE_PLAYWRIGHT', '0') == '1'
            try_playwright = use_playwright and _PLAYWRIGHT_AVAILABLE
            if try_playwright:
                try:
                    ua = os.getenv('AR_USER_AGENT', 'Mozilla/5.0 (compatible; ar-bot/1.0)')
                    # Respect robots.txt before attempting a headful fetch
                    try:
                        allowed = _is_allowed_by_robots(url, ua)
                    except Exception:
                        allowed = True
                    if allowed:
                        logger.info('Attempting Playwright-rendered fetch for %s (BRAVE_USE_PLAYWRIGHT=1)', url)
                        with sync_playwright() as pw:
                            browser = pw.chromium.launch(headless=True)
                            page = browser.new_page(user_agent=ua)
                            page.goto(url, timeout=20000)
                            # wait for body
                            try:
                                page.wait_for_selector('body', timeout=8000)
                            except Exception:
                                pass
                            page_content = page.content()
                            page_title = page.title() or ''
                            # Try to capture article or paragraphs
                            try:
                                article_handle = page.query_selector('article')
                                if article_handle:
                                    page_body = article_handle.inner_text()
                                else:
                                    paragraphs = page.query_selector_all('p')
                                    texts = [p.inner_text() for p in paragraphs if p]
                                    page_body = "\n\n".join(texts)
                            except Exception:
                                page_body = page_content
                            browser.close()
                            if page_body and len(page_body) >= 100:
                                links = _extract_footer_links(page_content, url)
                                return {"title": page_title.strip(), "body": page_body.strip(), "url": url, "terms": links.get("terms", ""), "privacy": links.get("privacy", "")}
                except Exception as e:
                    logger.warning('Playwright fallback failed for %s: %s', url, e)

            # Dump raw response for debugging
            try:
                dump_dir = Path(os.getenv('AR_FETCH_DEBUG_DIR', '/tmp/ar_fetch_debug'))
                dump_dir.mkdir(parents=True, exist_ok=True)
                safe = re.sub(r'[^a-zA-Z0-9_.-]', '_', url)[:120]
                (dump_dir / f'{safe}_status_{resp.status_code}.html').write_text(resp.text or '', encoding='utf-8')
                logger.debug('Wrote raw fetch output to %s', dump_dir)
            except Exception:
                pass
            try:
                links = _extract_footer_links(getattr(resp, 'text', '') or '', url)
            except Exception:
                links = {"terms": "", "privacy": ""}
            return {"title": "", "body": "", "url": url, "terms": links.get("terms", ""), "privacy": links.get("privacy", "")}

        soup = BeautifulSoup(resp.text, "html.parser")
        title = soup.title.string.strip() if soup.title and soup.title.string else ""

        # Try OpenGraph / Twitter meta fallbacks for title/description
        if not title:
            og_title = soup.select_one('meta[property="og:title"]') or soup.select_one('meta[name="twitter:title"]')
            if og_title and og_title.get('content'):
                title = og_title.get('content').strip()

        # Extract main article/body heuristically
        article = soup.find("article")
        if article:
            body = article.get_text(separator=" \n ", strip=True)
        else:
            # fallback: gather paragraph text
            paragraphs = soup.find_all("p")
            body = "\n\n".join(p.get_text(strip=True) for p in paragraphs)

        # If body or title are thin, try OG/Twitter description and dump for debugging
        if (not body or len(body) < 200) and soup.select_one('meta[property="og:description"]'):
            og_desc = soup.select_one('meta[property="og:description"]') or soup.select_one('meta[name="twitter:description"]')
            if og_desc and og_desc.get('content'):
                body = og_desc.get('content').strip()
        if (not title or not body or len(body) < 200):
            # Attempt Playwright fallback for thin content if enabled and allowed
            use_playwright = os.getenv('BRAVE_USE_PLAYWRIGHT', '0') == '1'
            try_playwright = use_playwright and _PLAYWRIGHT_AVAILABLE
            if try_playwright:
                try:
                    ua = os.getenv('AR_USER_AGENT', 'Mozilla/5.0 (compatible; ar-bot/1.0)')
                    allowed = True
                    try:
                        allowed = _is_allowed_by_robots(url, ua)
                    except Exception:
                        allowed = True
                    if allowed:
                        logger.info('Attempting Playwright-rendered fetch for thin content: %s', url)
                        with sync_playwright() as pw:
                            browser = pw.chromium.launch(headless=True)
                            page = browser.new_page(user_agent=ua)
                            page.goto(url, timeout=20000)
                            try:
                                page.wait_for_selector('body', timeout=8000)
                            except Exception:
                                pass
                            page_html = page.content()
                            page_title = page.title() or ''
                            try:
                                article_handle = page.query_selector('article')
                                if article_handle:
                                    page_body = article_handle.inner_text()
                                else:
                                    paragraphs = page.query_selector_all('p')
                                    texts = [p.inner_text() for p in paragraphs if p]
                                    page_body = "\n\n".join(texts)
                            except Exception:
                                # fallback to raw HTML if inner_text extraction fails
                                page_body = page_html
                            browser.close()
                            if page_body and len(page_body) >= 200:
                                try:
                                    links = _extract_footer_links(page_html, url)
                                except Exception:
                                    links = {"terms": "", "privacy": ""}
                                return {"title": page_title.strip(), "body": page_body.strip(), "url": url, "terms": links.get("terms", ""), "privacy": links.get("privacy", "")}
                except Exception as e:
                    logger.warning('Playwright fallback for thin content failed for %s: %s', url, e)

            try:
                dump_dir = Path(os.getenv('AR_FETCH_DEBUG_DIR', '/tmp/ar_fetch_debug'))
                dump_dir.mkdir(parents=True, exist_ok=True)
                safe = re.sub(r'[^a-zA-Z0-9_.-]', '_', url)[:120]
                (dump_dir / f'{safe}_thin.html').write_text(resp.text or '', encoding='utf-8')
                logger.debug('Wrote thin-content raw fetch output to %s', dump_dir)
            except Exception:
                pass

        try:
            links = _extract_footer_links(getattr(resp, 'text', '') or '', url)
        except Exception:
            links = {"terms": "", "privacy": ""}
        return {"title": title, "body": body, "url": url, "terms": links.get("terms", ""), "privacy": links.get("privacy", "")}
    except Exception as e:
        logger.error("Error fetching page %s: %s", url, e)
        # Attempt to dump whatever we have for debugging
        try:
            dump_dir = Path(os.getenv('AR_FETCH_DEBUG_DIR', '/tmp/ar_fetch_debug'))
            dump_dir.mkdir(parents=True, exist_ok=True)
            safe = re.sub(r'[^a-zA-Z0-9_.-]', '_', url)[:120]
            if resp is not None:
                (dump_dir / f'{safe}_exception.html').write_text(getattr(resp, 'text', '') or '', encoding='utf-8')
        except Exception:
            pass
        return {"title": "", "body": "", "url": url}


def collect_brave_pages(query: str, target_count: int = 10, pool_size: int | None = None, min_body_length: int = 200) -> List[Dict[str, str]]:
    """Collect up to `target_count` successfully fetched pages for a Brave search query.

    Behavior:
    - Request `pool_size` search results (defaults to max(30, target_count*3)).
    - Iterate results in order, skip URLs disallowed by robots.txt.
    - Attempt to fetch each allowed URL via `fetch_page` and only count pages whose
      `body` length >= `min_body_length` as successful.
    - Stop once `target_count` successful pages are collected or the pool is exhausted.

    This function honors robots.txt directives and will not fetch pages explicitly
    disallowed for the configured user-agent.
    """
    if pool_size is None:
        pool_size = max(30, target_count * 3)

    results = []
    try:
        search_results = search_brave(query, size=pool_size)
    except Exception as e:
        logger.warning('Brave search failed while collecting pages: %s', e)
        search_results = []

    if not search_results:
        return []

    # robots.txt cache per netloc
    robots_cache: Dict[str, robotparser.RobotFileParser] = {}
    ua = headers = {
        'User-Agent': os.getenv('AR_USER_AGENT', 'Mozilla/5.0 (compatible; ar-bot/1.0)')
    }

    def is_allowed_by_robots(url: str) -> bool:
        parsed = urlparse(url)
        netloc = parsed.netloc
        scheme = parsed.scheme or 'https'
        key = f"{scheme}://{netloc}"
        if key in robots_cache:
            rp = robots_cache[key]
            try:
                return rp.can_fetch(ua['User-Agent'], parsed.path or '/')
            except Exception:
                return True

        robots_url = f"{key}/robots.txt"
        rp = robotparser.RobotFileParser()
        try:
            # Fetch robots.txt using requests so we can set headers and timeouts
            _wait_for_rate_limit()
            r = requests.get(robots_url, headers=ua, timeout=5)
            if r.status_code == 200 and r.text:
                rp.parse(r.text.splitlines())
            else:
                # No robots.txt or non-200: treat as permissive
                rp.parse([])
        except Exception:
            # If robots fetch fails, prefer permissive to avoid blocking useful fetches
            try:
                rp.parse([])
            except Exception:
                pass
        robots_cache[key] = rp
        try:
            return rp.can_fetch(ua['User-Agent'], parsed.path or '/')
        except Exception:
            return True

    collected: List[Dict[str, str]] = []
    for item in search_results:
        if len(collected) >= target_count:
            break
        url = item.get('url')
        if not url:
            continue

        # Respect robots.txt
        try:
            allowed = is_allowed_by_robots(url)
        except Exception:
            allowed = True

        if not allowed:
            logger.info('Skipping %s due to robots.txt disallow', url)
            continue

        # Attempt to fetch and only count if body meets minimum length
        content = fetch_page(url)
        body = content.get('body') or ''
        if body and len(body) >= min_body_length:
            collected.append(content)
        else:
            logger.debug('Skipping %s because content is thin or empty (len=%s)', url, len(body))

    if collected:
        logger.info('Collected %s/%s successful pages for query=%s', len(collected), target_count, query)
    else:
        logger.info('No usable pages collected for query=%s', query)

    return collected
