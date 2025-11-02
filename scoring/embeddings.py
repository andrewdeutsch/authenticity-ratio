"""
Embedding-based analysis for Trust Stack attribute detection

This module provides semantic embedding capabilities for Phase B:
- Brand voice consistency using sentence embeddings
- Claim consistency checking across content
- Semantic similarity analysis

Uses sentence-transformers for efficient embedding generation.
"""

import logging
from typing import Optional, Dict, Any, List, Tuple
import numpy as np
from functools import lru_cache

logger = logging.getLogger(__name__)

# Lazy loading to avoid import errors if dependencies not installed
_embedding_model = None


def _get_embedding_model():
    """Lazy load sentence embedding model"""
    global _embedding_model

    if _embedding_model is None:
        try:
            from sentence_transformers import SentenceTransformer
            logger.info("Loading sentence embedding model (all-MiniLM-L6-v2)...")
            _embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("Embedding model loaded successfully")
        except Exception as e:
            logger.warning(f"Could not load embedding model: {e}")
            _embedding_model = False  # Mark as failed

    return _embedding_model if _embedding_model is not False else None


class BrandVoiceAnalyzer:
    """
    Brand voice consistency analysis using embeddings

    Compares content embeddings to brand corpus to measure consistency.
    Enhances attributes:
    - brand_voice_consistency_score (Coherence)
    """

    def __init__(self, brand_corpus: Optional[List[str]] = None):
        """
        Initialize analyzer

        Args:
            brand_corpus: List of example brand content for comparison
        """
        self.model = _get_embedding_model()
        self.enabled = self.model is not None
        self.brand_corpus = brand_corpus or []
        self._brand_embeddings = None

    def set_brand_corpus(self, brand_corpus: List[str]):
        """
        Set or update brand voice corpus

        Args:
            brand_corpus: List of example brand content
        """
        self.brand_corpus = brand_corpus
        self._brand_embeddings = None  # Reset cached embeddings

    def _get_brand_embeddings(self) -> Optional[np.ndarray]:
        """Get cached brand corpus embeddings"""
        if not self.enabled or not self.brand_corpus:
            return None

        if self._brand_embeddings is None:
            try:
                self._brand_embeddings = self.model.encode(
                    self.brand_corpus,
                    convert_to_numpy=True
                )
                logger.info(f"Encoded {len(self.brand_corpus)} brand corpus items")
            except Exception as e:
                logger.warning(f"Failed to encode brand corpus: {e}")
                return None

        return self._brand_embeddings

    def analyze_brand_voice_consistency(self, content: str) -> Optional[Dict[str, Any]]:
        """
        Analyze brand voice consistency

        Args:
            content: Content text to analyze

        Returns:
            Dictionary with consistency metrics or None if analysis fails
            {
                'similarity': float (0-1),
                'value': float (rating 1-10),
                'evidence': str,
                'confidence': float
            }
        """
        if not self.enabled or not content:
            return None

        brand_embeddings = self._get_brand_embeddings()
        if brand_embeddings is None or len(brand_embeddings) == 0:
            logger.debug("No brand corpus available for voice consistency analysis")
            return None

        try:
            # Encode content
            content_embedding = self.model.encode(content, convert_to_numpy=True)

            # Calculate cosine similarities with all brand corpus items
            similarities = self._cosine_similarities(content_embedding, brand_embeddings)

            # Use average similarity
            avg_similarity = float(np.mean(similarities))
            max_similarity = float(np.max(similarities))

            # Map similarity (0-1) to rating (1-10)
            # 0.8+ = excellent consistency (9-10)
            # 0.6-0.8 = good (6-9)
            # 0.4-0.6 = fair (3-6)
            # <0.4 = poor (1-3)
            if avg_similarity >= 0.8:
                value = 9 + (avg_similarity - 0.8) * 5  # 9-10
            elif avg_similarity >= 0.6:
                value = 6 + (avg_similarity - 0.6) * 15  # 6-9
            elif avg_similarity >= 0.4:
                value = 3 + (avg_similarity - 0.4) * 15  # 3-6
            else:
                value = 1 + (avg_similarity * 5)  # 1-3

            # Confidence based on corpus size and similarity variance
            similarity_variance = float(np.var(similarities))
            confidence = min(1.0, 0.5 + (len(self.brand_corpus) / 20) - similarity_variance)

            return {
                'similarity': avg_similarity,
                'max_similarity': max_similarity,
                'value': value,
                'evidence': f"Brand voice similarity: {avg_similarity:.3f} (max: {max_similarity:.3f})",
                'confidence': max(0.5, confidence)
            }

        except Exception as e:
            logger.warning(f"Brand voice analysis failed: {e}")
            return None

    def _cosine_similarities(self, query_embedding: np.ndarray, corpus_embeddings: np.ndarray) -> np.ndarray:
        """
        Calculate cosine similarities between query and corpus

        Args:
            query_embedding: Single embedding vector
            corpus_embeddings: Matrix of corpus embeddings

        Returns:
            Array of similarity scores
        """
        # Normalize embeddings
        query_norm = query_embedding / np.linalg.norm(query_embedding)
        corpus_norms = corpus_embeddings / np.linalg.norm(corpus_embeddings, axis=1, keepdims=True)

        # Calculate dot product (cosine similarity for normalized vectors)
        similarities = np.dot(corpus_norms, query_norm)

        return similarities


