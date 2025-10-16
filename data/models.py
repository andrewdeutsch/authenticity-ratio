"""
Data models for AR tool
Matching the AWS Athena schema structure
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum

class ContentSource(Enum):
    REDDIT = "reddit"
    AMAZON = "amazon"
    YOUTUBE = "youtube"
    BRAVE = "brave"

class ContentClass(Enum):
    AUTHENTIC = "authentic"
    SUSPECT = "suspect"
    INAUTHENTIC = "inauthentic"

@dataclass
class NormalizedContent:
    """Matches ar_content_normalized_v2 table schema"""
    content_id: str
    src: str
    platform_id: str
    author: str
    title: str
    body: str
    rating: Optional[float] = None
    upvotes: Optional[int] = None
    helpful_count: Optional[float] = None
    event_ts: str = ""  # Stored as string for Athena compatibility
    run_id: str = ""
    meta: Dict[str, str] = None
    
    def __post_init__(self):
        if self.meta is None:
            self.meta = {}

@dataclass
class ContentScores:
    """Matches ar_content_scores_v2 table schema"""
    content_id: str
    brand: str
    src: str
    event_ts: str
    score_provenance: float
    score_resonance: float
    score_coherence: float
    score_transparency: float
    score_verification: float
    class_label: str
    is_authentic: bool
    rubric_version: str
    run_id: str
    meta: str = ""
    
    @property
    def overall_score(self) -> float:
        """Calculate weighted overall score"""
        from config.settings import SETTINGS
        weights = SETTINGS['scoring_weights']
        
        return (
            self.score_provenance * weights.provenance +
            self.score_resonance * weights.resonance +
            self.score_coherence * weights.coherence +
            self.score_transparency * weights.transparency +
            self.score_verification * weights.verification
        )

@dataclass
class AuthenticityRatio:
    """AR calculation result"""
    brand_id: str
    source: str
    run_id: str
    total_items: int
    authentic_items: int
    suspect_items: int
    inauthentic_items: int
    authenticity_ratio_pct: float
    
    @property
    def extended_ar(self) -> float:
        """Extended AR formula: (A + 0.5S) ÷ (A + S + I) × 100"""
        if self.total_items == 0:
            return 0.0
        return (self.authentic_items + 0.5 * self.suspect_items) / self.total_items * 100

@dataclass
class BrandConfig:
    """Brand-specific configuration"""
    brand_id: str
    name: str
    keywords: List[str]
    exclude_keywords: List[str]
    sources: List[ContentSource]
    custom_scoring_weights: Optional[Dict[str, float]] = None
    active: bool = True

@dataclass
class PipelineRun:
    """Track pipeline execution"""
    run_id: str
    brand_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    status: str = "running"  # running, completed, failed
    items_processed: int = 0
    errors: List[str] = None
    # Optional: hold classified scores produced by the scoring pipeline so
    # callers (reports/telemetry) can consume the exact objects that were
    # uploaded to S3/Athena.
    classified_scores: Optional[List[Any]] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
