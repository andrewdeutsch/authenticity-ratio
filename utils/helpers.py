"""
Helper utilities for AR tool
Common functions and utilities
"""

import uuid
import logging
from datetime import datetime
from typing import Dict, Any, List
import json
import hashlib

from config.settings import SETTINGS

logger = logging.getLogger(__name__)

def generate_run_id() -> str:
    """Generate unique run ID for pipeline execution"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = str(uuid.uuid4())[:8]
    return f"run_{timestamp}_{unique_id}"

def validate_config() -> List[str]:
    """Validate configuration settings and return any issues"""
    issues = []
    
    # Import validation function from settings
    from config.settings import validate_config as settings_validate
    issues.extend(settings_validate())
    
    # Additional validations
    if SETTINGS['min_score_threshold'] <= SETTINGS['suspect_threshold']:
        issues.append("Min score threshold must be greater than suspect threshold")
    
    if SETTINGS['max_content_length'] <= 0:
        issues.append("Max content length must be positive")
    
    if SETTINGS['batch_size'] <= 0:
        issues.append("Batch size must be positive")
    
    return issues

def format_timestamp(timestamp: datetime = None) -> str:
    """Format timestamp for Athena compatibility"""
    if timestamp is None:
        timestamp = datetime.now()
    return timestamp.isoformat()

def calculate_content_hash(content: str) -> str:
    """Calculate hash for content deduplication"""
    return hashlib.md5(content.encode('utf-8')).hexdigest()

def truncate_content(content: str, max_length: int = None) -> str:
    """Truncate content to maximum length"""
    if max_length is None:
        max_length = SETTINGS['max_content_length']
    
    if len(content) <= max_length:
        return content
    
    # Truncate and add ellipsis
    return content[:max_length-3] + "..."

def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe file operations"""
    # Remove or replace invalid characters
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    
    # Limit length
    if len(filename) > 200:
        filename = filename[:200]
    
    return filename

def load_json_safely(file_path: str) -> Dict[str, Any]:
    """Safely load JSON file with error handling"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.warning(f"JSON file not found: {file_path}")
        return {}
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in file {file_path}: {e}")
        return {}
    except Exception as e:
        logger.error(f"Error loading JSON file {file_path}: {e}")
        return {}

def save_json_safely(data: Dict[str, Any], file_path: str) -> bool:
    """Safely save data to JSON file with error handling"""
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        logger.error(f"Error saving JSON file {file_path}: {e}")
        return False

def chunk_list(items: List[Any], chunk_size: int = None) -> List[List[Any]]:
    """Split list into chunks of specified size"""
    if chunk_size is None:
        chunk_size = SETTINGS['batch_size']
    
    return [items[i:i + chunk_size] for i in range(0, len(items), chunk_size)]

def retry_on_failure(max_retries: int = 3, delay: float = 1.0):
    """Decorator for retrying functions on failure"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        logger.error(f"Function {func.__name__} failed after {max_retries} attempts: {e}")
                        raise
                    else:
                        logger.warning(f"Function {func.__name__} failed on attempt {attempt + 1}, retrying: {e}")
                        import time
                        time.sleep(delay * (attempt + 1))  # Exponential backoff
            return None
        return wrapper
    return decorator

def format_bytes(bytes_value: int) -> str:
    """Format bytes into human readable format"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_value < 1024.0:
            return f"{bytes_value:.1f} {unit}"
        bytes_value /= 1024.0
    return f"{bytes_value:.1f} PB"

def format_duration(seconds: float) -> str:
    """Format duration in seconds to human readable format"""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}m"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}h"

def get_percentage_change(old_value: float, new_value: float) -> float:
    """Calculate percentage change between two values"""
    if old_value == 0:
        return 0.0 if new_value == 0 else 100.0
    return ((new_value - old_value) / old_value) * 100

def is_valid_email(email: str) -> bool:
    """Simple email validation"""
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def clean_text(text: str) -> str:
    """Clean and normalize text"""
    if not text:
        return ""
    
    # Remove excessive whitespace
    text = ' '.join(text.split())
    
    # Remove common HTML entities
    html_entities = {
        '&amp;': '&',
        '&lt;': '<',
        '&gt;': '>',
        '&quot;': '"',
        '&#39;': "'",
        '&nbsp;': ' '
    }
    
    for entity, replacement in html_entities.items():
        text = text.replace(entity, replacement)
    
    return text.strip()

def extract_domain(url: str) -> str:
    """Extract domain from URL"""
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        return parsed.netloc
    except:
        return ""

def normalize_rating(rating: float, source: str) -> float:
    """Normalize rating to 0-1 scale"""
    if source == "amazon":
        # Amazon ratings are 1-5, convert to 0-1
        return (rating - 1) / 4
    elif source == "reddit":
        # Reddit upvote ratio is already 0-1
        return rating
    else:
        # Assume already normalized
        return min(1.0, max(0.0, rating))