class ClaimConsistencyAnalyzer:
    """
    Claim consistency analysis across content

    Checks for contradictions and consistency in claims.
    Enhances attributes:
    - claim_consistency_across_pages (Coherence)
    """

    def __init__(self):
        self.model = _get_embedding_model()
        self.enabled = self.model is not None

    def analyze_claim_consistency(self, content: str, related_content: List[str]) -> Optional[Dict[str, Any]]:
        """
        Analyze claim consistency across content

        Args:
            content: Primary content text
            related_content: List of related content to compare against

        Returns:
            Dictionary with consistency metrics or None if analysis fails
            {
                'contradictions': int,
                'consistent_claims': int,
                'value': float (rating 1-10),
                'evidence': str,
                'confidence': float
            }
        """
        if not self.enabled or not content or not related_content:
            return None

        try:
            # Extract claims from content (simple sentence splitting for now)
            content_claims = self._extract_claims(content)

            if not content_claims:
                return None

            # Extract claims from related content
            all_related_claims = []
            for related in related_content:
                related_claims = self._extract_claims(related)
                all_related_claims.extend(related_claims)

            if not all_related_claims:
                return None

            # Encode all claims
            content_embeddings = self.model.encode(content_claims, convert_to_numpy=True)
            related_embeddings = self.model.encode(all_related_claims, convert_to_numpy=True)

            # Find potential contradictions
            contradictions = 0
            consistent_claims = 0

            for i, claim_text in enumerate(content_claims):
                claim_emb = content_embeddings[i]

                # Calculate similarities with related claims
                similarities = self._cosine_similarities(claim_emb, related_embeddings)

                # Find highly similar claims (semantic similarity > 0.7)
                similar_indices = np.where(similarities > 0.7)[0]

                for idx in similar_indices:
                    related_claim_text = all_related_claims[idx]

                    # Check for negation mismatch (simple heuristic)
                    if self._has_negation_mismatch(claim_text, related_claim_text):
                        contradictions += 1
                    else:
                        consistent_claims += 1

            # Map contradictions to rating
            if contradictions == 0:
                value = 10.0
            elif contradictions <= 2:
                value = 7.0
            elif contradictions <= 5:
                value = 4.0
            else:
                value = 1.0

            # Confidence based on number of claims analyzed
            confidence = min(1.0, 0.6 + (len(content_claims) / 20))

            return {
                'contradictions': contradictions,
                'consistent_claims': consistent_claims,
                'total_claims': len(content_claims),
                'value': value,
                'evidence': f"{contradictions} potential contradictions found across {len(content_claims)} claims",
                'confidence': confidence
            }

        except Exception as e:
            logger.warning(f"Claim consistency analysis failed: {e}")
            return None

    def _extract_claims(self, text: str, min_length: int = 20) -> List[str]:
        """
        Extract claims from text (simple sentence splitting)

        Args:
            text: Text to extract claims from
            min_length: Minimum claim length in characters

        Returns:
            List of claim strings
        """
        # Simple sentence splitting (in production, use spaCy or nltk)
        sentences = text.split('.')
        claims = [s.strip() for s in sentences if len(s.strip()) >= min_length]

        return claims

    def _has_negation_mismatch(self, claim1: str, claim2: str) -> bool:
        """
        Check if two similar claims have negation mismatch

        Args:
            claim1: First claim text
            claim2: Second claim text

        Returns:
            True if one claim is negated and the other is not
        """
        negation_words = ['not', 'no', 'never', 'none', 'neither', "n't", 'cannot']

        claim1_lower = claim1.lower()
        claim2_lower = claim2.lower()

        claim1_has_negation = any(word in claim1_lower for word in negation_words)
        claim2_has_negation = any(word in claim2_lower for word in negation_words)

        # Mismatch if one has negation and the other doesn't
        return claim1_has_negation != claim2_has_negation

    def _cosine_similarities(self, query_embedding: np.ndarray, corpus_embeddings: np.ndarray) -> np.ndarray:
        """Calculate cosine similarities (same as BrandVoiceAnalyzer)"""
        query_norm = query_embedding / np.linalg.norm(query_embedding)
        corpus_norms = corpus_embeddings / np.linalg.norm(corpus_embeddings, axis=1, keepdims=True)
        similarities = np.dot(corpus_norms, query_norm)
        return similarities


