"""
Link verifier for validating LLM-reported broken links
Checks actual HTTP status codes to prevent hallucinations
"""

import re
import logging
from typing import List, Set
import requests
from urllib.parse import urljoin, urlparse

logger = logging.getLogger(__name__)

# Timeout for HTTP requests (seconds)
REQUEST_TIMEOUT = 5


def extract_urls(text: str) -> Set[str]:
    """
    Extract URLs from text content
    
    Args:
        text: Content text to extract URLs from
    
    Returns:
        Set of unique URLs found in text
    """
    # Regex pattern for URLs
    url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
    
    urls = set(re.findall(url_pattern, text))
    return urls


def check_link_status(url: str) -> dict:
    """
    Check HTTP status of a single URL
    
    Args:
        url: URL to check
    
    Returns:
        Dict with 'url', 'status_code', 'is_broken', 'error'
    """
    try:
        response = requests.head(url, timeout=REQUEST_TIMEOUT, allow_redirects=True)
        status_code = response.status_code
        is_broken = status_code >= 400  # 4xx and 5xx are broken
        
        return {
            'url': url,
            'status_code': status_code,
            'is_broken': is_broken,
            'error': None
        }
    except requests.exceptions.Timeout:
        logger.warning(f"Timeout checking URL: {url}")
        return {
            'url': url,
            'status_code': None,
            'is_broken': True,
            'error': 'timeout'
        }
    except requests.exceptions.RequestException as e:
        logger.warning(f"Error checking URL {url}: {e}")
        return {
            'url': url,
            'status_code': None,
            'is_broken': True,
            'error': str(e)
        }


def verify_broken_links(content_text: str, content_url: str = None) -> List[dict]:
    """
    Verify which links in content are actually broken
    
    Args:
        content_text: Text content to check for links
        content_url: Base URL for resolving relative links (optional)
    
    Returns:
        List of broken link dicts with url, status_code, error
    """
    urls = extract_urls(content_text)
    
    if not urls:
        logger.debug("No URLs found in content")
        return []
    
    logger.info(f"Checking {len(urls)} URLs for broken links")
    
    broken_links = []
    for url in urls:
        # Resolve relative URLs if base URL provided
        if content_url and not urlparse(url).netloc:
            url = urljoin(content_url, url)
        
        result = check_link_status(url)
        if result['is_broken']:
            broken_links.append(result)
            logger.info(f"Found broken link: {url} (status={result['status_code']})")
    
    return broken_links
