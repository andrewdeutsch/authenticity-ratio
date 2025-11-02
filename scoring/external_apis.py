"""
External API integration framework for Trust Stack attribute detection

This module provides infrastructure for calling external APIs:
- Domain reputation checking (NewsGuard-style)
- Fact-checking APIs (ClaimBuster, Google Fact Check, etc.)
- Rate limiting and caching
- Error handling and fallbacks

Phase B includes basic framework with simple implementations.
Full API integrations planned for future phases.
"""

import logging
import time
import requests
from typing import Optional, Dict, Any
from functools import lru_cache
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class ExternalAPIClient:
    """
    Base class for external API integrations

    Provides common functionality:
    - Rate limiting
    - Caching
    - Error handling
    """

    def __init__(self, api_key: Optional[str] = None, rate_limit: float = 1.0):
        """
        Initialize API client

        Args:
            api_key: Optional API key for authenticated requests
            rate_limit: Minimum seconds between requests (default: 1.0)
        """
        self.api_key = api_key
        self.rate_limit = rate_limit  # seconds between requests
        self.last_request_time = 0

    def _rate_limit_wait(self):
        """Enforce rate limiting between requests"""
        elapsed = time.time() - self.last_request_time

        if elapsed < self.rate_limit:
            wait_time = self.rate_limit - elapsed
            logger.debug(f"Rate limiting: waiting {wait_time:.2f}s")
            time.sleep(wait_time)

        self.last_request_time = time.time()

    def _make_request(self, url: str, headers: Optional[Dict[str, str]] = None,
                     params: Optional[Dict[str, Any]] = None, timeout: int = 5) -> Optional[Dict[str, Any]]:
        """
        Make rate-limited HTTP request

        Args:
            url: Request URL
            headers: Optional HTTP headers
            params: Optional query parameters
            timeout: Request timeout in seconds

        Returns:
            JSON response or None if request fails
        """
        self._rate_limit_wait()

        try:
            response = requests.get(url, headers=headers, params=params, timeout=timeout)
            response.raise_for_status()
            return response.json()

        except requests.exceptions.Timeout:
            logger.warning(f"Request timeout: {url}")
            return None

        except requests.exceptions.RequestException as e:
            logger.warning(f"Request failed: {url} - {e}")
            return None

        except ValueError as e:
            logger.warning(f"Invalid JSON response: {url} - {e}")
            return None