class SemanticSimilarityAnalyzer:
    """
    General semantic similarity analysis

    Provides utility methods for semantic comparison.
    """

    def __init__(self):
        self.model = _get_embedding_model()
        self.enabled = self.model is not None

    def calculate_similarity(self, text1: str, text2: str) -> Optional[float]:
        """
        Calculate semantic similarity between two texts

        Args:
            text1: First text
            text2: Second text

        Returns:
            Similarity score (0-1) or None if analysis fails
        """
        if not self.enabled or not text1 or not text2:
            return None

        try:
            embeddings = self.model.encode([text1, text2], convert_to_numpy=True)

            # Calculate cosine similarity
            similarity = np.dot(embeddings[0], embeddings[1]) / (
                np.linalg.norm(embeddings[0]) * np.linalg.norm(embeddings[1])
            )

            return float(similarity)

        except Exception as e:
            logger.warning(f"Similarity calculation failed: {e}")
            return None

    def find_most_similar(self, query: str, candidates: List[str], top_k: int = 5) -> List[Tuple[str, float]]:
        """
        Find most similar texts from candidates

        Args:
            query: Query text
            candidates: List of candidate texts
            top_k: Number of top results to return

        Returns:
            List of (text, similarity) tuples, sorted by similarity (descending)
        """
        if not self.enabled or not query or not candidates:
            return []

        try:
            # Encode query and candidates
            query_embedding = self.model.encode(query, convert_to_numpy=True)
            candidate_embeddings = self.model.encode(candidates, convert_to_numpy=True)

            # Calculate similarities
            query_norm = query_embedding / np.linalg.norm(query_embedding)
            candidate_norms = candidate_embeddings / np.linalg.norm(candidate_embeddings, axis=1, keepdims=True)
            similarities = np.dot(candidate_norms, query_norm)

            # Get top k
            top_indices = np.argsort(similarities)[::-1][:top_k]

            results = [(candidates[i], float(similarities[i])) for i in top_indices]

            return results

        except Exception as e:
            logger.warning(f"Finding similar texts failed: {e}")
            return []


# Singleton instances for reuse
_brand_voice_analyzer_instance = None
_claim_consistency_analyzer_instance = None
_semantic_similarity_analyzer_instance = None


def get_brand_voice_analyzer(brand_corpus: Optional[List[str]] = None) -> BrandVoiceAnalyzer:
    """Get singleton BrandVoiceAnalyzer instance"""
    global _brand_voice_analyzer_instance
    if _brand_voice_analyzer_instance is None:
        _brand_voice_analyzer_instance = BrandVoiceAnalyzer(brand_corpus)
    elif brand_corpus is not None:
        _brand_voice_analyzer_instance.set_brand_corpus(brand_corpus)
    return _brand_voice_analyzer_instance


def get_claim_consistency_analyzer() -> ClaimConsistencyAnalyzer:
    """Get singleton ClaimConsistencyAnalyzer instance"""
    global _claim_consistency_analyzer_instance
    if _claim_consistency_analyzer_instance is None:
        _claim_consistency_analyzer_instance = ClaimConsistencyAnalyzer()
    return _claim_consistency_analyzer_instance


def get_semantic_similarity_analyzer() -> SemanticSimilarityAnalyzer:
    """Get singleton SemanticSimilarityAnalyzer instance"""
    global _semantic_similarity_analyzer_instance
    if _semantic_similarity_analyzer_instance is None:
        _semantic_similarity_analyzer_instance = SemanticSimilarityAnalyzer()
    return _semantic_similarity_analyzer_instance
