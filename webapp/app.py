"""
Trust Stack Rating Web Application
A comprehensive interface for brand content Trust Stack Rating analysis
"""
from __future__ import annotations

import sys
import os

# Ensure project root is on PYTHONPATH
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import json
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
import glob as file_glob
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse

from config.settings import APIConfig, SETTINGS
from scoring.llm_client import ChatClient

# Configure logging for the webapp
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Helper Functions
def infer_brand_domains(brand_id: str) -> Dict[str, List[str]]:
    """
    Automatically infer likely brand domains from brand_id.

    Args:
        brand_id: Brand identifier (e.g., 'nike', 'coca-cola')

    Returns:
        Dict with 'domains', 'subdomains', and 'social_handles' keys
    """
    if not brand_id:
        return {'domains': [], 'subdomains': [], 'social_handles': []}

    brand_id_clean = brand_id.lower().strip()

    # Handle common brand name variations (for domains, never use spaces)
    brand_variations = []

    # If there are spaces, create hyphenated and combined versions
    if ' ' in brand_id_clean:
        brand_variations.append(brand_id_clean.replace(' ', '-'))  # red-bull
        brand_variations.append(brand_id_clean.replace(' ', ''))   # redbull
    elif '-' in brand_id_clean:
        # If there are hyphens, also try without
        brand_variations.append(brand_id_clean)                    # coca-cola
        brand_variations.append(brand_id_clean.replace('-', ''))   # cocacola
    else:
        # Simple brand name without spaces or hyphens
        brand_variations.append(brand_id_clean)                    # nike

    # Generate common domain patterns
    domains = []
    for variant in brand_variations:
        domains.extend([
            f"{variant}.com",
            f"www.{variant}.com",
        ])

    # Generate common subdomains
    subdomains = []
    for variant in brand_variations:
        subdomains.extend([
            f"blog.{variant}.com",
            f"www.{variant}.com",
            f"shop.{variant}.com",
            f"store.{variant}.com",
        ])

    # Generate social handle variations (include original for handles like "@red bull")
    social_handles = []
    # Add handles based on domain variants
    for variant in brand_variations:
        social_handles.extend([
            f"@{variant}",
            variant,
        ])
    # Also add original brand_id if different (for handles with spaces)
    if brand_id_clean not in brand_variations:
        social_handles.extend([
            f"@{brand_id_clean}",
            brand_id_clean,
        ])

    # Remove duplicates while preserving order
    domains = list(dict.fromkeys(domains))
    subdomains = list(dict.fromkeys(subdomains))
    social_handles = list(dict.fromkeys(social_handles))

    return {
        'domains': domains,
        'subdomains': subdomains,
        'social_handles': social_handles
    }


def extract_issues_from_items(items: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Extract specific issues from content items grouped by dimension.

    Args:
        items: List of analyzed content items with detected attributes

    Returns:
        Dictionary mapping dimension to list of specific issues found
    """
    dimension_issues = {
        'provenance': [],
        'verification': [],
        'transparency': [],
        'coherence': [],
        'resonance': []
    }

    for item in items:
        meta = item.get('meta', {})
        if isinstance(meta, str):
            try:
                meta = json.loads(meta)
            except:
                meta = {}
        elif meta is None:
            meta = {}

        # Extract detected attributes
        detected_attrs = meta.get('detected_attributes', [])
        title = meta.get('title', meta.get('name', 'Unknown content'))[:60]
        url = meta.get('source_url', meta.get('url', ''))

        for attr in detected_attrs:
            dimension = attr.get('dimension', 'unknown')
            value = attr.get('value', 5)
            evidence = attr.get('evidence', '')
            label = attr.get('label', '')

            # Only report low-scoring attributes (value <= 5 indicates problems)
            if dimension in dimension_issues and value <= 5:
                dimension_issues[dimension].append({
                    'title': title,
                    'url': url,
                    'issue': label,
                    'evidence': evidence,
                    'value': value
                })

    return dimension_issues


ENGLISH_DOMAIN_SUFFIXES = (
    '.com',
    '.us',
    '.ca',
    '.co.uk',
    '.com.au',
    '.ie',
    '.nz',
    '.sg',
    '.co.nz',
    '.com.sg',
    '.com.my',
    '.com.ph'
)

ENGLISH_COUNTRY_SUFFIXES = tuple(s for s in ENGLISH_DOMAIN_SUFFIXES if s != '.com')

# For this task the user requested USA-only sites
USA_DOMAIN_SUFFIXES = ('.com', '.us')

PROMOTIONAL_SUBPATHS = [
    '/about', '/about-us', '/press', '/press-room', '/newsroom', '/stories', '/careers',
    '/investor-relations', '/sustainability', '/insights', '/promotions', '/offers', '/events'
]


def normalize_brand_slug(brand_id: str) -> str:
    return re.sub(r'[^a-z0-9]', '', brand_id.lower())


def extract_hostname(url: str) -> str:
    return (urlparse(url).hostname or '').lower()


def is_english_host(url: str) -> bool:
    host = extract_hostname(url)
    return any(host.endswith(suffix) for suffix in ENGLISH_DOMAIN_SUFFIXES)


def is_usa_host(url: str) -> bool:
    host = extract_hostname(url)
    return any(host.endswith(suffix) for suffix in USA_DOMAIN_SUFFIXES)


def find_main_american_url(entries: List[Dict[str, Any]], brand_id: str) -> Optional[str]:
    slug = normalize_brand_slug(brand_id)
    for entry in entries:
        host = extract_hostname(entry['url'])
        if host.endswith('.com') and slug and slug in host:
            return entry['url']
        if host.endswith('.com') and host.startswith('www.'):
            return entry['url']
    return None


def has_country_variants(entries: List[Dict[str, Any]], main_url: str) -> bool:
    main_host = extract_hostname(main_url)
    for entry in entries:
        host = extract_hostname(entry['url'])
        if host != main_host and host.endswith(ENGLISH_COUNTRY_SUFFIXES):
            return True
    return False


def add_primary_subpages(entries: List[Dict[str, Any]], main_url: str) -> List[Dict[str, Any]]:
    parsed_main = urlparse(main_url)
    base = f"{parsed_main.scheme}://{parsed_main.netloc}"
    seen = {entry['url'] for entry in entries}
    for path in PROMOTIONAL_SUBPATHS:
        candidate = f"{base}{path}"
        if candidate not in seen:
            entries.append({'url': candidate, 'is_primary': True, 'synthesized': True})
            seen.add(candidate)
    return entries


def is_promotional_url(url: str) -> bool:
    parsed = urlparse(url)
    path = parsed.path.lower()
    if any(path.startswith(p) for p in PROMOTIONAL_SUBPATHS):
        return True
    # also accept query-based promo links or common promo words
    if any(k in path for k in ('promo', 'campaign', 'offer', 'deal', 'discount')):
        return True
    return False


def ensure_promotional_quota(entries: List[Dict[str, Any]], main_url: Optional[str], max_urls: int) -> List[Dict[str, Any]]:
    """Ensure at least 25% of the returned entries are promotional brand-owned pages.

    If not enough promotional URLs exist, generate subpage promotional URLs from the main_url
    (e.g., /promotions, /offers) until we hit the quota or reach max_urls.
    """
    if not entries:
        return entries

    target = max(1, int((0.25 * max_urls) + 0.999))  # ceil(25% of max_urls)
    promo_count = sum(1 for e in entries if is_promotional_url(e['url']))

    if promo_count >= target:
        return entries

    # Attempt to create promotional URLs from main_url
    if not main_url:
        return entries

    parsed_main = urlparse(main_url)
    base = f"{parsed_main.scheme}://{parsed_main.netloc}"
    seen = {e['url'] for e in entries}

    # We no longer synthesize promotional URLs. If the verified set does not
    # contain enough promotional pages, we return what we have and let the
    # caller decide whether to re-run the LLM with a targeted prompt.
    return entries


def get_brand_domains_from_llm(brand_id: str, model: str = 'gpt-4o-mini') -> List[str]:
    """
    Use LLM to discover all official domains owned by a brand.

    This is used to build site-restricted search queries for more efficient
    brand-controlled URL collection.

    Args:
        brand_id: Brand identifier (e.g., 'mastercard', 'nike')
        model: LLM model to use (default: gpt-4o-mini for cost efficiency)

    Returns:
        List of domains (e.g., ['mastercard.com', 'investor.mastercard.com'])
    """
    import openai
    import logging

    logger = logging.getLogger(__name__)

    prompt = f"""List all official domains and subdomains owned by {brand_id}.

Include:
- Main corporate website
- Investor relations sites
- Product/service sites
- Career/jobs sites
- Newsroom/press sites
- Developer/API sites
- International variants (e.g., .co.uk, .com.au)

Rules:
- One domain per line
- Domain only, no 'www.' prefix
- No URLs, just domains
- No explanations or numbering
- Maximum 15 domains

Example format:
mastercard.com
investor.mastercard.com
priceless.com
"""

    try:
        response = openai.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=500
        )

        text = response.choices[0].message.content.strip()
        logger.debug('LLM domain discovery response:\n%s', text)

        # Parse domains from response
        domains = []
        for line in text.split('\n'):
            line = line.strip()
            # Remove common prefixes/formatting
            line = line.replace('www.', '').replace('http://', '').replace('https://', '')
            line = line.split('/')[0]  # Remove any paths
            line = line.split()[0]  # Take first word if multiple

            # Validate: must contain a dot and look like a domain
            if '.' in line and len(line) > 3 and not line.startswith('#'):
                domains.append(line.lower())

        # Deduplicate and limit
        domains = list(dict.fromkeys(domains))[:15]
        logger.info(f'LLM discovered {len(domains)} domains for {brand_id}: {domains}')

        return domains

    except Exception as e:
        logger.warning(f'LLM domain discovery failed for {brand_id}: {e}')
        return []


def suggest_brand_urls_from_llm(brand_id: str, keywords: List[str], model: str = 'gpt-4o-mini', max_urls: int = 10,
                               brand_domains: List[str] = None) -> List[Dict[str, Any]]:
    """
    Ask an LLM to enumerate likely brand-owned URLs for the given brand.

    Args:
        brand_id: Brand identifier
        keywords: Search keywords to provide context
        model: LLM model to use
        max_urls: Maximum number of URLs to return

    Returns:
        Ordered list of dictionaries with keys `url` and `is_primary`, where primary entries come first
    """
    prompt = (
        f"Provide up to {max_urls} canonical brand-owned URLs for {brand_id}. "
    f"Include the most relevant primary domains first, followed by any supporting subdomains, english-speaking country variants, and promotional hubs that belong to {brand_id}. "
    "Highlight international domains (e.g., .com.au, .co.uk, .ca, .ie) and other brand-owned marketing sites. "
        "Return only the URLs (one per line), without numbering or explanations."
    )
    try:
        client = ChatClient(default_model=model)
        messages = [
            {'role': 'system', 'content': 'You are a helpful research assistant.'},
            {'role': 'user', 'content': prompt}
        ]
        # Respect config: do not perform LLM/verification for explicitly excluded brands
        excluded = SETTINGS.get('excluded_brands', []) or []
        if brand_id and brand_id.lower() in excluded:
            logger.info('Brand %s is in excluded_brands; skipping LLM enumeration', brand_id)
            return []

        # Ask the model for structured JSON-per-line output: url, evidence, confidence
        # Temporarily enable debug logging for this call so we can capture raw model output
        prev_level = logger.level
        try:
            logger.setLevel(logging.DEBUG)
            response = client.chat(messages=messages, max_tokens=1024)
            text = response.get('content') or response.get('text') or ''
            logger.debug('LLM raw response:\n%s', text)
        finally:
            logger.setLevel(prev_level)

        # Parse JSON lines if available (model should return one JSON object per line)
        candidates: List[Dict[str, Any]] = []
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                url = obj.get('url')
                evidence = obj.get('evidence')
                confidence = int(obj.get('confidence') or 0)
                if url:
                    candidates.append({'url': url.strip(), 'evidence': evidence, 'confidence': confidence})
            except Exception:
                # Fall back to regex extraction per-line if JSON parse fails
                m = re.search(r'(https?://[\w\-\.\/\%\?&=#:]+)', line)
                if m:
                    candidates.append({'url': m.group(1).strip(), 'evidence': None, 'confidence': 0})
        # Build a deduped candidate list, respecting the order and any model confidence
        seen_urls = set()
        deduped_candidates: List[Dict[str, Any]] = []
        for c in candidates:
            url = c['url'].rstrip('.,;')
            if url in seen_urls:
                continue
            seen_urls.add(url)
            # prefer US/.com hosts only
            if not is_usa_host(url):
                continue
            is_primary = classify_brand_url(url, brand_id, brand_domains) == 'primary'
            deduped_candidates.append({
                'url': url,
                'evidence': c.get('evidence'),
                'confidence': c.get('confidence', 0),
                'is_primary': is_primary
            })
        # Log parsed candidates for debugging (INFO so it appears in typical logs)
        try:
            logger.info('Parsed LLM candidates (deduped, US-only): %s', json.dumps(deduped_candidates, indent=2))
        except Exception:
            logger.info('Parsed LLM candidates (deduped, US-only): %s', str(deduped_candidates))

        # Verify candidates in parallel, prioritizing primaries
        ordered = sorted(deduped_candidates, key=lambda x: (0 if x['is_primary'] else 1, -int(x.get('confidence', 0))))

        verified_entries: List[Dict[str, Any]] = []
        from concurrent.futures import ThreadPoolExecutor, as_completed

        max_workers = min(20, max(4, len(ordered)))
        with ThreadPoolExecutor(max_workers=max_workers) as exe:
            future_to_entry = {exe.submit(verify_url, e['url'], brand_id): e for e in ordered}
            for fut in as_completed(future_to_entry):
                entry = future_to_entry[fut]
                try:
                    result = fut.result()
                except Exception as exc:
                    logger.debug('Verification raised for %s: %s', entry['url'], exc)
                    continue
                if result and result.get('ok'):
                    # fetch title for display
                    title = fetch_page_title(result.get('final_url') or entry['url'], brand_id)
                    verified_entries.append({
                        'url': result.get('final_url') or entry['url'],
                        'is_primary': entry['is_primary'],
                        'verified': True,
                        'status': result.get('status'),
                        'soft_verified': result.get('soft_verified', False),
                        'verification_method': result.get('method'),
                        'title': title,
                        'evidence': entry.get('evidence'),
                        'confidence': entry.get('confidence', 0),
                        'is_promotional': is_promotional_url(entry['url'])
                    })
                else:
                    logger.debug('Unverified candidate: %s (status=%s)', entry['url'], result.get('status') if isinstance(result, dict) else None)
                if len(verified_entries) >= max_urls:
                    break

        if verified_entries:
            # Clear any previous fallback indicator
            try:
                if 'llm_search_fallback' in st.session_state:
                    del st.session_state['llm_search_fallback']
                if 'llm_search_fallback_count' in st.session_state:
                    del st.session_state['llm_search_fallback_count']
            except Exception:
                pass

        if not verified_entries:
            logger.info('No verified URLs found after LLM verification for brand: %s. Attempting web-search fallback...', brand_id)
            try:
                fallback = search_urls_fallback(brand_id, keywords, target_count=max_urls)
                if fallback:
                    logger.info('Search fallback returned %d verified URLs for %s', len(fallback), brand_id)
                    verified_entries = fallback[:max_urls]
                    # Mark that fallback was used so UI can show a banner
                    try:
                        st.session_state['llm_search_fallback'] = True
                        st.session_state['llm_search_fallback_count'] = len(verified_entries)
                    except Exception:
                        pass
                else:
                    logger.warning('Search fallback did not return any verified URLs for brand: %s', brand_id)
            except Exception as e:
                logger.warning('Search fallback failed for %s: %s', brand_id, e)

        return verified_entries[:max_urls]
    except Exception as exc:
        logger.warning('LLM brand URL suggestion failed: %s', exc)
        return []


def enumerate_brand_urls_from_llm_raw(brand_id: str, keywords: List[str], model: str = 'gpt-4o-mini', candidate_limit: int = 100) -> List[str]:
    """Return raw LLM candidates (unverified) so the UI can show them for debugging/verification."""
    # Respect excluded brands config
    excluded = SETTINGS.get('excluded_brands', []) or []
    if brand_id and brand_id.lower() in excluded:
        logger.info('Brand %s is in excluded_brands; skipping raw LLM enumeration', brand_id)
        return []
    prompt = (
        f"Provide up to {candidate_limit} canonical brand-owned URLs for {brand_id}. "
        f"Include primary domains, localized variants, investor/careers pages and promotional hubs. "
        "Return only the URLs (one per line), without numbering or explanations."
    )
    try:
        client = ChatClient(default_model=model)
        messages = [
            {'role': 'system', 'content': 'You are a helpful research assistant.'},
            {'role': 'user', 'content': prompt}
        ]
        # Turn on debug briefly and log the raw response
        prev_level = logger.level
        try:
            logger.setLevel(logging.DEBUG)
            response = client.chat(messages=messages, max_tokens=512)
            text = response.get('content') or response.get('text') or ''
            logger.debug('LLM raw (raw enumerator) response:\n%s', text)
        finally:
            logger.setLevel(prev_level)
        url_candidates = re.findall(r'https?://[\w\-\.\/\%\?&=#:]+', text)
        unique_urls = []
        for url in url_candidates:
            clean_url = url.strip().rstrip('.,;')
            if clean_url not in unique_urls:
                unique_urls.append(clean_url)
            if len(unique_urls) >= candidate_limit:
                break
        return unique_urls
    except Exception:
        return []


def classify_brand_url(url: str, brand_id: str, brand_domains: List[str] = None) -> str:
    """Label a brand URL as primary or a supporting subdomain."""

    parsed = urlparse(url)
    host = (parsed.hostname or '').lower()
    if not host:
        return 'subdomain'

    stripped_host = host[4:] if host.startswith('www.') else host
    normalized_domains = {d.lower().lstrip('www.') for d in (brand_domains or []) if d}
    brand_slug = re.sub(r'[^a-z0-9]', '', brand_id.lower())

    if stripped_host in normalized_domains:
        return 'primary'
    if brand_slug:
        if stripped_host == brand_slug or stripped_host.startswith(f"{brand_slug}."):
            return 'primary'

    return 'subdomain'


def normalize_international_url(url: str, brand_id: str) -> Optional[str]:
    """Rewrite invalid brand hosts like `brand.com.xx` to `brand.xx` if sensible."""

    parsed = urlparse(url)
    host = (parsed.hostname or '').lower()
    if not host:
        return None

    brand_slug = re.sub(r'[^a-z0-9]', '', brand_id.lower())
    if not brand_slug:
        return None

    if host.startswith('www.'):
        prefix = 'www.'
        stripped = host[4:]
    else:
        prefix = ''
        stripped = host

    if stripped.startswith(f"{brand_slug}.com.") and stripped.count('.') >= 2:
        parts = stripped.split('.')
        normalized = '.'.join([parts[0]] + parts[2:])
        new_host = f"{prefix}{normalized}"
        parsed = parsed._replace(netloc=new_host)
        return parsed.geturl()

    return None


def fetch_page_title(url: str, brand_id: str = '', timeout: float = 5.0) -> str:
    """Retrieve a human-readable title for a given URL, fallback to hostname, and handle hostname mismatches."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (compatible; TrustStackBot/1.0; +https://example.com/bot)'
    }
    browser_headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    try:
        # Try with a polite bot UA first
        response = requests.get(url, timeout=timeout, headers=headers)
        status = getattr(response, 'status_code', None)
        if status and 200 <= status < 400:
            soup = BeautifulSoup(response.text, 'html.parser')
            title_tag = soup.title
            if title_tag and title_tag.string:
                title = title_tag.string.strip()
                if title:
                    return title
        # If we get a 403, retry with a browser UA which some sites accept
        if status == 403:
            logger.debug('Received 403 fetching title for %s; retrying with browser UA', url)
            try:
                resp2 = requests.get(url, timeout=max(timeout, 6.0), headers=browser_headers)
                if getattr(resp2, 'status_code', None) and 200 <= resp2.status_code < 400:
                    soup = BeautifulSoup(resp2.text, 'html.parser')
                    title_tag = soup.title
                    if title_tag and title_tag.string:
                        return title_tag.string.strip()
            except Exception as e:
                logger.debug('Browser-UA retry failed for %s: %s', url, e)
    except requests.exceptions.SSLError as exc:
        logger.debug('SSL error fetching %s: %s', url, exc)
        normalized_url = normalize_international_url(url, brand_id)
        if normalized_url and normalized_url != url:
            logger.info('Retrying with normalized host: %s', normalized_url)
            return fetch_page_title(normalized_url, brand_id, timeout)
        return _fallback_title(url)
    except Exception as exc:
        logger.debug('Unable to fetch title for %s: %s', url, exc)
        return _fallback_title(url)

    parsed = urlparse(url)
    hostname = parsed.hostname or url
    return hostname


