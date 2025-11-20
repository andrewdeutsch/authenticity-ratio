"""
Content quality filter to detect and skip error pages, login walls, and invalid content
"""

import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)

# Error page indicators
ERROR_TITLES = {
    'access denied',
    'error',
    '404',
    '403',
    '401',
    '500',
    'not found',
    'page not found',
    'forbidden',
    'unauthorized',
    'server error',
    'bad request',
    'service unavailable'
}

# Login/auth page indicators
LOGIN_INDICATORS = {
    'login',
    'sign in',
    'sign up',
    'register',
    'authentication required',
    'please log in'
}

# Minimum content length (chars) for valid content
MIN_CONTENT_LENGTH = 100


def is_error_page(title: str, body: str) -> bool:
    """
    Check if content appears to be an error page
    
    Args:
        title: Page title
        body: Page body text
    
    Returns:
        True if content is an error page
    """
    title_lower = title.lower().strip() if title else ""
    body_lower = body.lower() if body else ""
    
    # Check title against error indicators
    if title_lower in ERROR_TITLES:
        logger.info(f"Detected error page by title: '{title}'")
        return True
    
    # Check if title contains error keywords
    error_keywords = ['error', '404', '403', '401', '500', 'denied', 'forbidden']
    if any(keyword in title_lower for keyword in error_keywords):
        logger.info(f"Detected error page by keyword in title: '{title}'")
        return True
    
    # Check body for error messages (first 500 chars)
    body_sample = body_lower[:500]
    if 'access denied' in body_sample or 'error occurred' in body_sample:
        logger.info(f"Detected error page by body content: '{title}'")
        return True
    
    return False


def is_login_wall(title: str, body: str) -> bool:
    """
    Check if content appears to be a login/authentication page
    
    Args:
        title: Page title
        body: Page body text
    
    Returns:
        True if content is a login wall
    """
    title_lower = title.lower().strip() if title else ""
    body_lower = body.lower() if body else ""
    
    # Check title
    if title_lower in LOGIN_INDICATORS:
        logger.info(f"Detected login wall by title: '{title}'")
        return True
    
    # Check for login form patterns in body (first 1000 chars)
    body_sample = body_lower[:1000]
    login_patterns = [
        'email or mobile number',
        'username and password',
        'sign in to continue',
        'login to access',
        'please log in',
        'authentication required',
        'otp code',
        'captcha'
    ]
    
    # If multiple login patterns found, it's likely a login page
    pattern_count = sum(1 for pattern in login_patterns if pattern in body_sample)
    if pattern_count >= 2:
        logger.info(f"Detected login wall by form patterns: '{title}' ({pattern_count} patterns)")
        return True
    
    return False


def is_insufficient_content(title: str, body: str) -> bool:
    """
    Check if content is too short to be meaningful
    
    Args:
        title: Page title
        body: Page body text
    
    Returns:
        True if content is insufficient
    """
    body_length = len(body) if body else 0
    
    if body_length < MIN_CONTENT_LENGTH:
        logger.info(f"Detected insufficient content: '{title}' ({body_length} chars)")
        return True
    
    return False


def should_skip_content(title: str, body: str, url: str = None) -> Optional[str]:
    """
    Determine if content should be skipped from scoring
    
    Args:
        title: Page title
        body: Page body text
        url: Optional URL for logging
    
    Returns:
        Reason string if content should be skipped, None otherwise
    """
    if is_error_page(title, body):
        return "error_page"
    
    if is_login_wall(title, body):
        return "login_wall"
    
    if is_insufficient_content(title, body):
        return "insufficient_content"
    
    return None
