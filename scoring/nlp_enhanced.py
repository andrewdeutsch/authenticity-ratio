"""
Enhanced NLP analysis for Trust Stack attribute detection

This module provides advanced NLP capabilities for Phase B:
- Sentiment analysis using transformers
- Readability scoring using textstat
- Language detection with confidence scores

These enhancements improve attribute detection accuracy and coverage.
"""

import logging
from typing import Optional, Dict, Any, List
from functools import lru_cache

logger = logging.getLogger(__name__)

# Lazy loading to avoid import errors if dependencies not installed
_sentiment_analyzer = None
_embedding_model = None


def _get_sentiment_analyzer():
    """Lazy load sentiment analysis pipeline"""
    global _sentiment_analyzer

    if _sentiment_analyzer is None:
        try:
            from transformers import pipeline
            logger.info("Loading sentiment analysis model (distilbert-base-uncased-finetuned-sst-2-english)...")
            _sentiment_analyzer = pipeline(
                "sentiment-analysis",
                model="distilbert-base-uncased-finetuned-sst-2-english"
            )
            logger.info("Sentiment analysis model loaded successfully")
        except Exception as e:
            logger.warning(f"Could not load sentiment analyzer: {e}")
            _sentiment_analyzer = False  # Mark as failed

    return _sentiment_analyzer if _sentiment_analyzer is not False else None