class DomainReputationClient(ExternalAPIClient):
    """
    Domain reputation checking

    Provides trust scores for domains based on:
    - Known trusted/untrusted domain lists
    - TLD-based heuristics
    - (Future) Integration with NewsGuard, Web of Trust, etc.

    Enhances attributes:
    - source_reputation_score (Provenance)
    """

    def __init__(self, api_key: Optional[str] = None):
        super().__init__(api_key=api_key, rate_limit=1.0)

        # Trusted domain database (simple whitelist for Phase B)
        self.trusted_domains = {
            # Government
            '.gov': 10.0,
            '.mil': 10.0,

            # Education
            '.edu': 9.0,

            # Major news organizations
            'nytimes.com': 9.0,
            'wsj.com': 9.0,
            'washingtonpost.com': 9.0,
            'bbc.com': 9.0,
            'bbc.co.uk': 9.0,
            'reuters.com': 9.0,
            'apnews.com': 9.0,
            'npr.org': 9.0,
            'theguardian.com': 9.0,
            'ft.com': 9.0,

            # Tech news
            'techcrunch.com': 8.0,
            'wired.com': 8.0,
            'arstechnica.com': 8.0,

            # Organizations
            '.org': 7.0,

            # Academic/Research
            'scholar.google.com': 9.0,
            'arxiv.org': 8.0,
            'pubmed.gov': 10.0,
        }

        # Untrusted domain database (simple blacklist)
        self.untrusted_domains = {
            # Free/spam TLDs
            '.tk': 2.0,
            '.ml': 2.0,
            '.ga': 2.0,
            '.cf': 2.0,
            '.gq': 2.0,

            # Known low-quality
            '.info': 4.0,
            '.biz': 4.0,
        }

    @lru_cache(maxsize=1000)
    def get_domain_score(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Get domain trust score

        Args:
            url: Full URL or domain name

        Returns:
            Dictionary with reputation info or None
            {
                'domain': str,
                'score': float (0-10),
                'evidence': str,
                'confidence': float
            }
        """
        try:
            # Extract domain from URL
            if url.startswith('http'):
                parsed = urlparse(url)
                domain = parsed.netloc.lower()
            else:
                domain = url.lower()

            # Remove www. prefix
            if domain.startswith('www.'):
                domain = domain[4:]

            # Check trusted domains
            for trusted_key, score in self.trusted_domains.items():
                if domain.endswith(trusted_key):
                    return {
                        'domain': domain,
                        'score': score,
                        'value': score,  # Same as score for domain reputation
                        'evidence': f"Trusted domain: {domain}",
                        'confidence': 0.9
                    }

            # Check untrusted domains
            for untrusted_key, score in self.untrusted_domains.items():
                if domain.endswith(untrusted_key):
                    return {
                        'domain': domain,
                        'score': score,
                        'value': score,
                        'evidence': f"Untrusted TLD: {untrusted_key}",
                        'confidence': 0.8
                    }

            # Default: neutral score for unknown domains
            return {
                'domain': domain,
                'score': 5.0,
                'value': 5.0,
                'evidence': f"Unknown domain: {domain}",
                'confidence': 0.5
            }

        except Exception as e:
            logger.warning(f"Domain reputation check failed for {url}: {e}")
            return None

    def add_trusted_domain(self, domain: str, score: float):
        """
        Add domain to trusted list

        Args:
            domain: Domain name
            score: Trust score (0-10)
        """
        self.trusted_domains[domain.lower()] = score
        # Clear cache to reflect changes
        self.get_domain_score.cache_clear()

    def add_untrusted_domain(self, domain: str, score: float):
        """
        Add domain to untrusted list

        Args:
            domain: Domain name
            score: Trust score (0-10)
        """
        self.untrusted_domains[domain.lower()] = score
        # Clear cache to reflect changes
        self.get_domain_score.cache_clear()


class FactCheckingClient(ExternalAPIClient):
    """
    Fact-checking API integration

    Provides claim verification from fact-checking databases:
    - (Future) ClaimBuster API
    - (Future) Google Fact Check Tools API
    - (Future) Full Fact API

    Enhances attributes:
    - fact_checked_claim_presence (Verification)
    """

    def __init__(self, api_key: Optional[str] = None):
        super().__init__(api_key=api_key, rate_limit=2.0)
        self.enabled = False  # Disabled until API keys configured

    def check_claim(self, claim: str) -> Optional[Dict[str, Any]]:
        """
        Check if claim has been fact-checked

        Args:
            claim: Claim text to verify

        Returns:
            Dictionary with fact-check results or None
            {
                'rating': str,  # 'true', 'false', 'mixed', 'unverified'
                'confidence': float,
                'source': str,
                'url': str
            }
        """
        if not self.enabled:
            logger.debug("Fact-checking API not enabled (requires API key)")
            return None

        # TODO: Integrate with actual fact-checking APIs
        # Placeholder implementation for Phase B
        return None

    def check_multiple_claims(self, claims: list[str]) -> Dict[str, Any]:
        """
        Check multiple claims

        Args:
            claims: List of claim texts

        Returns:
            Dictionary mapping claims to results
        """
        results = {}

        for claim in claims:
            result = self.check_claim(claim)
            if result:
                results[claim] = result

        return results


class MediaVerificationClient(ExternalAPIClient):
    """
    Media verification (C2PA, EXIF, reverse image search)

    Provides media authenticity checking:
    - (Future) C2PA manifest verification
    - (Future) EXIF metadata analysis
    - (Future) Reverse image search

    Enhances attributes:
    - c2pa_provenance_data_present (Provenance)
    - media_manipulation_check (Verification)
    """

    def __init__(self, api_key: Optional[str] = None):
        super().__init__(api_key=api_key, rate_limit=1.0)
        self.enabled = False  # Disabled until implemented

    def check_c2pa_manifest(self, image_url: str) -> Optional[Dict[str, Any]]:
        """
        Check for C2PA provenance manifest

        Args:
            image_url: URL to image

        Returns:
            Dictionary with C2PA data or None
        """
        # TODO: Implement C2PA verification
        return None

    def analyze_exif(self, image_url: str) -> Optional[Dict[str, Any]]:
        """
        Analyze EXIF metadata

        Args:
            image_url: URL to image

        Returns:
            Dictionary with EXIF data or None
        """
        # TODO: Implement EXIF analysis
        return None


# Singleton instances
_domain_reputation_client = None
_fact_checking_client = None
_media_verification_client = None


def get_domain_reputation_client(api_key: Optional[str] = None) -> DomainReputationClient:
    """Get singleton DomainReputationClient instance"""
    global _domain_reputation_client
    if _domain_reputation_client is None:
        _domain_reputation_client = DomainReputationClient(api_key)
    return _domain_reputation_client


def get_fact_checking_client(api_key: Optional[str] = None) -> FactCheckingClient:
    """Get singleton FactCheckingClient instance"""
    global _fact_checking_client
    if _fact_checking_client is None:
        _fact_checking_client = FactCheckingClient(api_key)
    return _fact_checking_client


def get_media_verification_client(api_key: Optional[str] = None) -> MediaVerificationClient:
    """Get singleton MediaVerificationClient instance"""
    global _media_verification_client
    if _media_verification_client is None:
        _media_verification_client = MediaVerificationClient(api_key)
    return _media_verification_client
