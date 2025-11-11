"""Domain classification module for URL categorization

Classifies URLs as brand-owned or 3rd party based on domain matching and heuristics.
Supports the 60/40 ratio methodology for holistic trust assessment.
"""

from __future__ import annotations
import logging
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class URLSourceType(Enum):
    """URL source classification"""
    BRAND_OWNED = "brand_owned"
    THIRD_PARTY = "third_party"
    UNKNOWN = "unknown"


class BrandPropertyTier(Enum):
    """Brand-owned property classification tiers"""
    PRIMARY_WEBSITE = "primary_website"  # Main domain, homepage
    CONTENT_HUB = "content_hub"  # Blog, press room, docs
    DIRECT_TO_CONSUMER = "direct_to_consumer"  # E-commerce, portal, email landing
    BRAND_SOCIAL = "brand_social"  # Official verified social accounts


class ThirdPartyTier(Enum):
    """3rd party source classification tiers"""
    NEWS_MEDIA = "news_media"  # News outlets, press
    USER_GENERATED = "user_generated"  # Reviews, social UGC
    EXPERT_PROFESSIONAL = "expert_professional"  # Analyst reports, expert blogs
    MARKETPLACE = "marketplace"  # Amazon, app stores, distribution


@dataclass
class URLClassification:
    """Classification result for a URL"""
    url: str
    source_type: URLSourceType
    tier: Optional[BrandPropertyTier | ThirdPartyTier] = None
    confidence: float = 1.0  # 0.0-1.0
    domain: str = ""
    subdomain: str = ""
    reason: str = ""


@dataclass
class URLCollectionConfig:
    """Configuration for URL collection with ratio enforcement"""
    # Target ratio (0.0-1.0)
    brand_owned_ratio: float = 0.6
    third_party_ratio: float = 0.4

    # Brand identification
    brand_domains: List[str] = None  # e.g., ['nike.com', 'nike.co.uk']
    brand_subdomains: List[str] = None  # e.g., ['blog.nike.com', 'help.nike.com']
    brand_social_handles: List[str] = None  # e.g., ['@nike', 'nike', '/nike']

    # Tier distribution (optional, for fine-grained control)
    # If specified, ensures certain % within each tier
    brand_tier_ratios: Optional[Dict[BrandPropertyTier, float]] = None
    third_party_tier_ratios: Optional[Dict[ThirdPartyTier, float]] = None

    def __post_init__(self):
        if self.brand_domains is None:
            self.brand_domains = []
        if self.brand_subdomains is None:
            self.brand_subdomains = []
        if self.brand_social_handles is None:
            self.brand_social_handles = []

        # Validate ratios sum to 1.0
        total = self.brand_owned_ratio + self.third_party_ratio
        if not (0.99 <= total <= 1.01):  # Allow small floating point error
            raise ValueError(f"Ratios must sum to 1.0, got {total}")


# Common 3rd party domain classifications
KNOWN_NEWS_DOMAINS = {
    'nytimes.com', 'wsj.com', 'washingtonpost.com', 'bbc.com', 'cnn.com',
    'reuters.com', 'bloomberg.com', 'forbes.com', 'techcrunch.com',
    'theverge.com', 'wired.com', 'arstechnica.com', 'engadget.com'
}

KNOWN_REVIEW_DOMAINS = {
    'trustpilot.com', 'g2.com', 'capterra.com', 'yelp.com', 'glassdoor.com',
    'sitejabber.com', 'consumeraffairs.com', 'bbb.org'
}

KNOWN_SOCIAL_DOMAINS = {
    'twitter.com', 'x.com', 'facebook.com', 'instagram.com', 'linkedin.com',
    'youtube.com', 'tiktok.com', 'reddit.com', 'pinterest.com', 'snapchat.com'
}

KNOWN_MARKETPLACE_DOMAINS = {
    'amazon.com', 'amazon.co.uk', 'amazon.de', 'amazon.fr', 'amazon.ca',
    'ebay.com', 'walmart.com', 'target.com', 'bestbuy.com',
    'etsy.com', 'shopify.com'
}

KNOWN_EXPERT_DOMAINS = {
    'gartner.com', 'forrester.com', 'idc.com', 'mckinsey.com',
    'stackoverflow.com', 'medium.com', 'substack.com'
}