def verify_url(url: str, brand_id: str = '', timeout: float = 5.0) -> bool:
    """Verify that a URL is reachable (2xx or 3xx).

    Returns a dict: {'ok': bool, 'status': int|None, 'final_url': str|None}

    Retries with normalized host on SSL errors.
    """
    headers = {'User-Agent': 'Mozilla/5.0 (compatible; TrustStackBot/1.0; +https://example.com/bot)'}
    try:
        # Prefer HEAD for lightweight check
        resp = requests.head(url, timeout=timeout, headers=headers, allow_redirects=True)
        status = getattr(resp, 'status_code', None)
        final = getattr(resp, 'url', url)
        if status and 200 <= status < 400:
            return {'ok': True, 'status': status, 'final_url': final}
        # If forbidden (403), try again with a browser UA via GET
        if status == 403:
            logger.debug('HEAD returned 403 for %s; retrying GET with browser UA', url)
            try:
                browser_headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
                resp2 = requests.get(url, timeout=max(timeout, 6.0), headers=browser_headers, allow_redirects=True)
                status2 = getattr(resp2, 'status_code', None)
                final2 = getattr(resp2, 'url', url)
                if status2 and 200 <= status2 < 400:
                    return {'ok': True, 'status': status2, 'final_url': final2}
                # If still forbidden, attempt DNS resolution as a soft-verification
                try:
                    from socket import getaddrinfo
                    host = extract_hostname(url)
                    if host:
                        addrs = getaddrinfo(host, None)
                        if addrs:
                            logger.info('Host %s resolves via DNS; marking soft-verified', host)
                            return {'ok': True, 'status': status2, 'final_url': final2, 'soft_verified': True, 'method': 'dns_resolution'}
                except Exception as _:
                    pass
                return {'ok': False, 'status': status2, 'final_url': final2}
            except Exception as e:
                logger.debug('Browser-UA GET retry failed for %s: %s', url, e)
                return {'ok': False, 'status': status, 'final_url': final}
        # Some servers don't like HEAD; fall back to GET for verification
        if status in (405, 501) or status is None:
            try:
                resp = requests.get(url, timeout=max(timeout, 6.0), headers=headers, allow_redirects=True)
                status = getattr(resp, 'status_code', None)
                final = getattr(resp, 'url', url)
                return {'ok': bool(status and 200 <= status < 400), 'status': status, 'final_url': final}
            except Exception as e:
                logger.debug('GET fallback failed for %s after HEAD status=%s: %s', url, status, e)
                return {'ok': False, 'status': status, 'final_url': final}
        return {'ok': False, 'status': status, 'final_url': final}
    except requests.exceptions.SSLError as exc:
        logger.debug('SSL error verifying %s: %s', url, exc)
        normalized = normalize_international_url(url, brand_id)
        if normalized and normalized != url:
            logger.info('Retrying verification with normalized host: %s', normalized)
            return verify_url(normalized, brand_id, timeout)
        return {'ok': False, 'status': None, 'final_url': None}
    except Exception as exc:
        # Some network/HEAD-specific errors can be resolved by trying GET once
        logger.debug('HEAD request failed for %s: %s -- attempting GET fallback', url, exc)
        try:
            resp = requests.get(url, timeout=max(timeout, 6.0), headers=headers, allow_redirects=True)
            status = getattr(resp, 'status_code', None)
            final = getattr(resp, 'url', url)
            return {'ok': bool(status and 200 <= status < 400), 'status': status, 'final_url': final}
        except requests.exceptions.SSLError as exc2:
            logger.debug('SSL error on GET fallback for %s: %s', url, exc2)
            normalized = normalize_international_url(url, brand_id)
            if normalized and normalized != url:
                logger.info('Retrying verification with normalized host (GET fallback): %s', normalized)
                return verify_url(normalized, brand_id, timeout)
            return {'ok': False, 'status': None, 'final_url': None}
        except Exception as exc2:
            logger.debug('GET fallback also failed for %s: %s', url, exc2)
            return {'ok': False, 'status': None, 'final_url': None}


def search_urls_fallback(brand_id: str, keywords: List[str], target_count: int = 20) -> List[Dict[str, Any]]:
    """Run a quick web search fallback to collect candidate URLs, classify and verify them.

    This uses the unified search interface (ingestion.search_unified.search) and returns
    entries in the same shape as suggest_brand_urls_from_llm produces so the UI can consume them.
    """
    try:
        from ingestion.search_unified import search, validate_provider_config
    except Exception as e:
        logger.info('Search fallback not available: %s', e)
        return []

    # Validate provider readiness
    cfg = validate_provider_config()
    if not cfg.get('ready'):
        logger.info('Search provider not configured or available for fallback: %s', cfg.get('message'))
        return []

    query = ' '.join(keywords) if keywords else brand_id
    try:
        results = search(query, size=target_count)
    except Exception as e:
        logger.warning('Search fallback failed: %s', e)
        return []

    # Collect candidate URLs and classify
    candidates = []
    for r in results:
        url = r.get('url')
        if not url:
            continue
        is_primary = classify_brand_url(url, brand_id, None) == 'primary'
        candidates.append({'url': url, 'is_primary': is_primary, 'title': r.get('title', ''), 'snippet': r.get('snippet', '')})

    # Verify candidates in parallel
    verified: List[Dict[str, Any]] = []
    from concurrent.futures import ThreadPoolExecutor, as_completed
    max_workers = min(20, max(4, len(candidates)))
    with ThreadPoolExecutor(max_workers=max_workers) as exe:
        future_to_c = {exe.submit(verify_url, c['url'], brand_id): c for c in candidates}
        for fut in as_completed(future_to_c):
            c = future_to_c[fut]
            try:
                res = fut.result()
            except Exception as e:
                logger.debug('Search fallback verification raised for %s: %s', c['url'], e)
                continue
            if res and res.get('ok'):
                title = fetch_page_title(res.get('final_url') or c['url'], brand_id)
                verified.append({
                    'url': res.get('final_url') or c['url'],
                    'is_primary': c.get('is_primary', False),
                    'verified': True,
                    'status': res.get('status'),
                    'soft_verified': res.get('soft_verified', False),
                    'verification_method': res.get('method'),
                    'title': title,
                    'evidence': None,
                    'confidence': 0,
                    'is_promotional': is_promotional_url(c['url'])
                })
            if len(verified) >= target_count:
                break

    return verified


