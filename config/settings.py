"""
Main configuration settings for AR tool
"""

import os
from typing import Dict, List, Any
from dataclasses import dataclass

@dataclass
class ScoringWeights:
    """5D Trust Dimension weights"""
    provenance: float = 0.20
    verification: float = 0.20
    transparency: float = 0.20
    coherence: float = 0.20
    resonance: float = 0.20

@dataclass
class APIConfig:
    """API configurations for data sources"""
    reddit_client_id: str = os.getenv('REDDIT_CLIENT_ID', '')
    reddit_client_secret: str = os.getenv('REDDIT_CLIENT_SECRET', '')
    reddit_user_agent: str = os.getenv('REDDIT_USER_AGENT', 'AR-Tool/1.0')
    
    # Amazon Product Advertising API
    amazon_access_key: str = os.getenv('AMAZON_ACCESS_KEY', '')
    amazon_secret_key: str = os.getenv('AMAZON_SECRET_KEY', '')
    amazon_associate_tag: str = os.getenv('AMAZON_ASSOCIATE_TAG', '')
    
    # OpenAI for LLM scoring
    openai_api_key: str = os.getenv('OPENAI_API_KEY', '')

# Global settings
SETTINGS = {
    'app_name': 'Authenticity Ratio Tool',
    'version': '1.0.0',
    'debug': os.getenv('DEBUG', 'False').lower() == 'true',
    
    # Scoring configuration
    'scoring_weights': ScoringWeights(),
    'rubric_version': 'v1.0',
    'min_score_threshold': 0.7,  # Minimum score to be considered authentic
    'suspect_threshold': 0.5,    # Score range for suspect content
    
    # Content processing
    'max_content_length': 10000,  # Characters
    'deduplication_window': 24,   # Hours for SimHash deduplication
    'batch_size': 100,
    
    # API rate limits
    'reddit_rate_limit': 60,      # requests per minute
    'amazon_rate_limit': 1,       # requests per second
    'openai_rate_limit': 60,      # requests per minute
    
    # Data retention
    'data_retention_days': 90,
    'max_runs_per_brand': 1000,
    
    # Reporting
    'report_formats': ['pdf', 'markdown', 'json'],
    'default_report_format': 'pdf',
    'include_charts': True,
    'chart_format': 'png',
}

# Brand configuration templates
BRAND_TEMPLATES = {
    'default': {
        'keywords': [],
        'exclude_keywords': [],
        'sources': ['reddit', 'amazon'],
        'custom_scoring_weights': None,
    }
}

# Verification database endpoints
VERIFICATION_DBS = {
    'fda': 'https://api.fda.gov/',
    'sec': 'https://www.sec.gov/',
    'whois': 'https://whoisjson.com/',
    'c2pa': 'https://c2pa.org/',
}

def get_brand_config(brand_id: str) -> Dict[str, Any]:
    """Get configuration for a specific brand"""
    # In production, this would load from database or config files
    return BRAND_TEMPLATES.get('default', {}).copy()

def validate_config() -> List[str]:
    """Validate configuration and return any issues"""
    issues = []
    
    if not SETTINGS['scoring_weights'].provenance + \
           SETTINGS['scoring_weights'].verification + \
           SETTINGS['scoring_weights'].transparency + \
           SETTINGS['scoring_weights'].coherence + \
           SETTINGS['scoring_weights'].resonance == 1.0:
        issues.append("Scoring weights must sum to 1.0")
    
    if SETTINGS['min_score_threshold'] <= SETTINGS['suspect_threshold']:
        issues.append("Min score threshold must be greater than suspect threshold")
    
    return issues
