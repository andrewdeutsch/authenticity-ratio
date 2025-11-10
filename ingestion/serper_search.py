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

    # Serper supports up to 100 results per request (vs Brave's 20)
    max_per_request = int(os.getenv('SERPER_MAX_PER_REQUEST', '100'))

    all_results = []
    page = 1
    max_pages = 10  # Safety limit for pagination

    while len(all_results) < size and page <= max_pages:
        # Calculate how many results to request in this batch
        remaining = size - len(all_results)
        batch_size = min(remaining, max_per_request)

        # Prepare request payload
        payload = {
            "q": query,
            "num": batch_size,
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

                # Check if we have more results available
                # Serper includes searchInformation.totalResults but we rely on organic results length
                if len(organic_results) < batch_size:
                    # No more results available
                    logger.info('Serper API returned fewer results than requested - no more results available')
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