def _fallback_title(url: str) -> str:
    parsed = urlparse(url)
    hostname = parsed.hostname or url
    return hostname


def get_remedy_for_issue(issue_type: str, dimension: str) -> str:
    """
    Get specific remedy recommendation for a detected issue type.

    Args:
        issue_type: Type of issue detected (e.g., "Privacy Policy Link Availability Clarity")
        dimension: Dimension the issue belongs to

    Returns:
        Specific actionable remedy recommendation
    """
    # Map specific issues to remedies
    remedies = {
        # Provenance
        'AI vs Human Labeling Clarity': 'Add clear labels indicating whether content is AI-generated or human-created. Use schema.org markup to embed this metadata.',
        'Author Brand Identity Verified': '''Implement appropriate author attribution based on content type:

**For Blog Posts & Articles:** Add visible bylines with author names and optional author bio pages.

**For Corporate Landing Pages:** Consider these options:
• **Structured Data (Recommended):** Add schema.org markup with author/publisher info using JSON-LD format (invisible to users, visible to search engines)
• **Meta Tags:** Add <meta name="author" content="Team/Organization"> tags
• **Subtle Footer Attribution:** Include "Content by [Team]" or "Maintained by [Name/Team]" in page footer
• **About/Credits Pages:** Create dedicated /about or /team page and link discretely from main pages
• **Expandable Page Info:** Add a small "ⓘ" icon or "About this page" link showing contributors

Example Schema.org markup for landing pages:
```html
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "WebPage",
  "author": {
    "@type": "Organization",
    "name": "Acme Corp Marketing Team"
  },
  "publisher": {
    "@type": "Organization",
    "name": "Acme Corporation"
  }
}
</script>
```''',
        'C2PA CAI Manifest Present': 'Implement Content Authenticity Initiative (C2PA) manifests for media files to provide cryptographic provenance.',
        'Canonical URL Matches Declared Source': 'Ensure canonical URLs match the declared source. Add proper <link rel="canonical"> tags to all pages.',
        'Digital Watermark Fingerprint Detected': 'Add digital watermarks or fingerprints to images and videos for traceability.',
        'EXIF Metadata Integrity': 'Preserve EXIF metadata in images. Ensure metadata includes creator, date, and copyright information.',
        'Source Domain Trust Baseline': 'Improve domain reputation by adding SSL certificates, privacy policies, and contact information.',
        'Schema Compliance': 'Implement schema.org structured data markup (JSON-LD) for all content types.',
        'Metadata Completeness': 'Add complete metadata including title, description, author, date, and Open Graph/Twitter Card tags.',

        # Verification
        'Ad Sponsored Label Consistency': 'Clearly label all sponsored content and advertisements with "Sponsored" or "Ad" labels.',
        'Agent Safety Guardrail Presence': 'Implement content safety guardrails and moderation policies. Document them publicly.',
        'Claim to Source Traceability': 'Add citations and references for all claims. Link to authoritative sources.',
        'Engagement Authenticity Ratio': 'Monitor and remove fake engagement (bots, fake reviews). Encourage authentic user interactions.',
        'Influencer Partner Identity Verified': 'Verify influencer and partner identities. Display verification badges or certificates.',
        'Review Authenticity Confidence': 'Implement verified review systems. Flag or remove suspicious reviews.',
        'Seller Product Verification Rate': 'Verify seller identities and product authenticity. Display verification status prominently.',
        'Verified Purchaser Review Rate': 'Mark reviews from verified purchasers. Implement purchase verification in your review system.',

        # Transparency
        'AI Explainability Disclosure': 'When using AI, explain how it works and what data it uses. Add an AI transparency page.',
        'AI Generated Assisted Disclosure Present': 'Clearly disclose when content is AI-generated or AI-assisted. Add disclosure statements to all AI content.',
        'Bot Disclosure Response Audit': 'Clearly identify bot-generated responses. Add "This is an automated response" disclaimers.',
        'Caption Subtitle Availability Accuracy': 'Add accurate captions and subtitles to all video content. Use human review for accuracy.',
        'Data Source Citations for Claims': 'Add inline citations for all data-driven claims. Link to primary sources and datasets.',
        'Privacy Policy Link Availability Clarity': 'Add a clear Privacy Policy link to your footer and make it easily accessible. Ensure the policy is clear and up-to-date.',

        # Coherence
        'Brand Voice Consistency Score': 'Audit content for consistent brand voice. Create and enforce brand voice guidelines.',
        'Broken Link Rate': 'Regularly audit and fix broken links. Use automated link checkers weekly.',
        'Claim Consistency Across Pages': 'Ensure claims are consistent across all content. Create a single source of truth for key claims.',
        'Email Asset Consistency Check': 'Standardize email templates and branding. Ensure consistency with website branding.',
        'Engagement to Trust Correlation': 'Monitor how engagement patterns correlate with trust metrics. Address suspicious patterns.',
        'Multimodal Consistency Score': 'Ensure text, images, and videos tell a consistent story. Audit multimedia content for alignment.',
        'Temporal Continuity Versions': 'Maintain version history for content updates. Show update dates and change logs.',
        'Trust Fluctuation Index': 'Monitor trust score changes over time. Investigate and address sudden drops.',

        # Resonance
        'Community Alignment Index': 'Engage with your community authentically. Monitor sentiment and adjust messaging to align with community values.',
        'Creative Recency vs Trend': 'Stay current with trends while maintaining brand authenticity. Update content regularly.',
        'Cultural Context Alignment': 'Ensure content is culturally appropriate and relevant. Work with cultural consultants for diverse markets.',
        'Language Locale Match': 'Provide content in appropriate languages for your target markets. Use professional translation services.',
        'Personalization Relevance Embedding Similarity': 'Improve personalization algorithms to better match user interests while respecting privacy.',
        'Readability Grade Level Fit': 'Adjust content readability to match your target audience. Use readability tools to test and optimize.',
        'Tone Sentiment Appropriateness': 'Ensure content tone matches the context and audience expectations. Avoid overly promotional language.'
    }

    return remedies.get(issue_type, f'Address this {dimension} issue by improving content quality and adding relevant metadata.')


def generate_rating_recommendation(avg_rating: float, dimension_breakdown: Dict[str, Any], items: List[Dict[str, Any]]) -> str:
    """
    Generate data-driven recommendation based on dimension analysis with specific examples.

    Args:
        avg_rating: Average rating score (0-100)
        dimension_breakdown: Dictionary with dimension averages
        items: List of analyzed content items

    Returns:
        Comprehensive recommendation string with concrete examples
    """
    # Define dimension details
    dimension_info = {
        'provenance': {
            'name': 'Provenance',
            'recommendation': 'implement structured metadata (schema.org markup), add clear author attribution, and include publication timestamps on all content',
            'description': 'origin tracking and metadata'
        },
        'verification': {
            'name': 'Verification',
            'recommendation': 'fact-check claims against authoritative sources, add citations and references, and link to verifiable external data',
            'description': 'factual accuracy'
        },
        'transparency': {
            'name': 'Transparency',
            'recommendation': 'add disclosure statements, clearly identify sponsored content, and provide detailed attribution for all sources',
            'description': 'disclosure and clarity'
        },
        'coherence': {
            'name': 'Coherence',
            'recommendation': 'audit messaging consistency across all channels, align visual branding, and ensure unified voice in customer communications',
            'description': 'cross-channel consistency'
        },
        'resonance': {
            'name': 'Resonance',
            'recommendation': 'increase authentic engagement with your audience, reduce promotional language, and ensure cultural relevance in messaging',
            'description': 'audience engagement'
        }
    }

    # Find lowest-performing dimension
    dimension_keys = ['provenance', 'verification', 'transparency', 'coherence', 'resonance']
    dimension_scores = {
        key: dimension_breakdown.get(key, {}).get('average', 0.5) * 100  # Convert to 0-100 scale
        for key in dimension_keys
    }

    # Extract specific issues from items
    dimension_issues = extract_issues_from_items(items)

    # Find the dimension with the lowest score
    if dimension_scores:
        lowest_dim_key = min(dimension_scores, key=dimension_scores.get)
        lowest_dim_score = dimension_scores[lowest_dim_key]
        lowest_dim_info = dimension_info[lowest_dim_key]

        # Get example issues for the lowest dimension
        issues_for_dim = dimension_issues.get(lowest_dim_key, [])
        example_text = ""
        if issues_for_dim:
            # Get first unique issue as example
            example = issues_for_dim[0]
            example_text = f" For example, on \"{example['title']}\", there was an issue with {example['issue'].lower()}: {example['evidence']}."

        # Generate comprehensive summary based on rating band
        if avg_rating >= 80:
            # Excellent - maintain standards with minor optimization
            return f"Your brand content demonstrates high quality with an average rating of {avg_rating:.1f}/100. To reach even greater heights, consider optimizing {lowest_dim_info['name']} (currently at {lowest_dim_score:.1f}/100) by continuing to {lowest_dim_info['recommendation']}.{example_text}"

        elif avg_rating >= 60:
            # Good - focus on improvement area
            return f"Your content shows solid quality with an average rating of {avg_rating:.1f}/100. To improve from Good to Excellent, focus on enhancing {lowest_dim_info['name']} (currently at {lowest_dim_score:.1f}/100) by taking action to {lowest_dim_info['recommendation']}.{example_text}"

        elif avg_rating >= 40:
            # Fair - requires focused attention
            return f"Your content quality is moderate with an average rating of {avg_rating:.1f}/100, requiring attention. To mitigate weak {lowest_dim_info['description']}, you should {lowest_dim_info['recommendation']}.{example_text} This will help move your rating from Fair to Good or Excellent."

        else:
            # Poor - immediate action needed
            return f"Your content quality is low with an average rating of {avg_rating:.1f}/100, requiring immediate action. Critical issue detected in {lowest_dim_info['name']} (scoring only {lowest_dim_score:.1f}/100). You must {lowest_dim_info['recommendation']}.{example_text}"

    else:
        # Fallback if no dimension data available
        return f"Your content has an average rating of {avg_rating:.1f}/100. Comprehensive dimension analysis is needed to provide specific recommendations."

# Page configuration
st.set_page_config(
    page_title="Trust Stack Rating Tool",
    page_icon="⭐",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        color: #1f77b4;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: #f0f2f6;
        padding: 1.5rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
    }
    .info-box {
        background: #e7f3ff;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #2196F3;
        margin: 1rem 0;
        color: #1565c0;
    }
    .success-box {
        background: #e8f5e9;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #4caf50;
        margin: 1rem 0;
        color: #2e7d32;
    }
    .warning-box {
        background: #fff3e0;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #ff9800;
        margin: 1rem 0;
        color: #e65100;
    }

    /* Animated progress indicator styles */
    .progress-container {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 0.75rem;
        margin: 1rem 0;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        min-height: 80px;
        display: flex;
        align-items: center;
        justify-content: center;
    }

    .progress-item {
        color: white;
        font-size: 1.1rem;
        font-weight: 500;
        text-align: center;
        line-height: 1.5;
        animation: fadeInOut 1.25s ease-in-out;
    }

    .progress-item-fadeout {
        animation: fadeOut 0.25s ease-out forwards;
    }

    @keyframes fadeInOut {
        0% {
            opacity: 0;
            transform: translateY(10px);
        }
        8% {
            opacity: 1;
            transform: translateY(0);
        }
        100% {
            opacity: 1;
            transform: translateY(0);
        }
    }

    @keyframes fadeOut {
        0% {
            opacity: 1;
            transform: translateY(0);
        }
        100% {
            opacity: 0;
            transform: translateY(-10px);
        }
    }

    .progress-emoji {
        font-size: 1.5rem;
        margin-right: 0.5rem;
        display: inline-block;
        animation: pulse 2s ease-in-out infinite;
    }

    @keyframes pulse {
        0%, 100% {
            transform: scale(1);
        }
        50% {
            transform: scale(1.1);
        }
    }
