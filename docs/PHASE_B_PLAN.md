# Phase B Plan: Enhanced Attribute Detection

## Overview
Enhance Trust Stack attribute detection from basic heuristics to advanced NLP, embeddings, and external APIs.

## Current State (Phase A)
- ✅ 36 attributes with basic heuristic detection
- ✅ ~11 attributes detected per content (30% coverage)
- ✅ Simple pattern matching, metadata checks
- ⚠️ No sentiment/tone analysis
- ⚠️ No embedding-based consistency checks
- ⚠️ No media analysis (C2PA, EXIF)
- ⚠️ No external API integration

## Phase B Goals
Increase detection coverage from 30% to 60-70% and improve accuracy.

---

## Enhancement Areas

### 1. NLP Models (Priority: HIGH)

#### Sentiment Analysis
**Attributes Enhanced:**
- `tone_sentiment_appropriateness` (Resonance)
- `trust_fluctuation_index` (Coherence)

**Implementation:**
```python
# Use transformers for sentiment
from transformers import pipeline
sentiment_analyzer = pipeline("sentiment-analysis")

def _detect_tone_sentiment_enhanced(content):
    result = sentiment_analyzer(content.body[:512])
    sentiment = result[0]['label']  # POSITIVE/NEGATIVE/NEUTRAL
    confidence = result[0]['score']

    # Map to 1-10 scale
    if sentiment == 'POSITIVE':
        value = 7 + (confidence * 3)  # 7-10
    elif sentiment == 'NEGATIVE':
        value = 1 + (confidence * 3)  # 1-4
    else:
        value = 5 + (confidence * 2)  # 5-7

    return DetectedAttribute(
        attribute_id="tone_sentiment_appropriateness",
        dimension="resonance",
        label="Tone & sentiment appropriateness",
        value=value,
        evidence=f"Sentiment: {sentiment} ({confidence:.2f})",
        confidence=confidence
    )
```

**Models to Use:**
- `distilbert-base-uncased-finetuned-sst-2-english` (sentiment)
- `cardiffnlp/twitter-roberta-base-sentiment` (social media)

#### Readability Analysis
**Attributes Enhanced:**
- `readability_grade_level_fit` (Resonance)

**Implementation:**
```python
import textstat

def _detect_readability_enhanced(content):
    text = content.body

    # Multiple readability metrics
    flesch_reading_ease = textstat.flesch_reading_ease(text)
    flesch_kincaid_grade = textstat.flesch_kincaid_grade(text)
    smog_index = textstat.smog_index(text)

    # Target: Grade 8-10 (general audience)
    target_grade = 9.0
    grade_diff = abs(flesch_kincaid_grade - target_grade)

    # Map to 1-10 scale
    if grade_diff <= 1:
        value = 10
    elif grade_diff <= 2:
        value = 8
    elif grade_diff <= 3:
        value = 6
    elif grade_diff <= 5:
        value = 4
    else:
        value = 2

    return DetectedAttribute(
        attribute_id="readability_grade_level_fit",
        dimension="resonance",
        label="Readability grade level fit",
        value=value,
        evidence=f"Grade: {flesch_kincaid_grade:.1f}, SMOG: {smog_index:.1f}",
        confidence=0.9
    )
```

**Library:** `textstat` (lightweight, no ML dependencies)

---

### 2. Embedding-Based Checks (Priority: HIGH)

#### Brand Voice Consistency
**Attributes Enhanced:**
- `brand_voice_consistency_score` (Coherence)

**Implementation:**
```python
from sentence_transformers import SentenceTransformer
import numpy as np

# Initialize once
model = SentenceTransformer('all-MiniLM-L6-v2')  # Fast, good quality

def _detect_brand_voice_enhanced(content, brand_corpus):
    """
    Compare content embedding to brand voice corpus

    brand_corpus: List of example brand content for comparison
    """
    # Embed content
    content_embedding = model.encode(content.body)

    # Embed brand corpus
    brand_embeddings = model.encode(brand_corpus)

    # Calculate cosine similarity
    similarities = [
        np.dot(content_embedding, brand_emb) /
        (np.linalg.norm(content_embedding) * np.linalg.norm(brand_emb))
        for brand_emb in brand_embeddings
    ]

    avg_similarity = np.mean(similarities)

    # Map similarity (0-1) to rating (1-10)
    # 0.8+ = excellent consistency
    # 0.6-0.8 = good
    # 0.4-0.6 = fair
    # <0.4 = poor

    if avg_similarity >= 0.8:
        value = 9 + (avg_similarity - 0.8) * 5  # 9-10
    elif avg_similarity >= 0.6:
        value = 6 + (avg_similarity - 0.6) * 15  # 6-9
    elif avg_similarity >= 0.4:
        value = 3 + (avg_similarity - 0.4) * 15  # 3-6
    else:
        value = 1 + (avg_similarity * 5)  # 1-3

    return DetectedAttribute(
        attribute_id="brand_voice_consistency_score",
        dimension="coherence",
        label="Brand voice consistency score",
        value=value,
        evidence=f"Similarity: {avg_similarity:.3f}",
        confidence=0.85
    )
```

