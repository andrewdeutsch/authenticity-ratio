"""Serper API search module

Provides a wrapper to query Serper's Google Search API and return structured results.
Serper offers a cost-effective alternative to direct Google Search API with generous rate limits.

API Documentation: https://serper.dev/
Pricing: ~$0.30 per 1,000 searches (free tier: 2,500 searches)
"""
from __future__ import annotations

import logging
import requests
import os
import time
import threading
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

# Rate limiting: minimum interval (seconds) between Serper API requests
_SERPER_REQUEST_INTERVAL = float(os.getenv('SERPER_REQUEST_INTERVAL', '1.0'))
_LAST_SERPER_REQUEST_TS = 0.0
_SERPER_RATE_LOCK = threading.Lock()


def _wait_for_rate_limit():
    """Ensure at least _SERPER_REQUEST_INTERVAL seconds between requests."""
    global _LAST_SERPER_REQUEST_TS
    if _SERPER_REQUEST_INTERVAL <= 0:
        return
    with _SERPER_RATE_LOCK:
        now = time.monotonic()
        elapsed = now - _LAST_SERPER_REQUEST_TS
        if elapsed < _SERPER_REQUEST_INTERVAL:
            to_sleep = _SERPER_REQUEST_INTERVAL - elapsed
            time.sleep(to_sleep)
        _LAST_SERPER_REQUEST_TS = time.monotonic()


def search_serper(query: str, size: int = 10) -> List[Dict[str, str]]:
    """Search using Serper API and return a list of result dicts {title, url, snippet}

    Args:
        query: Search query string
        size: Number of results to retrieve (max 100 per request)

    Returns:
        List of dicts with keys: title, url, snippet

    Raises:
        ValueError: If SERPER_API_KEY is not configured
        requests.exceptions.RequestException: If API request fails
    """
    api_key = os.getenv('SERPER_API_KEY')
    if not api_key:
        raise ValueError(
            "SERPER_API_KEY not found in environment. "
            "Get your key at https://serper.dev/ and add it to .env"
        )

    # Serper API endpoint
    endpoint = "https://google.serper.dev/search"

    # Serper's actual per-page limit is 10 results (despite documentation suggesting 100)
    # To get more results, we need to paginate through multiple pages
    results_per_page = 10
    max_per_request = min(int(os.getenv('SERPER_MAX_PER_REQUEST', '100')), 100)

    all_results = []
    page = 1
    max_pages = (size + results_per_page - 1) // results_per_page  # Calculate pages needed
    max_pages = min(max_pages, 10)  # Safety limit for pagination

    while len(all_results) < size and page <= max_pages:
        # Calculate how many results we still need
        remaining = size - len(all_results)
        # Request 10 results per page (Serper's page size)
        batch_size = min(remaining, results_per_page)

        # Prepare request payload
        payload = {
            "q": query,
            "num": results_per_page,  # Always request 10 per page
        }

        # Add pagination if not the first page
        if page > 1:
            # Serper uses page number for pagination
            payload["page"] = page

        headers = {
            "X-API-KEY": api_key,
            "Content-Type": "application/json"
        }

        logger.info(
            'Serper API request: query=%s, batch_size=%s, page=%s (collected: %s/%s)',
            query, batch_size, page, len(all_results), size
        )

        try:
            # Apply rate limiting
            _wait_for_rate_limit()

            # Make API request
            timeout = int(os.getenv('SERPER_API_TIMEOUT', '30'))
            response = requests.post(
                endpoint,
                json=payload,
                headers=headers,
                timeout=timeout
            )

            if response.status_code == 200:
                data = response.json()

                # Serper returns results in 'organic' field
                organic_results = data.get('organic', [])

                if not organic_results:
                    logger.warning('Serper API returned no organic results for query: %s', query)
                    break

                # Extract results in the expected format
                for item in organic_results:
                    title = item.get('title', '')
                    url = item.get('link', '')
                    snippet = item.get('snippet', '')

                    if url and url.startswith('http'):
                        all_results.append({
                            'title': title,
                            'url': url,
                            'snippet': snippet
                        })

                logger.info('Serper API batch returned %s results', len(organic_results))

                # Stop if we have enough results
                if len(all_results) >= size:
                    logger.info('Collected enough results: %s/%s', len(all_results), size)
                    break

                # Only stop if we got zero results (no more results available)
                if len(organic_results) == 0:
                    logger.info('Serper API returned zero results - no more results available')
                    break

            elif response.status_code == 401:
                logger.error('Serper API authentication failed - check your SERPER_API_KEY')
                raise ValueError('Invalid Serper API key')

            elif response.status_code == 429:
                logger.error('Serper API rate limit exceeded')
                raise requests.exceptions.RequestException('Serper API rate limit exceeded')

            else:
                logger.error('Serper API request failed: HTTP %s. Response: %s',
                           response.status_code, response.text[:500])
                break

        except requests.exceptions.Timeout:
            logger.error('Serper API request timed out for query: %s', query)
            break

        except requests.exceptions.RequestException as e:
            logger.error('Serper API request failed: %s', str(e))
            raise

        except Exception as e:
            logger.error('Unexpected error during Serper API request: %s', str(e))
            break

        page += 1

    logger.info('Serper search completed: collected %s results for query: %s', len(all_results), query)
    return all_results[:size]  # Ensure we don't return more than requested