</style>
""", unsafe_allow_html=True)


class ProgressAnimator:
    """
    Animated progress indicator that displays messages with fade-in/fade-out effects.
    Each message appears at 100% visibility, remains for 1 second, then fades out over 0.25s.
    """

    def __init__(self, container=None):
        """
        Initialize the progress animator.

        Args:
            container: Streamlit container to use. If None, creates a new empty container.
        """
        self.container = container if container is not None else st.empty()
        self.current_message = None

    def show(self, message: str, emoji: str = "🔍"):
        """
        Display an animated progress message.

        Args:
            message: The progress message to display (will be truncated if too long)
            emoji: Emoji to show with the message
        """
        # Truncate message if too long (keep it concise for animation effect)
        max_length = 120
        if len(message) > max_length:
            message = message[:max_length-3] + "..."

        self.current_message = message

        # Display with animation
        html = f"""
        <div class="progress-container">
            <div class="progress-item">
                <span class="progress-emoji">{emoji}</span>
                <span>{message}</span>
            </div>
        </div>
        """

        self.container.markdown(html, unsafe_allow_html=True)

        # Stay visible for 1 second
        time.sleep(1.0)

        # Fade out over 0.25 seconds
        html_fadeout = f"""
        <div class="progress-container">
            <div class="progress-item progress-item-fadeout">
                <span class="progress-emoji">{emoji}</span>
                <span>{message}</span>
            </div>
        </div>
        """

        self.container.markdown(html_fadeout, unsafe_allow_html=True)
        time.sleep(0.25)

    def clear(self):
        """Clear the progress display."""
        self.container.empty()
        self.current_message = None


def show_home_page():
    """Display the home/overview page"""
    st.markdown('<div class="main-header">⭐ Trust Stack Rating</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Measure and monitor brand content quality across digital channels</div>', unsafe_allow_html=True)

    st.divider()

    # What is Trust Stack Rating section
    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown("### 📊 What is the Trust Stack Rating?")
        st.markdown("""
        The **Trust Stack Rating** is a comprehensive scoring system that evaluates brand-linked content
        across six trust dimensions. Each piece of content receives a **0-100 rating** based on
        signals detected in metadata, structure, and provenance.

        #### Rating Scale (0-100)
        - **80-100** (🟢 Excellent): High-quality, verified content
        - **60-79** (🟡 Good): Solid content with minor improvements needed
        - **40-59** (🟠 Fair): Moderate quality requiring attention
        - **0-39** (🔴 Poor): Low-quality content needing immediate review

        #### Comprehensive Rating
        ```
        Rating = Weighted average across 6 dimensions
        ```
        Each dimension contributes based on configurable weights, with detected attributes
        providing bonuses or penalties.
        """)

    with col2:
        st.markdown("### 🎯 Quick Start")
        st.markdown("""
        1. **Configure** your brand and sources
        2. **Run** the analysis pipeline
        3. **Review** Trust Stack Ratings
        4. **Export** reports for stakeholders
        """)

        if st.button("🚀 Start New Analysis", type="primary", use_container_width=True):
            st.session_state['page'] = 'analyze'
            st.rerun()

    st.divider()

    # 5D Trust Dimensions
    st.markdown("### 🔍 5D Trust Dimensions")
    st.markdown("Each piece of content is scored 0-100 on five dimensions:")

    dimensions_cols = st.columns(3)

    dimensions = [
        ("Provenance", "🔗", "Origin, traceability, metadata integrity"),
        ("Verification", "✓", "Factual accuracy vs. trusted databases"),
        ("Transparency", "👁", "Disclosures, clarity, attribution"),
        ("Coherence", "🔄", "Consistency across channels and time"),
        ("Resonance", "📢", "Cultural fit, organic engagement")
    ]

    for idx, (name, icon, desc) in enumerate(dimensions):
        with dimensions_cols[idx % 3]:
            st.markdown(f"**{icon} {name}**")
            st.caption(desc)

    st.divider()

    # Pipeline overview
    st.markdown("### ⚙️ Analysis Pipeline")

    pipeline_steps = [
        ("1. Ingest", "Collect raw content and data from multiple sources\n\n_→ Purpose: Gather inputs._"),
        ("2. Normalize", "Standardize data structure, remove noise, and extract core metadata (source, title, author, date).\n\n_→ Purpose: Prepare clean, consistent inputs._"),
        ("3. Enrich", "Add contextual intelligence — provenance tags, schema markup, fact-check references, and entity recognition.\n\n_→ Purpose: Add meaning and traceability._"),
        ("4. Analyze", "Evaluate enriched content for trust-related patterns and attributes across the five dimensions (Provenance, Resonance, Coherence, Transparency, Verification).\n\n_→ Purpose: Interpret trust signals in context._"),
        ("5. Score", "Apply the 5D rubric to quantify each content item on a 0–100 scale per dimension.\n\n_→ Purpose: Turn analysis into measurable data._"),
        ("6. Synthesize", "Aggregate and weight results into an overall Trust Index or benchmark, highlighting gaps and strengths.\n\n_→ Purpose: Combine scores into a holistic rating._"),
        ("7. Report", "Generate visual outputs (PDF, dashboard, Markdown) with trust maps, insights, and recommended actions.\n\n_→ Purpose: Communicate results and next steps._")
    ]

    cols = st.columns(7)
    for idx, (step, desc) in enumerate(pipeline_steps):
        with cols[idx]:
            st.markdown(f"**{step}**")
            st.caption(desc)


def show_analyze_page():
    """Display the analysis configuration and execution page"""
    st.markdown('<div class="main-header">🚀 Run Analysis</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Configure and execute Trust Stack Rating analysis</div>', unsafe_allow_html=True)

    st.divider()

    # Configuration form
    with st.form("analysis_config"):
        col1, col2 = st.columns(2)

        with col1:
            brand_id = st.text_input(
                "Brand ID*",
                value="",
                placeholder="e.g., nike or mastercard",
                help="Unique identifier for the brand (e.g., 'nike', 'coca-cola'). Enter the desired brand before running analysis."
            )

            keywords = st.text_input(
                "Search Keywords*",
                value="",
                placeholder="Space-separated keywords (e.g., 'brand sustainability')",
                help="Space-separated keywords to search for (e.g., 'nike swoosh'). Required to build the search query."
            )

            max_items = st.number_input(
                "Max Items to Analyze",
                min_value=5,
                max_value=100,
                value=20,
                step=5,
                help="Maximum number of content items to analyze"
            )

        with col2:
            st.markdown("**Data Sources**")

            cfg = APIConfig()

            # Search Provider Selection
            st.markdown("**Web Search Provider**")

            # Check which providers are available
            brave_available = bool(cfg.brave_api_key)
            serper_available = bool(cfg.serper_api_key)

            # Determine default provider
            default_provider = 'serper' if serper_available else 'brave'

            # Create provider options
            provider_options = []
            provider_labels = []

            if brave_available:
                provider_options.append('brave')
                provider_labels.append('🌐 Brave')

            if serper_available:
                provider_options.append('serper')
                provider_labels.append('🔍 Serper')

            if not provider_options:
                st.error("⚠️ No search provider API keys configured. Please set BRAVE_API_KEY or SERPER_API_KEY.")
                search_provider = None
            elif len(provider_options) == 1:
                # Only one provider available, show as info
                search_provider = provider_options[0]
                st.info(f"Using {provider_labels[0]} (only available provider)")
            else:
                # Multiple providers available, let user choose
                default_index = provider_options.index(default_provider) if default_provider in provider_options else 0
                search_provider = st.radio(
                    "Select search provider:",
                    options=provider_options,
                    format_func=lambda x: '🌐 Brave' if x == 'brave' else '🔍 Serper',
                    index=default_index,
                    horizontal=True,
                    help="Choose between Brave Search or Serper (Google) for web search"
                )

            # Web search settings
            use_web_search = st.checkbox(
                "🌐 Enable Web Search",
                value=True,
                disabled=False,
                help="Enable web search to find and collect URLs for analysis."
            )
            # Use max_items for web pages to fetch (removed separate input to avoid confusion)
            web_pages = max_items if use_web_search else max_items

            # Reddit
            reddit_available = bool(cfg.reddit_client_id and cfg.reddit_client_secret)
            use_reddit = st.checkbox(
                "🔴 Reddit",
                value=False,
                disabled=not reddit_available,
                help="Requires REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET" if not reddit_available else "Search Reddit posts and comments"
            )

            # YouTube
            youtube_available = bool(cfg.youtube_api_key)
            use_youtube = st.checkbox(
                "📹 YouTube",
                value=False,
                disabled=not youtube_available,
                help="Requires YOUTUBE_API_KEY" if not youtube_available else "Search YouTube videos and comments"
            )
            include_comments = st.checkbox("Include YouTube comments", value=False) if use_youtube else False

        st.divider()

        # URL Collection Strategy - Simplified Interface
        with st.expander("⚙️ URL Collection Strategy", expanded=False):
            st.markdown("**Choose which URLs to collect:**")

            # Initialize session state for collection strategy if not exists
            if 'collection_strategy' not in st.session_state:
                st.session_state['collection_strategy'] = 'brand_controlled'

            collection_strategy = st.radio(
                "Collection Type",
                options=["brand_controlled", "third_party", "both"],
                format_func=lambda x: {
                    "brand_controlled": "🏢 Brand-Controlled Only",
                    "third_party": "🌐 3rd Party Only",
                    "both": "⚖️ Both (Balanced Collection)"
                }[x],
                index=["brand_controlled", "third_party", "both"].index(st.session_state['collection_strategy']),
                help="Select which type of URLs to collect for analysis",
                key='collection_strategy_radio'
            )

            # Update session state
            st.session_state['collection_strategy'] = collection_strategy

            # Show different help text based on selection
            if collection_strategy == "brand_controlled":
                st.info("📝 **Collecting only from brand-owned domains** (website, blog, social media). Domains auto-detected from brand ID.")
            elif collection_strategy == "third_party":
                st.info("📝 **Collecting only from external sources** (news, reviews, forums, social media).")
            else:  # both
                st.info("📝 **Collecting from both brand-owned and 3rd party sources** for holistic assessment (recommended 60/40 ratio).")

            # Only show ratio slider when "Both" is selected
            if collection_strategy == "both":
                st.markdown("**Adjust Collection Ratio:**")
                col_ratio1, col_ratio2 = st.columns(2)
                with col_ratio1:
                    brand_owned_ratio = st.slider(
                        "Brand-Owned Ratio (%)",
                        min_value=0,
                        max_value=100,
                        value=60,
                        step=5,
                        help="Percentage of URLs from brand-owned domains"
                    )
                with col_ratio2:
                    third_party_ratio = 100 - brand_owned_ratio
                    st.metric("3rd Party Ratio (%)", f"{third_party_ratio}%")
                    st.caption("Auto-calculated")
            else:
                # Set ratio to 100/0 or 0/100 based on selection
                if collection_strategy == "brand_controlled":
                    brand_owned_ratio = 100
                else:  # third_party
                    brand_owned_ratio = 0

            st.divider()

            # Auto-infer brand domains from brand_id
            if collection_strategy in ["brand_controlled", "both"]:
                # Automatically infer brand domains
                inferred = infer_brand_domains(brand_id)

                st.info(f"🤖 **Auto-detected brand domains:** {', '.join(inferred['domains'][:3])}{'...' if len(inferred['domains']) > 3 else ''}")

                # Advanced override option
                with st.expander("⚙️ Advanced: Customize Brand Domains (Optional)", expanded=False):
                    st.caption("The system automatically detects brand domains. Only customize if you need specific overrides.")

                    brand_domains_input = st.text_input(
                        "Override Brand Domains",
                        value="",
                        placeholder="Leave empty to use auto-detected domains",
                        help="Comma-separated list. Leave empty to use auto-detected domains."
                    )

                    brand_subdomains_input = st.text_input(
                        "Additional Subdomains",
                        value="",
                        placeholder="e.g., blog.nike.com, help.nike.com",
                        help="Comma-separated list of specific brand subdomains to add"
                    )

                    brand_social_handles_input = st.text_input(
                        "Additional Social Handles",
                        value="",
                        placeholder="e.g., @nikerunning, nikebasketball",
                        help="Comma-separated list of additional brand social media handles"
                    )

                # Use auto-detected or manual override
                if brand_domains_input.strip():
                    brand_domains = [d.strip() for d in brand_domains_input.split(',') if d.strip()]
                else:
                    brand_domains = inferred['domains']

                # Combine auto-detected with additional manual entries
                if brand_subdomains_input.strip():
                    manual_subdomains = [d.strip() for d in brand_subdomains_input.split(',') if d.strip()]
                    brand_subdomains = list(dict.fromkeys(inferred['subdomains'] + manual_subdomains))
                else:
                    brand_subdomains = inferred['subdomains']

                if brand_social_handles_input.strip():
                    manual_handles = [h.strip() for h in brand_social_handles_input.split(',') if h.strip()]
                    brand_social_handles = list(dict.fromkeys(inferred['social_handles'] + manual_handles))
                else:
                    brand_social_handles = inferred['social_handles']

                # Show confirmation
                if collection_strategy == "brand_controlled":
                    st.success(f"✓ Brand-controlled collection enabled with {len(brand_domains)} auto-detected domains")
            else:
                # No brand identification needed for 3rd party only
                brand_domains = []
                brand_subdomains = []
                brand_social_handles = []

        # DEBUG: Verify this section renders
        st.markdown("---")
        st.markdown("### 🤖 AI Model Configuration")

        # LLM Model Selection
        with st.expander("🤖 LLM Model Selection", expanded=True):
            st.markdown("**Choose which AI model to use for generating executive summaries and recommendations:**")

            col_model1, col_model2 = st.columns(2)

            with col_model1:
                summary_model = st.selectbox(
                    "Executive Summary Model",
                    options=[
                        "gpt-4o-mini",
                        "gpt-3.5-turbo",
                        "gpt-4o",
                        "claude-sonnet-4-20250514",
                        "claude-3-5-haiku-20241022",
                        "claude-3-haiku-20240307",
                        "gemini-1.5-pro",
                        "gemini-1.5-flash",
                        "deepseek-chat",
                        "deepseek-reasoner"
                    ],
                    index=0,  # default to gpt-4o-mini
                    help="Model for generating the main executive summary. Higher-tier models (GPT-4o) produce more detailed, actionable insights."
                )

            with col_model2:
                recommendations_model = st.selectbox(
                    "Recommendations Model",
                    options=[
                        "gpt-4o-mini",
                        "gpt-3.5-turbo",
                        "gpt-4o",
                        "claude-sonnet-4-20250514",
                        "claude-3-5-haiku-20241022",
                        "claude-3-haiku-20240307",
                        "gemini-1.5-pro",
                        "gemini-1.5-flash",
                        "deepseek-chat",
                        "deepseek-reasoner"
                    ],
                    index=0,  # default to gpt-4o-mini
                    help="Model for generating detailed recommendations section in markdown reports."
                )

            # Model information
            model_tiers = {
                'gpt-3.5-turbo': '💰 Budget',
                'gpt-4o-mini': '⚖️ Balanced',
                'gpt-4o': '⭐ Premium',
                'claude-sonnet-4-20250514': '⭐ Premium',
                'claude-3-5-haiku-20241022': '💰 Budget',
                'claude-3-haiku-20240307': '💰 Budget',
                'gemini-1.5-flash': '💰 Budget',
                'gemini-1.5-pro': '⚖️ Balanced',
                'deepseek-chat': '💰 Budget',
                'deepseek-reasoner': '⚖️ Balanced'
            }

            st.info(f"💡 **Selection**: Summary: {model_tiers.get(summary_model, '')} {summary_model} | Recommendations: {model_tiers.get(recommendations_model, '')} {recommendations_model}")
            st.caption("💡 **Tip**: Use premium models (Claude Sonnet 4, GPT-4o) for highest quality summaries with specific, actionable recommendations.")

        st.divider()

        col_search, col_submit, col_clear = st.columns([1, 1, 3])
        with col_search:
            search_urls = st.form_submit_button("🔍 Search URLs", use_container_width=True)
        with col_submit:
            submit = st.form_submit_button("▶️ Run Analysis", type="primary", use_container_width=True)
        with col_clear:
            if st.form_submit_button("Clear Results", use_container_width=True):
                st.session_state['last_run'] = None
                st.session_state['found_urls'] = None
                # clear any fallback indicator
                if 'llm_search_fallback' in st.session_state:
                    del st.session_state['llm_search_fallback']
                if 'llm_search_fallback_count' in st.session_state:
                    del st.session_state['llm_search_fallback_count']
                st.rerun()

    # Handle URL search
    if search_urls:
        # Validate inputs
        if not brand_id or not keywords:
            st.error("⚠️ Brand ID and Keywords are required")
            return

        # Build sources list
        sources = []
        if use_web_search:
            sources.append('web')
        if use_reddit:
            sources.append('reddit')
        if use_youtube:
            sources.append('youtube')

        if not sources:
            st.error("⚠️ Please select at least one data source")
            return

        # Search for URLs without running analysis
        search_for_urls(brand_id, keywords.split(), sources, web_pages, search_provider,
                       brand_domains, brand_subdomains, brand_social_handles,
                       collection_strategy, brand_owned_ratio)

    # Display found URLs for selection
    if 'found_urls' in st.session_state and st.session_state['found_urls']:
        st.markdown("### 📋 Found URLs")

        found_urls = st.session_state['found_urls']

        # Separate URLs into brand-owned and third-party
        brand_owned_urls = [u for u in found_urls if u.get('is_brand_owned', False)]
        third_party_urls = [u for u in found_urls if not u.get('is_brand_owned', False)]

        # Overall select/deselect buttons
        col_sel_all, col_desel_all, col_stats = st.columns([1, 1, 2])
        with col_sel_all:
            if st.button("✓ Select All"):
                for url_data in found_urls:
                    url_data['selected'] = True
                st.rerun()
        with col_desel_all:
            if st.button("✗ Deselect All"):
                for url_data in found_urls:
                    url_data['selected'] = False
                st.rerun()
        with col_stats:
            st.info(f"📊 Selected {sum(1 for u in found_urls if u.get('selected', True))} of {len(found_urls)} URLs")

        st.divider()

        # Brand-Owned URLs Section
        if brand_owned_urls:
            st.markdown("#### 🏢 Brand-Owned URLs")
            st.caption(f"{len(brand_owned_urls)} URLs from brand domains")

            for idx, url_data in enumerate(brand_owned_urls):
                col1, col2 = st.columns([1, 10])
                with col1:
                    url_data['selected'] = st.checkbox(
                        "Select",
                        value=url_data.get('selected', True),
                        key=f"brand_url_{idx}",
                        label_visibility="collapsed"
                    )
                with col2:
                    # Tier badge
                    tier = url_data.get('source_tier', 'unknown')
                    tier_emoji = {
                        'primary_website': '🏠',
                        'content_hub': '📚',
                        'direct_to_consumer': '🛒',
                        'brand_social': '📱'
                    }.get(tier, '📄')
                    tier_label = tier.replace('_', ' ').title()

                    # Show title with tier and soft-verify badge if present
                    short_title = url_data.get('title', url_data.get('url', ''))[:70]
                    ellips = '...' if len(url_data.get('title', '')) > 70 else ''
                    title_line = f"**{short_title}{ellips}** {tier_emoji} `{tier_label}`"
                    if url_data.get('soft_verified'):
                        # Show a clear soft-verified badge with method (DNS resolution, etc.)
                        method = url_data.get('verification_method') or url_data.get('method') or 'soft-verified'
                        title_line += f" ⚠️ *Soft-verified ({method})*"

                    st.markdown(title_line)
                    # Show URL and optionally verification status
                    status = url_data.get('status')
                    if status:
                        st.caption(f"🔗 {url_data['url']} — HTTP {status}")
                    else:
                        st.caption(f"🔗 {url_data['url']}")

            st.divider()

        # Third-Party URLs Section
        if third_party_urls:
            st.markdown("#### 🌐 Third-Party URLs")
            st.caption(f"{len(third_party_urls)} URLs from external sources")

            for idx, url_data in enumerate(third_party_urls):
                col1, col2 = st.columns([1, 10])
                with col1:
                    url_data['selected'] = st.checkbox(
                        "Select",
                        value=url_data.get('selected', True),
                        key=f"third_party_url_{idx}",
                        label_visibility="collapsed"
                    )
                with col2:
                    # Tier badge
                    tier = url_data.get('source_tier', 'unknown')
                    tier_emoji = {
                        'news_media': '📰',
                        'user_generated': '👥',
                        'expert_professional': '🎓',
                        'marketplace': '🏪'
                    }.get(tier, '🌐')
                    tier_label = tier.replace('_', ' ').title()

                    # Show title with tier and soft-verify badge if present
                    short_title = url_data.get('title', url_data.get('url', ''))[:70]
                    ellips = '...' if len(url_data.get('title', '')) > 70 else ''
                    title_line = f"**{short_title}{ellips}** {tier_emoji} `{tier_label}`"
                    if url_data.get('soft_verified'):
                        method = url_data.get('verification_method') or url_data.get('method') or 'soft-verified'
                        title_line += f" ⚠️ *Soft-verified ({method})*"

                    st.markdown(title_line)
                    status = url_data.get('status')
                    if status:
                        st.caption(f"🔗 {url_data['url']} — HTTP {status}")
                    else:
                        st.caption(f"🔗 {url_data['url']}")

    if submit:
        # Validate inputs
        if not brand_id or not keywords:
            st.error("⚠️ Brand ID and Keywords are required")
            return

        # Build sources list
        sources = []
        if use_web_search:
            sources.append('web')
        if use_reddit:
            sources.append('reddit')
        if use_youtube:
            sources.append('youtube')

        if not sources:
            st.error("⚠️ Please select at least one data source")
            return

        # Check if URLs were searched and selected
        selected_urls = None
        if 'found_urls' in st.session_state and st.session_state['found_urls']:
            selected_urls = [u for u in st.session_state['found_urls'] if u.get('selected', True)]
            if not selected_urls:
                st.error("⚠️ Please select at least one URL to analyze")
                return

        # Run pipeline
        run_analysis(brand_id, keywords.split(), sources, max_items, web_pages, include_comments, selected_urls, search_provider,
                    brand_domains, brand_subdomains, brand_social_handles,
                    summary_model=summary_model, recommendations_model=recommendations_model)


def detect_brand_owned_url(url: str, brand_id: str, brand_domains: List[str] = None, brand_subdomains: List[str] = None, brand_social_handles: List[str] = None) -> Dict[str, Any]:
    """
    Detect if a URL is a brand-owned property using the domain classifier.

    Returns:
        Dict with keys: is_brand_owned (bool), source_type (str), source_tier (str), reason (str)
    """
    try:
        from ingestion.domain_classifier import classify_url, URLCollectionConfig, URLSourceType

        # Create config for classification
        if brand_domains:
            config = URLCollectionConfig(
                brand_owned_ratio=0.6,
                third_party_ratio=0.4,
                brand_domains=brand_domains or [],
                brand_subdomains=brand_subdomains or [],
                brand_social_handles=brand_social_handles or []
            )
        else:
            # Fallback to simple heuristic if no domains provided
            from urllib.parse import urlparse
            domain = urlparse(url).netloc.lower().replace('www.', '')
            is_owned = brand_id.lower() in domain
            return {
                'is_brand_owned': is_owned,
                'source_type': 'brand_owned' if is_owned else 'third_party',
                'source_tier': 'primary_website' if is_owned else 'user_generated',
                'reason': f"Simple heuristic: {brand_id} {'found' if is_owned else 'not found'} in domain"
            }

        # Use domain classifier
        classification = classify_url(url, config)
        return {
            'is_brand_owned': classification.source_type == URLSourceType.BRAND_OWNED,
            'source_type': classification.source_type.value,
            'source_tier': classification.tier.value if classification.tier else 'unknown',
            'reason': classification.reason
        }
    except Exception as e:
        # Fallback on error
        return {
            'is_brand_owned': False,
            'source_type': 'unknown',
            'source_tier': 'unknown',
            'reason': f"Classification error: {str(e)}"
        }


def search_for_urls(brand_id: str, keywords: List[str], sources: List[str], web_pages: int, search_provider: str = 'serper',
                    brand_domains: List[str] = None, brand_subdomains: List[str] = None, brand_social_handles: List[str] = None,
                    collection_strategy: str = 'both', brand_owned_ratio: int = 60):
    """Search for URLs and store them in session state for user selection"""
    import os
    import logging

    # Set up logging
    logger = logging.getLogger(__name__)

    progress_animator = ProgressAnimator()
    progress_bar = st.progress(0)

    try:
        progress_animator.show("Initializing web search engine...", "🚀")
        progress_bar.progress(10)

        found_urls = []

        # Web search (using selected provider: Brave or Serper)
        if 'web' in sources:
            base_query = ' '.join(keywords)

            # For brand-controlled searches, use LLM to discover domains and restrict search
            if collection_strategy == 'brand_controlled':
                # Check cache first to avoid repeated LLM calls
                cache_key = f'brand_domains_{brand_id}'
                if cache_key in st.session_state:
                    llm_domains = st.session_state[cache_key]
                    logger.info(f'Using cached domains for {brand_id}: {llm_domains}')
                    progress_animator.show(f"Using {len(llm_domains)} cached brand domains for {brand_id}", "📦")
                else:
                    progress_animator.show(f"Discovering brand domains for {brand_id} using AI...", "🤖")
                    llm_domains = get_brand_domains_from_llm(brand_id, model='gpt-4o-mini')
                    # Cache for this session
                    st.session_state[cache_key] = llm_domains

                if llm_domains:
                    # Build site-restricted query using discovered domains
                    site_filters = " OR ".join([f"site:{domain}" for domain in llm_domains[:10]])
                    query = f"{base_query} ({site_filters})"
                    logger.info(f'Built site-restricted query for {brand_id}: {len(llm_domains)} domains')
                    progress_animator.show(f"Targeting {len(llm_domains)} verified brand domains", "🎯")
                else:
                    # Fallback to regular query if LLM fails
                    query = base_query
                    logger.warning(f'LLM domain discovery returned no domains for {brand_id}, using regular query')
                    progress_animator.show("Proceeding with general web search", "🌐")
            else:
                query = base_query

            provider_display = 'Brave Search' if search_provider == 'brave' else 'Google (via Serper)'
            provider_emoji = '🌐' if search_provider == 'brave' else '🔍'
            progress_animator.show(f"Querying {provider_display} for: {query[:80]}...", provider_emoji)
            progress_bar.progress(30)

            try:
                # Configure timeout for larger requests (scale with number of pages)
                # Each pagination batch needs time, so scale appropriately
                original_timeout = os.environ.get('BRAVE_API_TIMEOUT')
                timeout_seconds = min(30, 10 + (web_pages // 10))
                os.environ['BRAVE_API_TIMEOUT'] = str(timeout_seconds)

                # Calculate expected number of API requests
                if search_provider == 'brave':
                    max_per_request = int(os.getenv('BRAVE_API_MAX_COUNT', '20'))
                else:  # serper
                    # Serper returns 10 results per page, regardless of the num parameter
                    max_per_request = 10

                expected_requests = (web_pages + max_per_request - 1) // max_per_request  # Ceiling division

                if expected_requests > 1:
                    logger.info(f"Searching {search_provider}: query={query}, size={web_pages}, will make ~{expected_requests} paginated requests")
                    progress_animator.show(f"Preparing {expected_requests} API requests to fetch {web_pages} URLs", "📡")
                else:
                    logger.info(f"Searching {search_provider}: query={query}, size={web_pages}")
                    progress_animator.show(f"Fetching up to {web_pages} search results", "📡")

                # Create URLCollectionConfig for ratio enforcement
                url_collection_config = None
                if collection_strategy in ["brand_controlled", "both", "third_party"]:
                    # For brand_controlled and both, we need brand_domains to identify brand URLs
                    # For third_party, we can proceed with empty brand_domains (everything is 3rd party)
                    if collection_strategy in ["brand_controlled", "both"] and not brand_domains:
                        logger.warning(f"Cannot use {collection_strategy} strategy without brand_domains, falling back to no ratio enforcement")
                    else:
                        from ingestion.domain_classifier import URLCollectionConfig

                        # Convert percentage to decimal ratio
                        brand_ratio = brand_owned_ratio / 100.0
                        third_party_ratio = 1.0 - brand_ratio

                        url_collection_config = URLCollectionConfig(
                            brand_owned_ratio=brand_ratio,
                            third_party_ratio=third_party_ratio,
                            brand_domains=brand_domains or [],
                            brand_subdomains=brand_subdomains or [],
                            brand_social_handles=brand_social_handles or []
                        )
                        logger.info(f"Created URLCollectionConfig with {collection_strategy} strategy: {brand_ratio:.1%} brand-owned, {third_party_ratio:.1%} 3rd party")

                progress_bar.progress(50)

                # Use collect functions for ratio enforcement
                search_results = []
                # Use 5x pool size to account for access-denied URLs and stricter content filtering
                pool_size = web_pages * 5

                progress_animator.show(f"Collecting from pool of {pool_size} URLs with {collection_strategy} filtering", "🔄")

                if search_provider == 'brave':
                    from ingestion.brave_search import collect_brave_pages
                    progress_animator.show(f"Executing Brave Search API requests ({brand_owned_ratio}% brand-owned target)", "⚡")
                    pages = collect_brave_pages(
                        query=query,
                        target_count=web_pages,
                        pool_size=pool_size,
                        url_collection_config=url_collection_config
                    )
                    # Convert to search result format and show URLs as we process them
                    total_pages = len(pages)
                    for idx, page in enumerate(pages):
                        url = page.get('url', '')
                        # Show each URL as it's being inspected
                        progress_animator.show(
                            f"Inspecting result {idx + 1}/{total_pages}",
                            "🔍",
                            url=url
                        )
                        search_results.append({
                            'url': url,
                            'title': page.get('title', 'No title'),
                            'snippet': page.get('body', '')[:200]
                        })
                        # Update progress proportionally (50% -> 70%)
                        progress_percent = 50 + int((idx + 1) / total_pages * 20)
                        progress_bar.progress(min(progress_percent, 70))
                else:  # serper
                    from ingestion.serper_search import collect_serper_pages
                    progress_animator.show(f"Executing Google Search API requests ({brand_owned_ratio}% brand-owned target)", "⚡")
                    pages = collect_serper_pages(
                        query=query,
                        target_count=web_pages,
                        pool_size=pool_size,
                        url_collection_config=url_collection_config
                    )
                    # Convert to search result format and show URLs as we process them
                    total_pages = len(pages)
                    for idx, page in enumerate(pages):
                        url = page.get('url', '')
                        # Show each URL as it's being inspected
                        progress_animator.show(
                            f"Inspecting result {idx + 1}/{total_pages}",
                            "🔍",
                            url=url
                        )
                        search_results.append({
                            'url': url,
                            'title': page.get('title', 'No title'),
                            'snippet': page.get('body', '')[:200]
                        })
                        # Update progress proportionally (50% -> 70%)
                        progress_percent = 50 + int((idx + 1) / total_pages * 20)
                        progress_bar.progress(min(progress_percent, 70))

                progress_bar.progress(70)

                # Restore original timeout
                if original_timeout is not None:
                    os.environ['BRAVE_API_TIMEOUT'] = original_timeout
                else:
                    os.environ.pop('BRAVE_API_TIMEOUT', None)

                if not search_results:
                    st.warning(f"⚠️ No search results found. Try different keywords or check your {search_provider.upper()} API configuration.")

                    # Provide helpful diagnostics
                    st.info("**Troubleshooting tips:**")
                    if search_provider == 'brave':
                        st.markdown("""
                        - **Check your Brave API key**: Ensure `BRAVE_API_KEY` environment variable is set
                        - **Check the logs**: Look at the terminal/console for detailed error messages
                        - **Try fewer pages**: Start with 10-20 pages to test the connection
                        - **Verify API quota**: Your Brave API plan may have reached its limit
                        - **Check search query**: Try simpler, more common keywords first
                        """)
                    else:  # serper
                        st.markdown("""
                        - **Check your Serper API key**: Ensure `SERPER_API_KEY` environment variable is set
                        - **Check the logs**: Look at the terminal/console for detailed error messages
                        - **Try fewer pages**: Start with 10-20 pages to test the connection
                        - **Verify API quota**: Your Serper API plan may have reached its limit
                        - **Check search query**: Try simpler, more common keywords first
                        """)

                    # Show current configuration for debugging
                    with st.expander("🔍 Show Configuration Details"):
                        if search_provider == 'brave':
                            st.code(f"""
