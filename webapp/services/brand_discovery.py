"""
Brand discovery service for identifying brand domains and properties
"""
from typing import Dict, List, Any, Optional


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
