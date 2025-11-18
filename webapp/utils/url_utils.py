"""
URL utility functions for brand content analysis
"""
import re
from urllib.parse import urlparse
from typing import List, Dict, Any, Optional


# Domain suffix constants
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
)

ENGLISH_COUNTRY_SUFFIXES = tuple(s for s in ENGLISH_DOMAIN_SUFFIXES if s != '.com')

# For this task the user requested USA-only sites
USA_DOMAIN_SUFFIXES = ('.com', '.us')

PROMOTIONAL_SUBPATHS = [
    '/about', '/about-us', '/press', '/press-room', '/newsroom', '/stories', '/careers',
    '/investor-relations', '/sustainability', '/insights', '/promotions', '/offers', '/events'
]


def normalize_brand_slug(brand_id: str) -> str:
    """Convert brand ID to a normalized slug (alphanumeric only)."""
    return re.sub(r'[^a-z0-9]', '', brand_id.lower())


def extract_hostname(url: str) -> str:
    """Extract hostname from URL."""
    return (urlparse(url).hostname or '').lower()


def is_english_host(url: str) -> bool:
    """Check if URL uses an English-speaking domain suffix."""
    host = extract_hostname(url)
    return any(host.endswith(suffix) for suffix in ENGLISH_DOMAIN_SUFFIXES)


def is_usa_host(url: str) -> bool:
    """Check if URL uses a USA domain suffix."""
    host = extract_hostname(url)
    return any(host.endswith(suffix) for suffix in USA_DOMAIN_SUFFIXES)


def find_main_american_url(entries: List[Dict[str, Any]], brand_id: str) -> Optional[str]:
    """Find the main American URL from a list of entries."""
    slug = normalize_brand_slug(brand_id)
    for entry in entries:
        host = extract_hostname(entry['url'])
        if host.endswith('.com') and slug and slug in host:
            return entry['url']
        if host.endswith('.com') and host.startswith('www.'):
            return entry['url']
    return None


def has_country_variants(entries: List[Dict[str, Any]], main_url: str) -> bool:
    """Check if entries contain country-specific variants of main URL."""
    main_host = extract_hostname(main_url)
    for entry in entries:
        host = extract_hostname(entry['url'])
        if host != main_host and host.endswith(ENGLISH_COUNTRY_SUFFIXES):
            return True
    return False


def add_primary_subpages(entries: List[Dict[str, Any]], main_url: str) -> List[Dict[str, Any]]:
    """Add primary subpages to the entries list."""
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
    """Check if URL is likely a promotional page."""
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


def _fallback_title(url: str) -> str:
    """Generate a fallback title from URL hostname."""
    parsed = urlparse(url)
    hostname = parsed.hostname or url
    return hostname


def is_core_domain(url: str, brand_domains: List[str] = None) -> bool:
    """
    Check if a URL is a core domain (e.g., mastercard.com, mastercard.co.uk)
    rather than a subdomain (e.g., blog.mastercard.com).

    Args:
        url: The URL to check
        brand_domains: List of brand domains to check against

    Returns:
        True if this is a core domain, False otherwise
    """
    try:
        parsed = urlparse(url)
        netloc = parsed.netloc.lower()

        # Remove www. prefix for comparison
        if netloc.startswith('www.'):
            netloc = netloc[4:]

        # If no brand domains provided, can't determine
        if not brand_domains:
            return False

        # Check if the netloc matches any brand domain exactly
        for domain in brand_domains:
            domain_lower = domain.lower()
            if domain_lower.startswith('www.'):
                domain_lower = domain_lower[4:]

            # Exact match = core domain
            if netloc == domain_lower:
                return True

            # Also consider international variants as core domains
            # e.g., mastercard.co.uk, mastercard.com.au
            # Check if it's domain.TLD or domain.co.TLD format
            parts = netloc.split('.')
            domain_parts = domain_lower.split('.')

            # If netloc has 2-3 parts and starts with the same base domain name
            # Examples: mastercard.com (2 parts), mastercard.co.uk (3 parts)
            if len(parts) in [2, 3] and len(domain_parts) >= 2:
                # Compare the brand name part (e.g., "mastercard")
                if parts[0] == domain_parts[0]:
                    return True

        return False
    except Exception:
        return False


def is_login_page(url: str) -> bool:
    """
    Detect if a URL is a login/signin/authentication page.

    Args:
        url: The URL to check

    Returns:
        True if this appears to be a login page, False otherwise
    """
    try:
        parsed = urlparse(url)
        path = parsed.path.lower()
        query = parsed.query.lower()

        # Common login/auth patterns in URLs
        login_patterns = [
            '/login',
            '/signin',
            '/sign-in',
            '/log-in',
            '/auth',
            '/authenticate',
            '/authentication',
            '/account/login',
            '/user/login',
            '/customer/login',
            '/sso',
            '/oauth',
            '/saml',
            '/session/new',
            '/sessions/new',
            '/portal/login',
            '/access/login',
        ]

        # Check path for login patterns
        for pattern in login_patterns:
            if pattern in path:
                return True

        # Check query parameters for login indicators
        login_query_params = [
            'login',
            'signin',
            'auth',
            'authenticate',
            'redirect_to_login',
            'return_url',
        ]

        for param in login_query_params:
            if param in query:
                return True

        return False
    except Exception:
        return False
