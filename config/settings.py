"""
Main configuration settings for AR tool
"""

import os
from typing import Dict, List, Any
from dataclasses import dataclass
from dotenv import load_dotenv

# Load local .env file if present so os.getenv reads local secrets during dev
load_dotenv()

@dataclass
class ScoringWeights:
    """6D Trust Dimension weights"""
    provenance: float = 0.16666666666666666
    verification: float = 0.16666666666666666
    transparency: float = 0.16666666666666666
    coherence: float = 0.16666666666666666
    resonance: float = 0.16666666666666666
    ai_readiness: float = 0.16666666666666666

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
    # YouTube Data API v3
    youtube_api_key: str = os.getenv('YOUTUBE_API_KEY', '')

# Global settings
SETTINGS = {
    'app_name': 'Trust Stack Rating Tool',
    'version': '2.0.0-trust-stack',
    'debug': os.getenv('DEBUG', 'False').lower() == 'true',

    # Trust Stack Rating configuration
    'scoring_weights': ScoringWeights(),
    'rubric_version': 'v2.0-trust-stack',

    # Legacy AR thresholds (kept for backward compatibility and optional descriptive bands)
    'min_score_threshold': 0.75,  # 75/100 - Excellent/Authentic threshold
    'suspect_threshold': 0.40,    # 40/100 - Fair/Suspect threshold

    # Rating bands (optional descriptive labels, not used for AR calculation)
    'rating_scale': 100,  # 0-100 scale for all ratings
    'rating_bands': {
        'excellent': 80,  # >= 80 = Excellent
        'good': 60,       # 60-79 = Good
        'fair': 40,       # 40-59 = Fair
        'poor': 0,        # < 40 = Poor
    },

    # Feature flags
    'enable_legacy_ar_mode': True,  # Synthesize AR from ratings for backward compatibility
    'show_ar_in_ui': False,  # Don't show AR in initial UI (can enable later)
    
    # Content processing
    'max_content_length': 10000,  # Characters
    'deduplication_window': 24,   # Hours for SimHash deduplication
    'batch_size': 100,
    
    # API rate limits
    'reddit_rate_limit': 60,      # requests per minute
    'amazon_rate_limit': 1,       # requests per second
    'openai_rate_limit': 60,      # requests per minute
    'youtube_rate_limit': 60,    # requests per minute (YouTube Data API key quota should be considered)
    
    # Data retention
    'data_retention_days': 90,
    'max_runs_per_brand': 1000,
    
    # Reporting
    'report_formats': ['pdf', 'markdown', 'json'],
    'default_report_format': 'pdf',
    'include_charts': True,
    'chart_format': 'png',
    # Triage configuration: enable cheap triage before LLM scoring
    'triage_enabled': True,
    'triage_promote_threshold': 0.6,
    # When true, items demoted by triage are excluded from S3 uploads and reports
    'exclude_demoted_from_upload': False,
    # Global control: whether to include parsed comments in the analysis
    'include_comments_in_analysis': False,
}

# Brand configuration templates
BRAND_TEMPLATES = {
    'default': {
        'keywords': [],
        'exclude_keywords': [],
        'sources': ['reddit', 'amazon', 'youtube', 'yelp'],
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
           SETTINGS['scoring_weights'].resonance + \
           SETTINGS['scoring_weights'].ai_readiness == 1.0:
        issues.append("Scoring weights must sum to 1.0")
    
    if SETTINGS['min_score_threshold'] <= SETTINGS['suspect_threshold']:
        issues.append("Min score threshold must be greater than suspect threshold")
    
    return issues