def extract_domain_parts(url: str) -> Tuple[str, str, str]:
    """Extract domain, subdomain, and path from URL

    Returns:
        (domain, subdomain, path)
        e.g., ('nike.com', 'blog', '/article/123')
    """
    try:
        parsed = urlparse(url)
        netloc = parsed.netloc.lower()
        path = parsed.path

        # Split into parts
        parts = netloc.split('.')

        # Handle common cases
        if len(parts) >= 2:
            # Get the last 2 parts as the main domain
            domain = '.'.join(parts[-2:])
            # Everything before is subdomain
            subdomain = '.'.join(parts[:-2]) if len(parts) > 2 else ''
        else:
            domain = netloc
            subdomain = ''

        return domain, subdomain, path
    except Exception as e:
        logger.warning('Failed to parse URL %s: %s', url, e)
        return '', '', ''


def classify_url(url: str, config: URLCollectionConfig) -> URLClassification:
    """Classify a URL as brand-owned or 3rd party

    Args:
        url: URL to classify
        config: Collection configuration with brand domains

    Returns:
        URLClassification with source type and tier
    """
    domain, subdomain, path = extract_domain_parts(url)
    full_domain = f"{subdomain}.{domain}" if subdomain else domain

    # Check brand-owned domains
    if domain in config.brand_domains or full_domain in config.brand_subdomains:
        return _classify_brand_owned(url, domain, subdomain, path, config)

    # Check if it's a social media URL with brand handle
    if domain in KNOWN_SOCIAL_DOMAINS:
        return _classify_social_url(url, domain, path, config)

    # Otherwise, classify as 3rd party
    return _classify_third_party(url, domain, subdomain)


def _classify_brand_owned(
    url: str,
    domain: str,
    subdomain: str,
    path: str,
    config: URLCollectionConfig
) -> URLClassification:
    """Classify a brand-owned URL into appropriate tier"""

    # Primary website indicators
    if not subdomain or subdomain == 'www':
        if not path or path == '/' or path.startswith('/about') or path.startswith('/products'):
            return URLClassification(
                url=url,
                source_type=URLSourceType.BRAND_OWNED,
                tier=BrandPropertyTier.PRIMARY_WEBSITE,
                domain=domain,
                subdomain=subdomain,
                reason='Primary domain homepage or product pages'
            )

    # Content hub indicators
    content_hub_subdomains = {'blog', 'news', 'press', 'docs', 'help', 'support', 'learn', 'resources'}
    content_hub_paths = {'/blog', '/news', '/press', '/docs', '/help', '/support', '/resources'}

    if subdomain in content_hub_subdomains or any(path.startswith(p) for p in content_hub_paths):
        return URLClassification(
            url=url,
            source_type=URLSourceType.BRAND_OWNED,
            tier=BrandPropertyTier.CONTENT_HUB,
            domain=domain,
            subdomain=subdomain,
            reason=f'Content hub: {subdomain or path.split("/")[1]}'
        )

    # Direct-to-consumer indicators
    dtc_subdomains = {'shop', 'store', 'cart', 'checkout', 'account', 'my', 'portal'}
    dtc_paths = {'/shop', '/store', '/cart', '/checkout', '/account', '/order'}

    if subdomain in dtc_subdomains or any(path.startswith(p) for p in dtc_paths):
        return URLClassification(
            url=url,
            source_type=URLSourceType.BRAND_OWNED,
            tier=BrandPropertyTier.DIRECT_TO_CONSUMER,
            domain=domain,
            subdomain=subdomain,
            reason=f'D2C channel: {subdomain or path.split("/")[1]}'
        )

    # Default to primary website if on brand domain
    return URLClassification(
        url=url,
        source_type=URLSourceType.BRAND_OWNED,
        tier=BrandPropertyTier.PRIMARY_WEBSITE,
        domain=domain,
        subdomain=subdomain,
        reason='Brand domain (default classification)'
    )


def _classify_social_url(
    url: str,
    domain: str,
    path: str,
    config: URLCollectionConfig
) -> URLClassification:
    """Classify social media URL - check if it's brand's official account"""

    # Extract handle/username from path
    # Common patterns: /username, /@username, /c/username, /user/username
    path_parts = [p for p in path.split('/') if p]

    if path_parts:
        handle = path_parts[0].lstrip('@')

        # Check if it's a brand handle
        if any(
            brand_handle.lower().lstrip('@') == handle.lower()
            for brand_handle in config.brand_social_handles
        ):
            return URLClassification(
                url=url,
                source_type=URLSourceType.BRAND_OWNED,
                tier=BrandPropertyTier.BRAND_SOCIAL,
                domain=domain,
                subdomain='',
                reason=f'Brand official social account: @{handle}'
            )

    # Not a brand account - classify as 3rd party UGC
    return URLClassification(
        url=url,
        source_type=URLSourceType.THIRD_PARTY,
        tier=ThirdPartyTier.USER_GENERATED,
        domain=domain,
        subdomain='',
        reason='Social media user content'
    )