class SentimentAnalyzer:
    """
    Sentiment analysis for Trust Stack attributes

    Uses transformer-based models for accurate sentiment detection.
    Enhances attributes:
    - tone_sentiment_appropriateness (Resonance)
    - trust_fluctuation_index (Coherence)
    """

    def __init__(self):
        self.analyzer = _get_sentiment_analyzer()
        self.enabled = self.analyzer is not None

    def analyze_sentiment(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Analyze sentiment of text

        Args:
            text: Text to analyze (will be truncated to 512 tokens)

        Returns:
            Dictionary with sentiment info or None if analysis fails
            {
                'label': 'POSITIVE'|'NEGATIVE'|'NEUTRAL',
                'score': float (confidence 0-1),
                'value': float (mapped to 1-10 scale)
            }
        """
        if not self.enabled:
            return None

        try:
            # Truncate to 512 characters (roughly 512 tokens)
            text_truncated = text[:512] if text else ""

            if not text_truncated.strip():
                return None

            # Run sentiment analysis
            result = self.analyzer(text_truncated)[0]

            sentiment_label = result['label']  # POSITIVE or NEGATIVE
            confidence = result['score']

            # Map to 1-10 scale
            # POSITIVE: 7-10 (higher confidence = higher rating)
            # NEGATIVE: 1-4 (higher confidence = lower rating)
            if sentiment_label == 'POSITIVE':
                value = 7 + (confidence * 3)  # 7.0-10.0
            elif sentiment_label == 'NEGATIVE':
                value = 1 + ((1 - confidence) * 3)  # 1.0-4.0
            else:  # NEUTRAL (some models return this)
                value = 5 + (confidence * 2)  # 5.0-7.0

            return {
                'label': sentiment_label,
                'score': confidence,
                'value': value,
                'evidence': f"Sentiment: {sentiment_label} (confidence: {confidence:.2f})"
            }

        except Exception as e:
            logger.warning(f"Sentiment analysis failed: {e}")
            return None

    def analyze_tone_appropriateness(self, text: str, expected_tone: str = 'positive') -> Optional[float]:
        """
        Analyze if tone is appropriate for context

        Args:
            text: Content text
            expected_tone: Expected tone ('positive', 'negative', 'neutral')

        Returns:
            Rating 1-10 (10 = perfect tone match)
        """
        sentiment_result = self.analyze_sentiment(text)

        if not sentiment_result:
            return None

        detected_tone = sentiment_result['label'].lower()
        confidence = sentiment_result['score']

        # Check if detected tone matches expected
        if expected_tone.lower() in detected_tone:
            # Good match - higher confidence = higher rating
            return 7 + (confidence * 3)
        else:
            # Mismatch - return lower rating
            return 3 + ((1 - confidence) * 2)


class ReadabilityAnalyzer:
    """
    Readability analysis for Trust Stack attributes

    Uses textstat for multiple readability metrics.
    Enhances attributes:
    - readability_grade_level_fit (Resonance)
    """

    def __init__(self):
        self.enabled = True
        try:
            import textstat
            self.textstat = textstat
        except ImportError:
            logger.warning("textstat not available - readability analysis disabled")
            self.enabled = False
            self.textstat = None

    def analyze_readability(self, text: str, target_grade: float = 9.0) -> Optional[Dict[str, Any]]:
        """
        Analyze text readability

        Args:
            text: Text to analyze
            target_grade: Target reading grade level (default: 9.0 for general audience)

        Returns:
            Dictionary with readability metrics or None if analysis fails
            {
                'flesch_reading_ease': float,
                'flesch_kincaid_grade': float,
                'smog_index': float,
                'value': float (rating 1-10),
                'evidence': str
            }
        """
        if not self.enabled or not text:
            return None

        try:
            # Calculate multiple readability metrics
            flesch_reading_ease = self.textstat.flesch_reading_ease(text)
            flesch_kincaid_grade = self.textstat.flesch_kincaid_grade(text)
            smog_index = self.textstat.smog_index(text)

            # Calculate grade level difference from target
            grade_diff = abs(flesch_kincaid_grade - target_grade)

            # Map to 1-10 scale (closer to target = higher rating)
            if grade_diff <= 1:
                value = 10.0
            elif grade_diff <= 2:
                value = 8.0
            elif grade_diff <= 3:
                value = 6.0
            elif grade_diff <= 5:
                value = 4.0
            else:
                value = 2.0

            return {
                'flesch_reading_ease': flesch_reading_ease,
                'flesch_kincaid_grade': flesch_kincaid_grade,
                'smog_index': smog_index,
                'value': value,
                'evidence': f"Grade level: {flesch_kincaid_grade:.1f} (target: {target_grade:.1f}), SMOG: {smog_index:.1f}"
            }

        except Exception as e:
            logger.warning(f"Readability analysis failed: {e}")
            return None

    def get_reading_level_category(self, grade_level: float) -> str:
        """
        Categorize reading level

        Args:
            grade_level: Flesch-Kincaid grade level

        Returns:
            Category string
        """
        if grade_level <= 6:
            return "elementary"
        elif grade_level <= 8:
            return "middle_school"
        elif grade_level <= 12:
            return "high_school"
        elif grade_level <= 16:
            return "college"
        else:
            return "professional"


class LanguageDetector:
    """
    Enhanced language detection with confidence scores

    Uses langdetect for probabilistic language detection.
    Enhances attributes:
    - language_locale_match (Resonance)
    """

    def __init__(self):
        self.enabled = True
        try:
            from langdetect import detect, detect_langs
            self.detect = detect
            self.detect_langs = detect_langs
        except ImportError:
            logger.warning("langdetect not available - language detection disabled")
            self.enabled = False
            self.detect = None
            self.detect_langs = None

    def detect_language(self, text: str, target_language: str = 'en') -> Optional[Dict[str, Any]]:
        """
        Detect language with confidence scores

        Args:
            text: Text to analyze
            target_language: Expected language code (e.g., 'en', 'es', 'fr')

        Returns:
            Dictionary with detection results or None if detection fails
            {
                'detected_language': str,
                'confidence': float,
                'all_languages': List[tuple],  # [(lang, prob), ...]
                'value': float (rating 1-10),
                'evidence': str
            }
        """
        if not self.enabled or not text or len(text.strip()) < 10:
            return None

        try:
            # Detect with confidence
            detected = self.detect_langs(text)

            if not detected:
                return None

            # Get top detection
            top_lang = detected[0]
            lang_code = top_lang.lang
            confidence = top_lang.prob

            # Check if matches target
            if lang_code == target_language:
                value = 9 + confidence  # 9.0-10.0
            elif lang_code.startswith(target_language[:2]):
                # Close match (e.g., en-US vs en)
                value = 7 + (confidence * 2)  # 7.0-9.0
            else:
                # Mismatch
                value = 1 + (confidence * 3)  # 1.0-4.0

            # Get all detected languages
            all_languages = [(d.lang, d.prob) for d in detected[:3]]

            return {
                'detected_language': lang_code,
                'confidence': confidence,
                'all_languages': all_languages,
                'value': value,
                'evidence': f"Detected: {lang_code} (confidence: {confidence:.2f})"
            }

        except Exception as e:
            logger.warning(f"Language detection failed: {e}")
            return None

    def is_language_match(self, text: str, target_language: str = 'en', min_confidence: float = 0.7) -> bool:
        """
        Check if text matches target language with minimum confidence

        Args:
            text: Text to analyze
            target_language: Expected language code
            min_confidence: Minimum confidence threshold (0-1)

        Returns:
            True if language matches with sufficient confidence
        """
        result = self.detect_language(text, target_language)

        if not result:
            return False

        return (result['detected_language'] == target_language and
                result['confidence'] >= min_confidence)


# Singleton instances for reuse
_sentiment_analyzer_instance = None
_readability_analyzer_instance = None
_language_detector_instance = None


def get_sentiment_analyzer() -> SentimentAnalyzer:
    """Get singleton SentimentAnalyzer instance"""
    global _sentiment_analyzer_instance
    if _sentiment_analyzer_instance is None:
        _sentiment_analyzer_instance = SentimentAnalyzer()
    return _sentiment_analyzer_instance


def get_readability_analyzer() -> ReadabilityAnalyzer:
    """Get singleton ReadabilityAnalyzer instance"""
    global _readability_analyzer_instance
    if _readability_analyzer_instance is None:
        _readability_analyzer_instance = ReadabilityAnalyzer()
    return _readability_analyzer_instance


def get_language_detector() -> LanguageDetector:
    """Get singleton LanguageDetector instance"""
    global _language_detector_instance
    if _language_detector_instance is None:
        _language_detector_instance = LanguageDetector()
    return _language_detector_instance