**Model:** `all-MiniLM-L6-v2` (384-dim, fast, good quality)

#### Claim Consistency
**Attributes Enhanced:**
- `claim_consistency_across_pages` (Coherence)

**Implementation:**
```python
from sentence_transformers import util

def _detect_claim_consistency_enhanced(content, related_content):
    """
    Check if claims are consistent across related content
    """
    # Extract claims (simple sentence splitting for now)
    content_claims = [s.strip() for s in content.body.split('.') if len(s.strip()) > 20]

    if not content_claims:
        return None

    # Embed claims
    claim_embeddings = model.encode(content_claims)

    # Check for contradictions with related content claims
    contradictions = 0
    for related in related_content:
        related_claims = [s.strip() for s in related.body.split('.') if len(s.strip()) > 20]
        if not related_claims:
            continue

        related_embeddings = model.encode(related_claims)

        # Find semantically similar but potentially contradictory claims
        for i, claim_emb in enumerate(claim_embeddings):
            for j, related_emb in enumerate(related_embeddings):
                similarity = util.cos_sim(claim_emb, related_emb).item()

                # High semantic similarity but check for negation words
                if similarity > 0.7:
                    claim_text = content_claims[i].lower()
                    related_text = related_claims[j].lower()

                    # Simple negation check
                    negation_words = ['not', 'no', 'never', 'none', 'neither']
                    claim_has_neg = any(word in claim_text for word in negation_words)
                    related_has_neg = any(word in related_text for word in negation_words)

                    if claim_has_neg != related_has_neg:
                        contradictions += 1

    # Map contradictions to rating
    if contradictions == 0:
        value = 10
    elif contradictions <= 2:
        value = 7
    elif contradictions <= 5:
        value = 4
    else:
        value = 1

    return DetectedAttribute(
        attribute_id="claim_consistency_across_pages",
        dimension="coherence",
        label="Claim consistency across pages",
        value=value,
        evidence=f"{contradictions} potential contradictions found",
        confidence=0.7
    )
```

---

### 3. Enhanced Text Analysis (Priority: MEDIUM)

#### Language Detection
**Attributes Enhanced:**
- `language_locale_match` (Resonance)

**Implementation:**
```python
from langdetect import detect, detect_langs

def _detect_language_match_enhanced(content, target_language='en'):
    """Enhanced language detection with confidence"""
    try:
        # Detect with confidence
        detected = detect_langs(content.body)

        # Get top detection
        top_lang = detected[0]
        lang_code = top_lang.lang
        confidence = top_lang.prob

        # Check if matches target
        if lang_code == target_language:
            value = 9 + confidence  # 9-10
        elif lang_code.startswith(target_language[:2]):  # e.g., en-US vs en
            value = 7 + confidence * 2  # 7-9
        else:
            value = 1 + confidence * 3  # 1-4

        return DetectedAttribute(
            attribute_id="language_locale_match",
            dimension="resonance",
            label="Language/locale match",
            value=value,
            evidence=f"Detected: {lang_code} ({confidence:.2f})",
            confidence=confidence
        )
    except Exception:
        return None
```

**Library:** `langdetect` (fast, no ML dependencies)

---

### 4. External API Integration Framework (Priority: MEDIUM)

Create framework for external API calls with caching and rate limiting.

**File:** `scoring/external_apis.py`

```python
import requests
import time
from functools import lru_cache
from typing import Optional, Dict, Any

class ExternalAPIClient:
    """Base class for external API integrations"""

    def __init__(self, api_key: Optional[str] = None, rate_limit: float = 1.0):
        self.api_key = api_key
        self.rate_limit = rate_limit  # seconds between requests
        self.last_request_time = 0

    def _rate_limit_wait(self):
        """Enforce rate limiting"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.rate_limit:
            time.sleep(self.rate_limit - elapsed)
        self.last_request_time = time.time()

    @lru_cache(maxsize=1000)
    def _cached_get(self, url: str) -> Optional[Dict[str, Any]]:
        """Cached GET request"""
        self._rate_limit_wait()
        try:
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.warning(f"API request failed: {e}")
            return None


class DomainReputationClient(ExternalAPIClient):
    """Check domain reputation (NewsGuard-style)"""

    def get_domain_score(self, domain: str) -> Optional[float]:
        """
        Get domain trust score (0-10)

        Returns None if domain not found or API unavailable
        """
        # TODO: Integrate with actual reputation API
        # For now, use a simple whitelist/blacklist

        trusted_domains = {
            '.gov': 10,
            '.edu': 9,
            '.org': 7,
            'nytimes.com': 9,
            'wsj.com': 9,
            'bbc.com': 9,
            'reuters.com': 9,
            'apnews.com': 9,
        }

        untrusted_domains = {
            '.tk': 2,  # Free TLD, often spam
            '.ml': 2,
            '.ga': 2,
        }

        # Check trusted
        for trusted, score in trusted_domains.items():
            if domain.endswith(trusted):
                return score

        # Check untrusted
        for untrusted, score in untrusted_domains.items():
            if domain.endswith(untrusted):
                return score

        # Default: neutral
        return 5.0


class FactCheckingClient(ExternalAPIClient):
    """Check claims against fact-checking databases"""

    def check_claim(self, claim: str) -> Optional[Dict[str, Any]]:
        """
        Check if claim has been fact-checked

        Returns: {
            'rating': str,  # 'true', 'false', 'mixed', 'unverified'
            'confidence': float,
            'source': str
        }
        """
        # TODO: Integrate with ClaimBuster, Google Fact Check API, etc.
        # For now, return None (not implemented)
        return None
```