def collect_serper_pages(
    query: str,
    target_count: int = 10,
    pool_size: int | None = None,
    min_body_length: int = 200,
    url_collection_config: 'URLCollectionConfig' | None = None
) -> List[Dict[str, str]]:
    """Collect up to `target_count` successfully fetched pages from Serper search.

    Behavior:
    - Request `pool_size` search results (defaults to max(30, target_count*3)).
    - If url_collection_config is provided, enforces brand-owned vs 3rd party ratio
    - Iterate results in order and fetch page content
    - Only count pages whose `body` length >= `min_body_length` as successful
    - Stop once `target_count` successful pages are collected or the pool is exhausted

    Args:
        query: Search query
        target_count: Target number of pages to collect
        pool_size: Number of search results to request
        min_body_length: Minimum body length for a page to be considered valid
        url_collection_config: Optional ratio enforcement configuration

    Returns:
        List of dicts with page content {title, body, url, ...}
    """
    # Import fetch_page from brave_search module
    from ingestion.brave_search import fetch_page

    if pool_size is None:
        pool_size = max(30, target_count * 3)

    # Import classifier here to avoid circular imports
    if url_collection_config:
        from ingestion.domain_classifier import classify_url, URLSourceType

    try:
        search_results = search_serper(query, size=pool_size)
    except Exception as e:
        logger.warning('Serper search failed while collecting pages: %s', e)
        search_results = []

    if not search_results:
        return []

    # Ratio enforcement: track separate pools if config provided
    if url_collection_config:
        target_brand_owned = int(target_count * url_collection_config.brand_owned_ratio)
        target_third_party = int(target_count * url_collection_config.third_party_ratio)

        # Handle rounding to ensure we hit exact target_count
        if target_brand_owned + target_third_party < target_count:
            if url_collection_config.brand_owned_ratio >= url_collection_config.third_party_ratio:
                target_brand_owned += (target_count - target_brand_owned - target_third_party)
            else:
                target_third_party += (target_count - target_brand_owned - target_third_party)

        brand_owned_collected: List[Dict[str, str]] = []
        third_party_collected: List[Dict[str, str]] = []

        logger.info('Collecting with ratio enforcement: %d brand-owned (%.0f%%) + %d 3rd party (%.0f%%)',
                   target_brand_owned, url_collection_config.brand_owned_ratio * 100,
                   target_third_party, url_collection_config.third_party_ratio * 100)

        for item in search_results:
            # Stop if both pools are full
            if len(brand_owned_collected) >= target_brand_owned and len(third_party_collected) >= target_third_party:
                break

            url = item.get('url')
            if not url:
                continue

            # Classify the URL
            classification = classify_url(url, url_collection_config)
            is_brand_owned = classification.source_type == URLSourceType.BRAND_OWNED

            # Attempt to fetch and only count if body meets minimum length
            content = fetch_page(url)
            body = content.get('body') or ''
            if body and len(body) >= min_body_length:
                # Check if pool is full AFTER validating content
                # This ensures we keep searching for valid URLs even if one pool fills up
                if is_brand_owned and len(brand_owned_collected) >= target_brand_owned:
                    logger.debug('Skipping brand-owned URL %s - pool full', url)
                    continue
                if not is_brand_owned and len(third_party_collected) >= target_third_party:
                    logger.debug('Skipping 3rd party URL %s - pool full', url)
                    continue

                # Add source type metadata
                content['source_type'] = classification.source_type.value
                content['source_tier'] = classification.tier.value if classification.tier else 'unknown'

                if is_brand_owned:
                    brand_owned_collected.append(content)
                    logger.debug('Collected brand-owned page (%d/%d): %s',
                               len(brand_owned_collected), target_brand_owned, url)
                else:
                    third_party_collected.append(content)
                    logger.debug('Collected 3rd party page (%d/%d): %s',
                               len(third_party_collected), target_third_party, url)
            else:
                logger.debug('Skipping %s because content is thin or empty (len=%s)', url, len(body))

        # Combine results
        collected = brand_owned_collected + third_party_collected

        logger.info('Collected %d brand-owned + %d 3rd party = %d total pages (target: %d) for query=%s',
                   len(brand_owned_collected), len(third_party_collected), len(collected), target_count, query)

    else:
        # Original behavior: no ratio enforcement
        collected: List[Dict[str, str]] = []
        for item in search_results:
            if len(collected) >= target_count:
                break
            url = item.get('url')
            if not url:
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


def get_serper_stats() -> Dict[str, any]:
    """Get current Serper API usage statistics.

    Returns:
        Dict with usage statistics from Serper API

    Note: This requires a valid API key and may not be available on all plans.
    """
    api_key = os.getenv('SERPER_API_KEY')
    if not api_key:
        return {"error": "SERPER_API_KEY not configured"}

    try:
        _wait_for_rate_limit()
        response = requests.get(
            "https://google.serper.dev/account",
            headers={"X-API-KEY": api_key},
            timeout=10
        )

        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"HTTP {response.status_code}"}

    except Exception as e:
        logger.error('Failed to get Serper stats: %s', str(e))
        return {"error": str(e)}