def _classify_third_party(url: str, domain: str, subdomain: str) -> URLClassification:
    """Classify 3rd party URL into appropriate tier"""

    # News/media
    if domain in KNOWN_NEWS_DOMAINS:
        return URLClassification(
            url=url,
            source_type=URLSourceType.THIRD_PARTY,
            tier=ThirdPartyTier.NEWS_MEDIA,
            domain=domain,
            subdomain=subdomain,
            reason=f'Known news outlet: {domain}'
        )

    # Reviews
    if domain in KNOWN_REVIEW_DOMAINS:
        return URLClassification(
            url=url,
            source_type=URLSourceType.THIRD_PARTY,
            tier=ThirdPartyTier.USER_GENERATED,
            domain=domain,
            subdomain=subdomain,
            reason=f'Review platform: {domain}'
        )

    # Marketplace
    if domain in KNOWN_MARKETPLACE_DOMAINS:
        return URLClassification(
            url=url,
            source_type=URLSourceType.THIRD_PARTY,
            tier=ThirdPartyTier.MARKETPLACE,
            domain=domain,
            subdomain=subdomain,
            reason=f'Marketplace: {domain}'
        )

    # Expert/professional
    if domain in KNOWN_EXPERT_DOMAINS:
        return URLClassification(
            url=url,
            source_type=URLSourceType.THIRD_PARTY,
            tier=ThirdPartyTier.EXPERT_PROFESSIONAL,
            domain=domain,
            subdomain=subdomain,
            reason=f'Expert source: {domain}'
        )

    # Social (UGC)
    if domain in KNOWN_SOCIAL_DOMAINS:
        return URLClassification(
            url=url,
            source_type=URLSourceType.THIRD_PARTY,
            tier=ThirdPartyTier.USER_GENERATED,
            domain=domain,
            subdomain=subdomain,
            reason=f'Social UGC: {domain}'
        )

    # Default: classify based on domain patterns
    # .edu, .gov, .org often indicate expert/professional
    if domain.endswith('.edu') or domain.endswith('.gov') or domain.endswith('.org'):
        return URLClassification(
            url=url,
            source_type=URLSourceType.THIRD_PARTY,
            tier=ThirdPartyTier.EXPERT_PROFESSIONAL,
            domain=domain,
            subdomain=subdomain,
            reason=f'Authoritative TLD: {domain}'
        )

    # Default to user-generated content
    return URLClassification(
        url=url,
        source_type=URLSourceType.THIRD_PARTY,
        tier=ThirdPartyTier.USER_GENERATED,
        domain=domain,
        subdomain=subdomain,
        reason='General 3rd party content'
    )


def enforce_ratio(
    all_urls: List[str],
    config: URLCollectionConfig,
    target_count: int
) -> Tuple[List[str], Dict[str, int]]:
    """Enforce ratio by selecting URLs from pools

    Args:
        all_urls: All available URLs
        config: Collection configuration with ratios
        target_count: Target total number of URLs

    Returns:
        (selected_urls, stats) where stats contains distribution info
    """
    # Classify all URLs
    classifications = [classify_url(url, config) for url in all_urls]

    # Separate into pools
    brand_owned = [c for c in classifications if c.source_type == URLSourceType.BRAND_OWNED]
    third_party = [c for c in classifications if c.source_type == URLSourceType.THIRD_PARTY]

    # Calculate target counts
    target_brand = int(target_count * config.brand_owned_ratio)
    target_third_party = int(target_count * config.third_party_ratio)

    # Handle rounding by ensuring we hit exact target_count
    if target_brand + target_third_party < target_count:
        # Add remainder to larger pool
        if config.brand_owned_ratio >= config.third_party_ratio:
            target_brand += (target_count - target_brand - target_third_party)
        else:
            target_third_party += (target_count - target_brand - target_third_party)

    # Select from each pool
    selected_brand = brand_owned[:target_brand]
    selected_third_party = third_party[:target_third_party]

    # Combine and extract URLs
    selected_urls = [c.url for c in selected_brand + selected_third_party]

    # Generate stats
    stats = {
        'total': len(selected_urls),
        'brand_owned': len(selected_brand),
        'third_party': len(selected_third_party),
        'brand_owned_pct': len(selected_brand) / len(selected_urls) * 100 if selected_urls else 0,
        'third_party_pct': len(selected_third_party) / len(selected_urls) * 100 if selected_urls else 0,
        'brand_owned_available': len(brand_owned),
        'third_party_available': len(third_party),
    }

    logger.info(
        'URL ratio enforcement: selected %d brand-owned (%.1f%%) + %d 3rd party (%.1f%%) = %d total',
        stats['brand_owned'], stats['brand_owned_pct'],
        stats['third_party'], stats['third_party_pct'],
        stats['total']
    )

    return selected_urls, stats
