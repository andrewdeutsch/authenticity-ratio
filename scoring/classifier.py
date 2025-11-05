"""
Content classifier for Trust Stack Rating tool

DEPRECATED: This module provides legacy classification (Authentic/Suspect/Inauthentic)
for backward compatibility with AR calculations. In Trust Stack v2.0, the primary
model is per-property ratings (0-100 scale) without classification.

This classifier is kept for:
1. Optional descriptive rating bands (Excellent/Good/Fair/Poor)
2. Legacy AR synthesis when enable_legacy_ar_mode=True

New implementations should use TrustStackRating model with rating bands instead.
"""

from typing import List, Dict, Any
import logging
import json
import warnings

from config.settings import SETTINGS
from data.models import ContentScores, ContentClass, RatingBand

logger = logging.getLogger(__name__)

# Issue deprecation warning
warnings.warn(
    "ContentClassifier is deprecated in Trust Stack v2.0. "
    "Use TrustStackRating with rating_band property for new implementations. "
    "This classifier is kept for legacy AR mode only.",
    DeprecationWarning,
    stacklevel=2
)

class ContentClassifier:
    """
    DEPRECATED: Classifies content based on 5D scores

    This classifier provides legacy classification for backward compatibility.
    For Trust Stack v2.0, use rating bands instead.
    """

    def __init__(self, suppress_warning: bool = False):
        """
        Initialize classifier

        Args:
            suppress_warning: If True, suppress deprecation warning (useful for legacy mode)
        """
        self.min_authentic_threshold = SETTINGS['min_score_threshold']
        self.suspect_threshold = SETTINGS['suspect_threshold']
        self.scoring_weights = SETTINGS['scoring_weights']

        if not suppress_warning:
            logger.warning(
                "ContentClassifier is deprecated. "
                "Consider using rating bands from TrustStackRating model."
            )
    
    def classify_content(self, content_scores: ContentScores) -> ContentScores:
        """
        Classify content as Authentic, Suspect, or Inauthentic
        
        Args:
            content_scores: ContentScores object with dimension scores
            
        Returns:
            Updated ContentScores with classification
        """
        # Calculate weighted overall score
        overall_score = self._calculate_overall_score(content_scores)
        
        # Determine classification
        if overall_score >= self.min_authentic_threshold:
            class_label = ContentClass.AUTHENTIC.value
            is_authentic = True
        elif overall_score >= self.suspect_threshold:
            class_label = ContentClass.SUSPECT.value
            is_authentic = False
        else:
            class_label = ContentClass.INAUTHENTIC.value
            is_authentic = False
        
        # Update the content scores object
        content_scores.class_label = class_label
        content_scores.is_authentic = is_authentic
        
        logger.debug(f"Classified content {content_scores.content_id} as {class_label} (score: {overall_score:.3f})")
        
        return content_scores
    
    def _calculate_overall_score(self, content_scores: ContentScores) -> float:
        """Calculate weighted overall score from dimension scores"""
        return (
            content_scores.score_provenance * self.scoring_weights.provenance +
            content_scores.score_verification * self.scoring_weights.verification +
            content_scores.score_transparency * self.scoring_weights.transparency +
            content_scores.score_coherence * self.scoring_weights.coherence +
            content_scores.score_resonance * self.scoring_weights.resonance
        )
    
    def batch_classify_content(self, scores_list: List[ContentScores]) -> List[ContentScores]:
        """Classify multiple content scores in batch"""
        classified_scores = []
        
        logger.info(f"Batch classifying {len(scores_list)} content scores")
        
        for scores in scores_list:
            classified_score = self.classify_content(scores)
            classified_scores.append(classified_score)
        
        # Log classification summary
        self._log_classification_summary(classified_scores)
        
        return classified_scores
    
    def _log_classification_summary(self, classified_scores: List[ContentScores]) -> None:
        """Log summary of classification results"""
        authentic_count = sum(1 for s in classified_scores if s.class_label == ContentClass.AUTHENTIC.value)
        suspect_count = sum(1 for s in classified_scores if s.class_label == ContentClass.SUSPECT.value)
        inauthentic_count = sum(1 for s in classified_scores if s.class_label == ContentClass.INAUTHENTIC.value)
        
        total_count = len(classified_scores)
        
        logger.info(f"Classification Summary:")
        logger.info(f"  Total items: {total_count}")
        logger.info(f"  Authentic: {authentic_count} ({authentic_count/total_count*100:.1f}%)")
        logger.info(f"  Suspect: {suspect_count} ({suspect_count/total_count*100:.1f}%)")
        logger.info(f"  Inauthentic: {inauthentic_count} ({inauthentic_count/total_count*100:.1f}%)")
    
    def get_classification_confidence(self, content_scores: ContentScores) -> Dict[str, float]:
        """
        Get confidence scores for each classification
        
        Args:
            content_scores: ContentScores object
            
        Returns:
            Dictionary with confidence scores for each class
        """
        overall_score = self._calculate_overall_score(content_scores)
        
        # Calculate confidence based on distance from thresholds
        authentic_confidence = max(0, overall_score - self.min_authentic_threshold) / (1.0 - self.min_authentic_threshold)
        
        suspect_upper = min(1, (self.min_authentic_threshold - overall_score) / (self.min_authentic_threshold - self.suspect_threshold))
        suspect_lower = max(0, (overall_score - self.suspect_threshold) / (self.min_authentic_threshold - self.suspect_threshold))
        suspect_confidence = min(suspect_upper, suspect_lower)
        
        inauthentic_confidence = max(0, self.suspect_threshold - overall_score) / self.suspect_threshold
        
        # Normalize to sum to 1.0
        total_confidence = authentic_confidence + suspect_confidence + inauthentic_confidence
        if total_confidence > 0:
            authentic_confidence /= total_confidence
            suspect_confidence /= total_confidence
            inauthentic_confidence /= total_confidence
        
        return {
            "authentic": authentic_confidence,
            "suspect": suspect_confidence,
            "inauthentic": inauthentic_confidence
        }
    
    def analyze_dimension_performance(self, scores_list: List[ContentScores]) -> Dict[str, Any]:
        """
        Analyze how each dimension contributes to classification
        
        Args:
            scores_list: List of classified ContentScores
            
        Returns:
            Analysis of dimension performance
        """
        if not scores_list:
            return {}
        
        # Group by classification
        authentic_scores = [s for s in scores_list if s.class_label == ContentClass.AUTHENTIC.value]
        suspect_scores = [s for s in scores_list if s.class_label == ContentClass.SUSPECT.value]
        inauthentic_scores = [s for s in scores_list if s.class_label == ContentClass.INAUTHENTIC.value]
        
        analysis = {
            "dimension_averages": {
                "all": self._get_dimension_averages(scores_list),
                "authentic": self._get_dimension_averages(authentic_scores) if authentic_scores else {},
                "suspect": self._get_dimension_averages(suspect_scores) if suspect_scores else {},
                "inauthentic": self._get_dimension_averages(inauthentic_scores) if inauthentic_scores else {}
            },
            "dimension_correlations": self._get_dimension_correlations(scores_list),
            "classification_distribution": {
                "authentic": len(authentic_scores),
                "suspect": len(suspect_scores),
                "inauthentic": len(inauthentic_scores)
            }
        }
        
        return analysis
    
    def _get_dimension_averages(self, scores_list: List[ContentScores]) -> Dict[str, float]:
        """Get average scores for each dimension"""
        if not scores_list:
            return {}
        
        return {
            "provenance": sum(s.score_provenance for s in scores_list) / len(scores_list),
            "verification": sum(s.score_verification for s in scores_list) / len(scores_list),
            "transparency": sum(s.score_transparency for s in scores_list) / len(scores_list),
            "coherence": sum(s.score_coherence for s in scores_list) / len(scores_list),
            "resonance": sum(s.score_resonance for s in scores_list) / len(scores_list)
        }
    
    def _get_dimension_correlations(self, scores_list: List[ContentScores]) -> Dict[str, float]:
        """Calculate correlations between dimensions"""
        if len(scores_list) < 2:
            return {}
        
        # Simple correlation calculation (in production, use numpy/scipy)
        dimensions = ["provenance", "verification", "transparency", "coherence", "resonance"]
        correlations = {}
        
        for i, dim1 in enumerate(dimensions):
            for dim2 in dimensions[i+1:]:
                corr = self._calculate_correlation(
                    [getattr(s, f"score_{dim1}") for s in scores_list],
                    [getattr(s, f"score_{dim2}") for s in scores_list]
                )
                correlations[f"{dim1}_{dim2}"] = corr
        
        return correlations
    
    def _calculate_correlation(self, x: List[float], y: List[float]) -> float:
        """Calculate simple correlation coefficient"""
        if len(x) != len(y) or len(x) < 2:
            return 0.0

        n = len(x)
        sum_x = sum(x)
        sum_y = sum(y)
        sum_xy = sum(x[i] * y[i] for i in range(n))
        sum_x2 = sum(x[i] ** 2 for i in range(n))
        sum_y2 = sum(y[i] ** 2 for i in range(n))

        numerator = n * sum_xy - sum_x * sum_y
        denominator = ((n * sum_x2 - sum_x ** 2) * (n * sum_y2 - sum_y ** 2)) ** 0.5

        if denominator == 0:
            return 0.0

        return numerator / denominator

    # Trust Stack v2.0 methods

    def get_rating_band(self, content_scores: ContentScores) -> RatingBand:
        """
        Get Trust Stack rating band for content (new method for v2.0)

        Args:
            content_scores: ContentScores object

        Returns:
            RatingBand (Excellent/Good/Fair/Poor)
        """
        return content_scores.rating_band

    def batch_get_rating_bands(self, scores_list: List[ContentScores]) -> Dict[RatingBand, int]:
        """
        Get rating band distribution for batch of content

        Args:
            scores_list: List of ContentScores

        Returns:
            Dictionary with count for each rating band
        """
        distribution = {
            RatingBand.EXCELLENT: 0,
            RatingBand.GOOD: 0,
            RatingBand.FAIR: 0,
            RatingBand.POOR: 0
        }

        for scores in scores_list:
            band = self.get_rating_band(scores)
            distribution[band] += 1

        return distribution

    def log_rating_band_summary(self, scores_list: List[ContentScores]) -> None:
        """
        Log summary of rating band distribution (Trust Stack v2.0 style)

        Args:
            scores_list: List of ContentScores
        """
        distribution = self.batch_get_rating_bands(scores_list)
        total = len(scores_list)

        logger.info("Trust Stack Rating Band Summary:")
        logger.info(f"  Total items: {total}")
        logger.info(f"  Excellent (80-100): {distribution[RatingBand.EXCELLENT]} ({distribution[RatingBand.EXCELLENT]/total*100:.1f}%)")
        logger.info(f"  Good (60-79):      {distribution[RatingBand.GOOD]} ({distribution[RatingBand.GOOD]/total*100:.1f}%)")
        logger.info(f"  Fair (40-59):      {distribution[RatingBand.FAIR]} ({distribution[RatingBand.FAIR]/total*100:.1f}%)")
        logger.info(f"  Poor (0-39):       {distribution[RatingBand.POOR]} ({distribution[RatingBand.POOR]/total*100:.1f}%)")