---

### 5. Implementation Strategy

#### Phase B.1: Core NLP (Week 1)
- ✅ Add sentiment analysis with transformers
- ✅ Enhance readability with textstat
- ✅ Improve language detection with langdetect
- ✅ Update existing detectors to use new methods

#### Phase B.2: Embeddings (Week 1)
- ✅ Integrate sentence-transformers
- ✅ Implement brand voice consistency
- ✅ Add claim consistency checking
- ✅ Create embedding cache for performance

#### Phase B.3: External APIs (Week 2)
- ✅ Create API client framework
- ✅ Add domain reputation checking
- ✅ Stub fact-checking integration
- ✅ Add rate limiting and caching

#### Phase B.4: Testing & Validation (Week 2)
- ✅ Test with diverse content
- ✅ Measure coverage improvement (30% → 60%+)
- ✅ Validate accuracy with manual review
- ✅ Performance benchmarks

---

## Dependencies to Add

### Python Packages
```bash
# NLP
pip install transformers>=4.30.0
pip install torch>=2.0.0  # or tensorflow
pip install textstat>=0.7.3
pip install langdetect>=1.0.9

# Embeddings
pip install sentence-transformers>=2.2.2

# APIs
pip install requests>=2.31.0

# Optional (for advanced features)
pip install spacy>=3.5.0
pip install nltk>=3.8.1
```

### Model Downloads
```python
# Sentiment analysis
from transformers import pipeline
sentiment = pipeline("sentiment-analysis", model="distilbert-base-uncased-finetuned-sst-2-english")

# Embeddings
from sentence_transformers import SentenceTransformer
embedder = SentenceTransformer('all-MiniLM-L6-v2')
```

---

## Expected Improvements

### Coverage
- **Before (Phase A)**: ~11/36 attributes (30%)
- **After (Phase B)**: ~22-25/36 attributes (60-70%)

### Accuracy
- **Sentiment**: 85-90% accuracy (vs 50% heuristic)
- **Readability**: Proper grade-level scoring
- **Brand voice**: Quantitative similarity metrics
- **Language**: Confidence scores, not just binary

### Performance
- **Sentiment**: ~100-200ms per content (GPU: 50ms)
- **Embeddings**: ~50-100ms per content (cached)
- **External APIs**: ~500-1000ms (cached, rate-limited)
- **Overall**: +500-1000ms per content item

---

## Files to Create/Modify

### New Files
- `scoring/nlp_enhanced.py` - NLP model wrappers
- `scoring/embeddings.py` - Embedding utilities
- `scoring/external_apis.py` - External API clients

### Modified Files
- `scoring/attribute_detector.py` - Enhanced detection methods
- `config/settings.py` - Add NLP/API configuration
- `requirements.txt` - Add new dependencies

### Test Files
- `scripts/test_enhanced_detection.py` - Test Phase B enhancements
- `scripts/benchmark_detection.py` - Performance benchmarks

---

## Configuration

Add to `config/settings.py`:

```python
# Phase B: Enhanced Detection
NLP_CONFIG = {
    'enabled': True,
    'sentiment_model': 'distilbert-base-uncased-finetuned-sst-2-english',
    'embedding_model': 'all-MiniLM-L6-v2',
    'cache_embeddings': True,
    'use_gpu': False,  # Set to True if CUDA available
}

API_CONFIG = {
    'domain_reputation_enabled': True,
    'fact_checking_enabled': False,  # Requires API key
    'rate_limit': 1.0,  # seconds between API calls
}

BRAND_VOICE_CONFIG = {
    'enabled': True,
    'corpus_path': 'data/brand_voice_corpus.txt',  # Brand content examples
    'min_similarity': 0.4,  # Minimum similarity for "on brand"
}
```

---

## Success Metrics

1. **Coverage**: Increase from 30% to 60-70%
2. **Accuracy**: Sentiment 85%+, Readability validated
3. **Performance**: <2s additional latency per item
4. **User Feedback**: Higher confidence in ratings

---

## Next Steps

1. Install dependencies
2. Create NLP wrapper module
3. Create embeddings module
4. Enhance attribute detector
5. Test and validate
6. Benchmark performance
7. Document improvements

Ready to implement!