Provider: Brave Search
Query: {query}
Pages requested: {web_pages}
Timeout: {timeout_seconds}s
API Key set: {'Yes' if os.getenv('BRAVE_API_KEY') else 'No'}
API Endpoint: {os.getenv('BRAVE_API_ENDPOINT', 'https://api.search.brave.com/res/v1/web/search')}
""")
                        else:
                            st.code(f"""
Provider: Serper (Google Search)
Query: {query}
Pages requested: {web_pages}
Timeout: {timeout_seconds}s
API Key set: {'Yes' if os.getenv('SERPER_API_KEY') else 'No'}
""")

                    progress_bar.empty()
                    progress_animator.clear()
                    return

                # Classify URLs and show them as we process them
                total_results = len(search_results)
                for idx, result in enumerate(search_results):
                    url = result.get('url', '')
                    if url:
                        # Show the current URL being classified (rotate through them)
                        progress_animator.show(
                            f"Classifying URL {idx + 1}/{total_results}",
                            "🏷️",
                            url=url
                        )

                        classification = detect_brand_owned_url(url, brand_id, brand_domains, brand_subdomains, brand_social_handles)
                        found_urls.append({
                            'url': url,
                            'title': result.get('title', 'No title'),
                            'description': result.get('snippet', result.get('description', '')),
                            'is_brand_owned': classification['is_brand_owned'],
                            'source_type': classification['source_type'],
                            'source_tier': classification['source_tier'],
                            'classification_reason': classification['reason'],
                            'selected': True,  # Default to selected
                            'source': search_provider
                        })

                        # Update progress bar proportionally (70% -> 90%)
                        progress_percent = 70 + int((idx + 1) / total_results * 20)
                        progress_bar.progress(min(progress_percent, 90))

                # Prioritize brand-owned URLs by sorting them first
                # This ensures brand domains appear at the top of the list
                found_urls.sort(key=lambda x: (not x['is_brand_owned'], x['url']))
                logger.info(f"Sorted {len(found_urls)} URLs with brand-owned URLs prioritized")

                progress_bar.progress(90)
                st.session_state['found_urls'] = found_urls

                brand_owned_count = sum(1 for u in found_urls if u['is_brand_owned'])
                third_party_count = sum(1 for u in found_urls if not u['is_brand_owned'])

                progress_bar.progress(100)
                progress_animator.show(f"Search complete! Found {brand_owned_count} brand + {third_party_count} 3rd-party URLs", "✅")
                progress_animator.clear()
                progress_bar.empty()

                st.success(f"✓ Found {len(found_urls)} URLs ({brand_owned_count} brand-owned, {third_party_count} third-party)")
                st.rerun()

            except TimeoutError as e:
                logger.error(f"Timeout error during {search_provider} search: {e}")
                st.error(f"⏱️ Search timed out after {timeout_seconds} seconds. Try requesting fewer URLs or check your network connection.")

            except ConnectionError as e:
                logger.error(f"Connection error during {search_provider} search: {e}")
                st.error(f"🌐 Connection error: Could not reach {search_provider.upper()} API. Please check your internet connection.")

            except Exception as e:
                logger.error(f"Error during {search_provider} search: {type(e).__name__}: {e}")
                st.error(f"❌ Search failed: {type(e).__name__}: {str(e)}")

                # Show more helpful error messages for common issues
                if 'api' in str(e).lower() or 'key' in str(e).lower():
                    api_key_name = 'BRAVE_API_KEY' if search_provider == 'brave' else 'SERPER_API_KEY'
                    st.info(f"💡 Tip: Check that your {api_key_name} is set correctly in your environment.")
                elif 'timeout' in str(e).lower():
                    st.info("💡 Tip: Try reducing the number of web pages to fetch, or check your network connection.")

    except Exception as e:
        logger.error(f"Unexpected error in search_for_urls: {type(e).__name__}: {e}")
        st.error(f"❌ Unexpected error: {type(e).__name__}: {str(e)}")

    finally:
        # Clean up progress indicators
        try:
            progress_bar.empty()
            progress_animator.clear()
        except:
            pass


def run_analysis(brand_id: str, keywords: List[str], sources: List[str], max_items: int, web_pages: int, include_comments: bool,
                 selected_urls: List[Dict] = None, search_provider: str = 'serper',
                 brand_domains: List[str] = None, brand_subdomains: List[str] = None, brand_social_handles: List[str] = None,
                 summary_model: str = 'gpt-4o-mini', recommendations_model: str = 'gpt-4o-mini'):
    """Execute the analysis pipeline"""

    # Create output directory
    output_dir = os.path.join(PROJECT_ROOT, 'output', 'webapp_runs')
    os.makedirs(output_dir, exist_ok=True)

    run_id = datetime.now().strftime('%Y%m%d_%H%M%S')
    run_dir = os.path.join(output_dir, f"{brand_id}_{run_id}")
    os.makedirs(run_dir, exist_ok=True)

    # Progress tracking
    progress_bar = st.progress(0)
    status_text = st.empty()

    try:
        # Step 1: Import modules
        status_text.text("Initializing pipeline components...")
        progress_bar.progress(10)

        from ingestion.brave_search import collect_brave_pages, fetch_page
        from ingestion.normalizer import ContentNormalizer
        from scoring.pipeline import ScoringPipeline
        from reporting.pdf_generator import PDFReportGenerator
        from reporting.markdown_generator import MarkdownReportGenerator
        from data.models import NormalizedContent

        try:
            from ingestion.reddit_crawler import RedditCrawler
        except:
            RedditCrawler = None

        try:
            from ingestion.youtube_scraper import YouTubeScraper
        except:
            YouTubeScraper = None

        # Step 2: Data Ingestion
        status_text.text(f"Ingesting content from {', '.join(sources)}...")
        progress_bar.progress(20)

        all_content = []

        # Web search ingestion (using selected provider)
        if 'web' in sources:
            # If URLs were pre-selected, use only those
            if selected_urls:
                # Filter URLs from the current search provider
                selected_web_urls = [u for u in selected_urls if u['source'] in ['brave', 'serper', 'web']]
                collected = []

                for url_data in selected_web_urls:
                    try:
                        page_data = fetch_page(url_data['url'])
                        if page_data and page_data.get('body'):
                            # Add brand-owned flag to metadata
                            page_data['is_brand_owned'] = url_data.get('is_brand_owned', False)
                            collected.append(page_data)
                    except Exception as e:
                        st.warning(f"⚠️ Could not fetch {url_data['url']}: {str(e)}")

                st.info(f"✓ Fetched {len(collected)} of {len(selected_web_urls)} selected web pages")
            else:
                # Original behavior: search and fetch automatically
                query = ' '.join(keywords)

                # Use the unified search interface with the selected provider
                from ingestion.search_unified import search
                search_results = search(query, size=web_pages, provider=search_provider)

                collected = []
                for result in search_results:
                    url = result.get('url', '')
                    if url:
                        try:
                            page_data = fetch_page(url)
                            if page_data and page_data.get('body'):
                                # Add metadata from search result
                                page_data['search_title'] = result.get('title', '')
                                page_data['search_snippet'] = result.get('snippet', '')
                                classification = detect_brand_owned_url(url, brand_id, brand_domains, brand_subdomains, brand_social_handles)
                                page_data['is_brand_owned'] = classification['is_brand_owned']
                                page_data['source_type'] = classification['source_type']
                                page_data['source_tier'] = classification['source_tier']
                                collected.append(page_data)
                        except Exception as e:
                            st.warning(f"⚠️ Could not fetch {url}: {str(e)}")

                st.info(f"✓ Collected {len(collected)} web pages using {search_provider}")

            # Convert to NormalizedContent
            for i, c in enumerate(collected):
                url = c.get('url')
                content_id = f"{search_provider}_{i}_{abs(hash(url or ''))}"
                is_brand_owned = c.get('is_brand_owned', False)

                meta = {
                    'source_url': url or '',
                    'content_type': 'web',
                    'title': c.get('title', ''),
                    'description': c.get('body', '')[:200],
                    'is_brand_owned': is_brand_owned,  # Add brand-owned flag to metadata
                    'search_provider': search_provider  # Track which provider was used
                }
                if c.get('terms'):
                    meta['terms'] = c.get('terms')
                if c.get('privacy'):
                    meta['privacy'] = c.get('privacy')

                nc = NormalizedContent(
                    content_id=content_id,
                    src=search_provider,
                    platform_id=url or '',
                    author='web',
                    title=c.get('title', '') or '',
                    body=c.get('body', '') or '',
                    run_id=run_id,
                    event_ts=datetime.now().isoformat(),
                    meta=meta,
                    url=url or '',
                    modality='text',
                    channel='web',
                    platform_type='web',
                    source_type=c.get('source_type', 'unknown'),
                    source_tier=c.get('source_tier', 'unknown')
                )
                all_content.append(nc)

        # Reddit ingestion
        if 'reddit' in sources and RedditCrawler:
            try:
                reddit = RedditCrawler()
                posts = reddit.search_posts(keywords=keywords, limit=max_items // len(sources))
                reddit_content = reddit.convert_to_normalized_content(posts, brand_id, run_id)
                all_content.extend(reddit_content)
                st.info(f"✓ Collected {len(reddit_content)} Reddit posts")
            except Exception as e:
                st.warning(f"⚠️ Reddit ingestion failed: {e}")

        # YouTube ingestion
        if 'youtube' in sources and YouTubeScraper:
            try:
                yt = YouTubeScraper()
                query = ' '.join(keywords)
                videos = yt.search_videos(query=query, max_results=max_items // len(sources))
                youtube_content = yt.convert_videos_to_normalized(videos, brand_id, run_id, include_comments=include_comments)
                all_content.extend(youtube_content)
                st.info(f"✓ Collected {len(youtube_content)} YouTube videos")
            except Exception as e:
                st.warning(f"⚠️ YouTube ingestion failed: {e}")

        if not all_content:
            st.error("❌ No content collected from any source")
            return

        # Step 3: Normalization
        status_text.text("Normalizing content...")
        progress_bar.progress(40)

        normalizer = ContentNormalizer()
        normalized_content = normalizer.normalize_content(all_content)

        # Step 4: Scoring
        status_text.text("Scoring content on 6D Trust dimensions...")
        progress_bar.progress(60)

        scoring_pipeline = ScoringPipeline()
        brand_config = {
            'brand_id': brand_id,
            'brand_name': brand_id,
            'keywords': keywords,
            'sources': sources
        }

        pipeline_run = scoring_pipeline.run_scoring_pipeline(normalized_content, brand_config)

        # Step 5: Generate Reports
        status_text.text("Generating reports...")
        progress_bar.progress(80)

        scores_list = pipeline_run.classified_scores or []
        scoring_report = scoring_pipeline.generate_scoring_report(scores_list, brand_config)

        # Add LLM model configuration to the report for use in executive summary
        scoring_report['llm_model'] = summary_model
        scoring_report['recommendations_model'] = recommendations_model
        scoring_report['use_llm_summary'] = True  # Enable LLM-powered summaries

        # Generate PDF
        pdf_generator = PDFReportGenerator()
        pdf_path = os.path.join(run_dir, f'ar_report_{brand_id}_{run_id}.pdf')
        pdf_generator.generate_report(scoring_report, pdf_path, include_items_table=True)

        # Generate Markdown
        markdown_generator = MarkdownReportGenerator()
        md_path = os.path.join(run_dir, f'ar_report_{brand_id}_{run_id}.md')
        markdown_generator.generate_report(scoring_report, md_path)

        # Save run data for visualization
        run_data = {
            'run_id': run_id,
            'brand_id': brand_id,
            'keywords': keywords,
            'sources': sources,
            'timestamp': datetime.now().isoformat(),
            'pdf_path': pdf_path,
            'md_path': md_path,
            'scoring_report': scoring_report,
            'total_items': len(normalized_content)
        }

        data_path = os.path.join(run_dir, '_run_data.json')
        with open(data_path, 'w') as f:
            json.dump(run_data, f, indent=2, default=str)

        # Complete
        progress_bar.progress(100)
        status_text.text("✓ Analysis complete!")

        st.success(f"✅ Analysis completed successfully! Analyzed {len(normalized_content)} content items.")

        # Store in session state
        st.session_state['last_run'] = run_data

        # Switch to results view
        time.sleep(1)
        st.session_state['page'] = 'results'
        st.rerun()

    except Exception as e:
        st.error(f"❌ Analysis failed: {e}")
        import traceback
        st.code(traceback.format_exc())


def programmatic_quick_run(urls: List[str], output_dir: str = None, brand_id: str = 'brand') -> Dict[str, Any]:
    """Programmatic helper used by tests to run the pipeline for a set of URLs.

    This function delegates to scripts.run_pipeline.run_pipeline_for_contents and
    returns the resulting dict. Tests may monkeypatch that function to simulate
    pipeline behavior.
    """
    try:
        from scripts.run_pipeline import run_pipeline_for_contents
    except Exception as e:
        raise RuntimeError(f"Could not import run_pipeline_for_contents: {e}")

    out_dir = output_dir or os.path.join(PROJECT_ROOT, 'output')
    os.makedirs(out_dir, exist_ok=True)

    # Delegate to pipeline runner
    result = run_pipeline_for_contents(urls, output_dir=out_dir, brand_id=brand_id)
    return result


def show_results_page():
    """Display analysis results with visualizations"""

    # Load last run or selected run
    run_data = st.session_state.get('last_run')

    if not run_data:
        st.warning("⚠️ No analysis results available. Please run an analysis first.")
        if st.button("← Back to Analysis"):
            st.session_state['page'] = 'analyze'
            st.rerun()
        return

    report = run_data.get('scoring_report', {})
    items = report.get('items', [])

    # Calculate average comprehensive rating
    if items:
        avg_rating = sum(item.get('final_score', 0) for item in items) / len(items)
    else:
        avg_rating = 0

    # Calculate rating distribution
    excellent = sum(1 for item in items if item.get('final_score', 0) >= 80)
    good = sum(1 for item in items if 60 <= item.get('final_score', 0) < 80)
    fair = sum(1 for item in items if 40 <= item.get('final_score', 0) < 60)
    poor = sum(1 for item in items if item.get('final_score', 0) < 40)

    # Header
    st.markdown('<div class="main-header">⭐ Trust Stack Results</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="sub-header">Brand: {run_data.get("brand_id")} | Run: {run_data.get("run_id")}</div>', unsafe_allow_html=True)

    # Display model info (read-only - model was selected before analysis)
    summary_model_used = report.get('llm_model', 'gpt-4o-mini')
    recommendations_model_used = report.get('recommendations_model', 'gpt-4o-mini')

    with st.expander("ℹ️ AI Models Used", expanded=False):
        st.markdown("**Models selected for this analysis:**")
        st.info(f"📝 **Executive Summary**: {summary_model_used}\n\n📋 **Recommendations**: {recommendations_model_used}")
        st.caption("💡 Models are selected on the analysis page before running. To use different models, run a new analysis.")

    st.divider()

    # Key Metrics
    st.markdown("### 🎯 Key Metrics")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="Average Rating",
            value=f"{avg_rating:.1f}/100",
            delta=None
        )

    with col2:
        st.metric(
            label="Total Content",
            value=f"{len(items):,}"
        )

    with col3:
        st.metric(
            label="Excellent (80+)",
            value=f"{excellent:,}",
            delta=f"{(excellent/len(items)*100):.0f}%" if items else "0%"
        )

    with col4:
        st.metric(
            label="Poor (<40)",
            value=f"{poor:,}",
            delta=f"{(poor/len(items)*100):.0f}%" if items else "0%"
        )

    # Generate Executive Summary using new module
    dimension_breakdown = report.get('dimension_breakdown', {})
    sources = report.get('sources', ['unknown'])

    # Import the new executive summary module
    from reporting.executive_summary import generate_executive_summary

    # Generate summary using models that were selected before analysis
    try:
        recommendation = generate_executive_summary(
            avg_rating=avg_rating,
            dimension_breakdown=dimension_breakdown,
            items=items,
            sources=sources,
            model=summary_model_used,
            use_llm=True  # Always use LLM for web app
        )
    except Exception as e:
        st.error(f"Executive summary generation failed: {e}")
        # Fallback to template
        recommendation = generate_rating_recommendation(avg_rating, dimension_breakdown, items)

    if avg_rating >= 80:
        st.markdown(f'<div class="success-box">🟢 <b>Excellent</b> - {recommendation}</div>', unsafe_allow_html=True)
    elif avg_rating >= 60:
        st.markdown(f'<div class="info-box">🟡 <b>Good</b> - {recommendation}</div>', unsafe_allow_html=True)
    elif avg_rating >= 40:
        st.markdown(f'<div class="warning-box">🟠 <b>Fair</b> - {recommendation}</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="warning-box">🔴 <b>Poor</b> - {recommendation}</div>', unsafe_allow_html=True)

    st.divider()

    # Visualizations
    col1, col2 = st.columns(2)

    with col1:
        # Rating Distribution Pie Chart
        st.markdown("#### Rating Distribution")

        fig_pie = px.pie(
            values=[excellent, good, fair, poor],
            names=['Excellent (80+)', 'Good (60-79)', 'Fair (40-59)', 'Poor (<40)'],
            color_discrete_map={
                'Excellent (80+)': '#2ecc71',
                'Good (60-79)': '#3498db',
                'Fair (40-59)': '#f39c12',
                'Poor (<40)': '#e74c3c'
            },
            hole=0.3
        )
        fig_pie.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig_pie, use_container_width=True, config={'displayModeBar': False})

    with col2:
        # Rating Score Distribution Histogram
        st.markdown("#### Score Distribution")

        scores = [item.get('final_score', 0) for item in items]

        fig_hist = go.Figure(data=[
            go.Histogram(
                x=scores,
                nbinsx=20,
                marker_color='#3498db',
                opacity=0.7
            )
        ])
        fig_hist.update_layout(
            xaxis_title="Rating Score (0-100)",
            yaxis_title="Number of Items",
            showlegend=False,
            height=350
        )
        # Add threshold lines
        fig_hist.add_vline(x=80, line_dash="dash", line_color="green", annotation_text="Excellent")
        fig_hist.add_vline(x=60, line_dash="dash", line_color="blue", annotation_text="Good")
        fig_hist.add_vline(x=40, line_dash="dash", line_color="orange", annotation_text="Fair")
        st.plotly_chart(fig_hist, use_container_width=True, config={'displayModeBar': False})

    st.divider()

    # Remedies Section - NEW!
    st.markdown("### 🔧 Remedies: Recommended Fixes by Dimension")

    dimension_issues = extract_issues_from_items(items)

    # Count total issues per dimension
    issue_counts = {dim: len(issues) for dim, issues in dimension_issues.items()}
    total_issues = sum(issue_counts.values())

    if total_issues > 0:
        st.markdown(f"**Found {total_issues} specific issues across {sum(1 for c in issue_counts.values() if c > 0)} dimensions**")

        # Display remedies for each dimension with issues
        for dimension_key in ['provenance', 'verification', 'transparency', 'coherence', 'resonance']:
            issues = dimension_issues.get(dimension_key, [])
            if not issues:
                continue

            dimension_names = {
                'provenance': ('🔗 Provenance', 'Origin & Metadata Issues'),
                'verification': ('✓ Verification', 'Accuracy & Verification Issues'),
                'transparency': ('👁 Transparency', 'Disclosure & Attribution Issues'),
                'coherence': ('🔄 Coherence', 'Consistency Issues'),
                'resonance': ('📢 Resonance', 'Engagement & Relevance Issues')
            }

            dim_emoji_name, dim_subtitle = dimension_names[dimension_key]

            with st.expander(f"{dim_emoji_name}: {len(issues)} issues found", expanded=(dimension_key == min(issue_counts, key=issue_counts.get) if issue_counts else False)):
                st.markdown(f"**{dim_subtitle}**")
                st.markdown("---")

                # Group issues by type
                issues_by_type = {}
                for issue in issues:
                    issue_type = issue['issue']
                    if issue_type not in issues_by_type:
                        issues_by_type[issue_type] = []
                    issues_by_type[issue_type].append(issue)

                # Display each issue type with affected pages
                for issue_type, type_issues in issues_by_type.items():
                    st.markdown(f"**⚠️ {issue_type}** ({len(type_issues)} occurrence{'s' if len(type_issues) > 1 else ''})")

                    # Show remedy recommendation based on issue type
                    remedy = get_remedy_for_issue(issue_type, dimension_key)
                    if remedy:
                        st.info(f"**💡 Recommended Fix:** {remedy}")

                    # Show first few affected pages
                    with st.expander(f"View affected content ({len(type_issues)} items)"):
                        for idx, issue in enumerate(type_issues[:10]):  # Limit to first 10
                            st.markdown(f"- **{issue['title']}**")
                            if issue['evidence']:
                                st.caption(f"  📝 {issue['evidence']}")
                            if issue['url']:
                                st.caption(f"  🔗 {issue['url']}")
                        if len(type_issues) > 10:
                            st.caption(f"... and {len(type_issues) - 10} more items")

                    st.markdown("")  # Spacing
    else:
        st.success("✅ No major issues detected! Your content shows strong trust signals across all dimensions.")

    st.divider()

    # 5D Trust Dimensions Analysis
    st.markdown("### 🔍 5D Trust Dimensions Breakdown")

    dimension_breakdown = report.get('dimension_breakdown', {})

    col1, col2 = st.columns([2, 1])

    with col1:
        # Radar Chart
        dimensions = ['Provenance', 'Verification', 'Transparency', 'Coherence', 'Resonance']
        dimension_keys = ['provenance', 'verification', 'transparency', 'coherence', 'resonance']

        scores = [dimension_breakdown.get(key, {}).get('average', 0) for key in dimension_keys]

        fig_radar = go.Figure()
        fig_radar.add_trace(go.Scatterpolar(
            r=scores,
            theta=dimensions,
            fill='toself',
            name='Current Scores',
            line_color='#3498db'
        ))

        fig_radar.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, 1]
                )
            ),
            showlegend=False,
            height=400
        )

        st.plotly_chart(fig_radar, use_container_width=True, config={'displayModeBar': False})

    with col2:
        st.markdown("#### Dimension Scores")

        for dim_name, dim_key in zip(dimensions, dimension_keys):
            dim_data = dimension_breakdown.get(dim_key, {})
            avg_score = dim_data.get('average', 0)

            # Status indicator
            if avg_score >= 0.8:
                status = "🟢"
            elif avg_score >= 0.6:
                status = "🟡"
            elif avg_score >= 0.4:
                status = "🟠"
            else:
                status = "🔴"

            st.markdown(f"**{status} {dim_name}**")
            st.progress(avg_score)
            st.caption(f"Score: {avg_score*100:.1f}/100 | Range: {dim_data.get('min', 0)*100:.1f} - {dim_data.get('max', 0)*100:.1f}")

    st.divider()

    # Content Items Detail
    st.markdown("### 📝 Content Items Detail")

    appendix = report.get('appendix', [])

    if items:
        # Create DataFrame for display
        items_data = []
        for item in items:
            meta = item.get('meta', {})
            score = item.get('final_score', 0)

            # Determine rating band
            if score >= 80:
                rating_band = '🟢 Excellent'
            elif score >= 60:
                rating_band = '🟡 Good'
            elif score >= 40:
                rating_band = '🟠 Fair'
            else:
                rating_band = '🔴 Poor'

            items_data.append({
                'Source': item.get('source', '').upper(),
                'Title': meta.get('title', meta.get('name', ''))[:50] + '...' if meta.get('title') or meta.get('name') else 'N/A',
                'Score': f"{score:.1f}",
                'Rating': rating_band,
                'URL': meta.get('source_url', meta.get('url', 'N/A'))
            })

        df = pd.DataFrame(items_data)

        # Color-code by rating band
        def color_rating(val):
            if '🟢' in val:
                return 'background-color: #d4edda; color: #155724'
            elif '🟡' in val:
                return 'background-color: #d1ecf1; color: #0c5460'
            elif '🟠' in val:
                return 'background-color: #fff3cd; color: #856404'
            elif '🔴' in val:
                return 'background-color: #f8d7da; color: #721c24'
            return ''

        styled_df = df.style.applymap(color_rating, subset=['Rating'])
        st.dataframe(styled_df, use_container_width=True, height=400)

        # Detailed view expander
        with st.expander("🔎 View Detailed Breakdown"):
            for idx, item_detail in enumerate(appendix[:20]):  # Limit to first 20 for performance
                meta = item_detail.get('meta', {})
                st.markdown(f"**Item {idx + 1}: {meta.get('title', 'Untitled')}**")

                col_a, col_b = st.columns([1, 2])

                with col_a:
                    item_score = item_detail.get('final_score', 0)
                    if item_score >= 80:
                        rating_band = '🟢 Excellent'
                    elif item_score >= 60:
                        rating_band = '🟡 Good'
                    elif item_score >= 40:
                        rating_band = '🟠 Fair'
                    else:
                        rating_band = '🔴 Poor'

                    st.write(f"**Source:** {item_detail.get('source', 'N/A')}")
                    st.write(f"**Rating Score:** {item_score:.1f}/100")
                    st.write(f"**Rating Band:** {rating_band}")

                with col_b:
                    st.write("**Dimension Scores:**")
                    dims = item_detail.get('dimension_scores', {})
                    dim_cols = st.columns(3)
                    for idx2, (dim_name, score) in enumerate(dims.items()):
                        if score is not None:
                            with dim_cols[idx2 % 3]:
                                st.metric(dim_name.title(), f"{score*100:.1f}/100")

                st.divider()

    st.divider()

    # Legacy AR Metrics (optional)
    with st.expander("📊 Legacy Metrics (Authenticity Ratio)"):
        st.caption("These metrics are provided for backward compatibility. The primary focus is Trust Stack Ratings.")

        ar_data = report.get('authenticity_ratio', {})

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric(
                label="Core AR",
                value=f"{ar_data.get('authenticity_ratio_pct', 0):.1f}%"
            )

        with col2:
            st.metric(
                label="Extended AR",
                value=f"{ar_data.get('extended_ar_pct', 0):.1f}%"
            )

        with col3:
            st.metric(
                label="Authentic Items",
                value=f"{ar_data.get('authentic_items', 0):,}"
            )

        with col4:
            st.metric(
                label="Inauthentic Items",
                value=f"{ar_data.get('inauthentic_items', 0):,}"
            )

        st.caption("**Note:** AR classifies content as Authentic/Suspect/Inauthentic using fixed thresholds. Trust Stack Ratings provide more nuanced 0-100 scores across 6 dimensions.")

    st.divider()

    # Export section
    st.markdown("### 📥 Export Reports")

    col1, col2, col3 = st.columns(3)

    with col1:
        pdf_path = run_data.get('pdf_path')
        if pdf_path and os.path.exists(pdf_path):
            with open(pdf_path, 'rb') as f:
                st.download_button(
                    label="📄 Download PDF Report",
                    data=f,
                    file_name=os.path.basename(pdf_path),
                    mime="application/pdf",
                    use_container_width=True
                )

    with col2:
        md_path = run_data.get('md_path')
        if md_path and os.path.exists(md_path):
            with open(md_path, 'r') as f:
                st.download_button(
                    label="📝 Download Markdown Report",
                    data=f.read(),
                    file_name=os.path.basename(md_path),
                    mime="text/markdown",
                    use_container_width=True
                )

    with col3:
        # Export raw data as JSON
        st.download_button(
            label="💾 Download Raw Data (JSON)",
            data=json.dumps(report, indent=2, default=str),
            file_name=f"trust_stack_data_{run_data.get('brand_id')}_{run_data.get('run_id')}.json",
            mime="application/json",
            use_container_width=True
        )


def show_history_page():
    """Display analysis history with enhanced features"""
    st.markdown('<div class="main-header">📚 Rating History</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">View and manage past analysis runs</div>', unsafe_allow_html=True)

    st.divider()

    # Find all past runs
    output_dir = os.path.join(PROJECT_ROOT, 'output', 'webapp_runs')

    if not os.path.exists(output_dir):
        st.info("📭 No analysis history found. Run your first analysis to get started!")
        if st.button("🚀 Run Your First Analysis"):
            st.session_state['page'] = 'analyze'
            st.rerun()
        return

    # Scan for run data files
    run_files = file_glob.glob(os.path.join(output_dir, '*', '_run_data.json'))

    if not run_files:
        st.info("📭 No analysis history found. Run your first analysis to get started!")
        if st.button("🚀 Run Your First Analysis"):
            st.session_state['page'] = 'analyze'
            st.rerun()
        return

    # Load and display runs
    runs = []
    for run_file in run_files:
        try:
            with open(run_file, 'r') as f:
                run_data = json.load(f)
                # Add file path for reference
                run_data['_file_path'] = run_file
                runs.append(run_data)
        except Exception as e:
            logger.warning(f"Failed to load run data from {run_file}: {e}")
            continue

    if not runs:
        st.warning("⚠️ Found run files but couldn't load any valid data. The files may be corrupted.")
        return

    # Sort by timestamp (newest first)
    runs.sort(key=lambda x: x.get('timestamp', ''), reverse=True)

    # Summary stats
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("📊 Total Runs", len(runs))
    with col2:
        unique_brands = len(set(r.get('brand_id', 'Unknown') for r in runs))
        st.metric("🏢 Brands Analyzed", unique_brands)
    with col3:
        total_items = sum(r.get('total_items', 0) for r in runs)
        st.metric("📝 Total Items", f"{total_items:,}")
    with col4:
        # Calculate average rating across all runs
        all_ratings = []
        for run in runs:
            report = run.get('scoring_report', {})
            items = report.get('items', [])
            if items:
                avg = sum(item.get('final_score', 0) for item in items) / len(items) * 100
                all_ratings.append(avg)
        if all_ratings:
            overall_avg = sum(all_ratings) / len(all_ratings)
            st.metric("⭐ Avg Rating", f"{overall_avg:.1f}/100")
        else:
            st.metric("⭐ Avg Rating", "N/A")

    st.divider()

    # Filter options
    with st.expander("🔍 Filter Options", expanded=False):
        filter_col1, filter_col2 = st.columns(2)
        with filter_col1:
            brands = sorted(set(r.get('brand_id', 'Unknown') for r in runs))
            selected_brand = st.selectbox("Filter by Brand", ["All"] + brands)
        with filter_col2:
            sources_all = sorted(set(src for r in runs for src in r.get('sources', [])))
            selected_source = st.selectbox("Filter by Source", ["All"] + sources_all)

    # Apply filters
    filtered_runs = runs
    if selected_brand != "All":
        filtered_runs = [r for r in filtered_runs if r.get('brand_id') == selected_brand]
    if selected_source != "All":
        filtered_runs = [r for r in filtered_runs if selected_source in r.get('sources', [])]

    st.write(f"**Showing {len(filtered_runs)} of {len(runs)} runs**")

    # Display runs in a more visual way
    for idx, run in enumerate(filtered_runs):
        report = run.get('scoring_report', {})
        items = report.get('items', [])
        dimension_breakdown = report.get('dimension_breakdown', {})

        # Calculate average rating for this run
        if items:
            avg_rating = sum(item.get('final_score', 0) for item in items) / len(items) * 100
        else:
            avg_rating = 0

        # Determine rating badge
        if avg_rating >= 80:
            rating_badge = "🟢 Excellent"
            badge_color = "#28a745"
        elif avg_rating >= 60:
            rating_badge = "🟡 Good"
            badge_color = "#ffc107"
        elif avg_rating >= 40:
            rating_badge = "🟠 Fair"
            badge_color = "#fd7e14"
        else:
            rating_badge = "🔴 Poor"
            badge_color = "#dc3545"

        # Format timestamp
        try:
            timestamp = datetime.fromisoformat(run.get('timestamp', '')).strftime('%B %d, %Y at %I:%M %p')
        except:
            timestamp = run.get('timestamp', 'Unknown')

        # Create card-style display
        with st.container():
            # Header row
            header_col1, header_col2, header_col3 = st.columns([3, 2, 1])

            with header_col1:
                st.markdown(f"### 🏢 {run.get('brand_id', 'Unknown Brand')}")
                st.caption(f"📅 {timestamp}")

            with header_col2:
                st.markdown(f"<h3 style='color: {badge_color}; text-align: center;'>{rating_badge}</h3>", unsafe_allow_html=True)
                st.markdown(f"<p style='text-align: center; font-size: 24px; margin: 0;'><b>{avg_rating:.1f}/100</b></p>", unsafe_allow_html=True)

            with header_col3:
                st.write("")  # Spacing
                if st.button("📊 View", key=f"view_{idx}", use_container_width=True):
                    st.session_state['last_run'] = run
                    st.session_state['page'] = 'results'
                    st.rerun()

            # Details row
            detail_col1, detail_col2, detail_col3, detail_col4 = st.columns(4)

            with detail_col1:
                st.metric("📝 Items", run.get('total_items', 0))

            with detail_col2:
                keywords = run.get('keywords', [])
                st.write("**🔍 Keywords:**")
                st.caption(', '.join(keywords[:3]) + ('...' if len(keywords) > 3 else ''))

            with detail_col3:
                sources = run.get('sources', [])
                st.write("**📊 Sources:**")
                st.caption(', '.join(sources))

            with detail_col4:
                # Show top dimension
                if dimension_breakdown:
                    dim_avgs = {k: v.get('average', 0) * 100 for k, v in dimension_breakdown.items()}
                    if dim_avgs:
                        top_dim = max(dim_avgs, key=dim_avgs.get)
                        st.write("**⭐ Top Dimension:**")
                        st.caption(f"{top_dim.title()} ({dim_avgs[top_dim]:.0f})")

            # Download reports section
            download_col1, download_col2, download_col3 = st.columns([2, 1, 1])

            with download_col1:
                # Show models used
                llm_model = report.get('llm_model', 'Unknown')
                rec_model = report.get('recommendations_model', 'Unknown')
                st.caption(f"🤖 Models: {llm_model} / {rec_model}")

            with download_col2:
                # PDF download
                pdf_path = run.get('pdf_path')
                if pdf_path and os.path.exists(pdf_path):
                    with open(pdf_path, 'rb') as f:
                        st.download_button(
                            label="📄 PDF",
                            data=f.read(),
                            file_name=os.path.basename(pdf_path),
                            mime="application/pdf",
                            key=f"pdf_{idx}",
                            use_container_width=True
                        )

            with download_col3:
                # Markdown download
                md_path = run.get('md_path')
                if md_path and os.path.exists(md_path):
                    with open(md_path, 'r') as f:
                        st.download_button(
                            label="📋 MD",
                            data=f.read(),
                            file_name=os.path.basename(md_path),
                            mime="text/markdown",
                            key=f"md_{idx}",
                            use_container_width=True
                        )

            st.divider()


def main():
    """Main application entry point"""

    # Initialize session state
    if 'page' not in st.session_state:
        st.session_state['page'] = 'home'

    # Sidebar navigation
    with st.sidebar:
        st.markdown("### Navigation")

        if st.button("🏠 Home", use_container_width=True):
            st.session_state['page'] = 'home'
            st.rerun()

        if st.button("🚀 Run Analysis", use_container_width=True):
            st.session_state['page'] = 'analyze'
            st.rerun()

        if st.button("📊 View Results", use_container_width=True):
            st.session_state['page'] = 'results'
            st.rerun()

        if st.button("📚 History", use_container_width=True):
            st.session_state['page'] = 'history'
            st.rerun()

        st.divider()

        # API Status
        st.markdown("### API Status")
        cfg = APIConfig()

        st.markdown("**Search Providers:**")
        st.write("🌐 Brave:", "✅" if cfg.brave_api_key else "❌")
        st.write("🔍 Serper:", "✅" if cfg.serper_api_key else "❌")

        st.markdown("**Other APIs:**")
        st.write("🔴 Reddit:", "✅" if (cfg.reddit_client_id and cfg.reddit_client_secret) else "❌")
        st.write("📹 YouTube:", "✅" if cfg.youtube_api_key else "❌")

        st.divider()
        st.caption("Trust Stack Rating v2.0")
        st.caption("6D Trust Framework")

    # Route to appropriate page
    page = st.session_state.get('page', 'home')

    if page == 'home':
        show_home_page()
    elif page == 'analyze':
        show_analyze_page()
    elif page == 'results':
        show_results_page()
    elif page == 'history':
        show_history_page()


if __name__ == '__main__':
    main()
