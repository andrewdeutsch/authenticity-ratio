"""
5D Trust Dimensions scorer for AR tool
Scores content on Provenance, Verification, Transparency, Coherence, Resonance
"""

from openai import OpenAI
from typing import Dict, Any, List, Optional
import logging
import json
from dataclasses import dataclass

from config.settings import SETTINGS, APIConfig
from data.models import NormalizedContent, ContentScores

logger = logging.getLogger(__name__)

@dataclass
class DimensionScores:
    """Individual dimension scores"""
    provenance: float
    verification: float
    transparency: float
    coherence: float
    resonance: float

class ContentScorer:
    """Scores content on 5D Trust Dimensions"""
    
    def __init__(self):
        # Use the new OpenAI client (openai>=1.0.0)
        # If API key is None or empty, the client will fall back to environment variables.
        self.client = OpenAI(api_key=APIConfig.openai_api_key)
        self.rubric_version = SETTINGS['rubric_version']
    
    def score_content(self, content: NormalizedContent, brand_context: Dict[str, Any]) -> DimensionScores:
        """
        Score content on all 5 dimensions
        
        Args:
            content: Content to score
            brand_context: Brand-specific context and keywords
        """
        logger.debug(f"Scoring content {content.content_id}")
        
        try:
            # Get LLM scores for each dimension
            provenance_score = self._score_provenance(content, brand_context)
            verification_score = self._score_verification(content, brand_context)
            transparency_score = self._score_transparency(content, brand_context)
            coherence_score = self._score_coherence(content, brand_context)
            resonance_score = self._score_resonance(content, brand_context)
            
            return DimensionScores(
                provenance=provenance_score,
                verification=verification_score,
                transparency=transparency_score,
                coherence=coherence_score,
                resonance=resonance_score
            )
            
        except Exception as e:
            logger.error(f"Error scoring content {content.content_id}: {e}")
            # Return neutral scores on error
            return DimensionScores(0.5, 0.5, 0.5, 0.5, 0.5)
    
    def _score_provenance(self, content: NormalizedContent, brand_context: Dict[str, Any]) -> float:
        """Score Provenance dimension: origin, traceability, metadata"""
        
        prompt = f"""
        Score the PROVENANCE of this content on a scale of 0.0 to 1.0.
        
        Provenance evaluates: origin clarity, traceability, metadata completeness
        
        Content:
        Title: {content.title}
        Body: {content.body}
        Author: {content.author}
        Source: {content.src}
        Platform ID: {content.platform_id}
        
        Brand Context: {brand_context.get('keywords', [])}
        
        Scoring criteria:
        - 0.8-1.0: Clear origin, verifiable author, complete metadata
        - 0.6-0.8: Good origin info, some metadata present
        - 0.4-0.6: Basic origin info, limited metadata
        - 0.2-0.4: Unclear origin, minimal metadata
        - 0.0-0.2: No clear origin, no verifiable metadata
        
        Return only a number between 0.0 and 1.0:
        """
        
        return self._get_llm_score(prompt)
    
    def _score_verification(self, content: NormalizedContent, brand_context: Dict[str, Any]) -> float:
        """Score Verification dimension: factual accuracy vs trusted DBs"""
        
        prompt = f"""
        Score the VERIFICATION of this content on a scale of 0.0 to 1.0.
        
        Verification evaluates: factual accuracy, consistency with known facts
        
        Content:
        Title: {content.title}
        Body: {content.body}
        
        Brand Context: {brand_context.get('keywords', [])}
        
        Scoring criteria:
        - 0.8-1.0: Highly verifiable facts, consistent with known information
        - 0.6-0.8: Mostly accurate, minor inconsistencies
        - 0.4-0.6: Some accurate info, some questionable claims
        - 0.2-0.4: Several inaccuracies or unverifiable claims
        - 0.0-0.2: Major inaccuracies or completely unverifiable
        
        Return only a number between 0.0 and 1.0:
        """
        
        return self._get_llm_score(prompt)
    
    def _score_transparency(self, content: NormalizedContent, brand_context: Dict[str, Any]) -> float:
        """Score Transparency dimension: disclosures, clarity"""
        
        prompt = f"""
        Score the TRANSPARENCY of this content on a scale of 0.0 to 1.0.
        
        Transparency evaluates: clear disclosures, honest communication, no hidden agendas
        
        Content:
        Title: {content.title}
        Body: {content.body}
        Author: {content.author}
        
        Scoring criteria:
        - 0.8-1.0: Clear disclosures, honest communication, transparent intent
        - 0.6-0.8: Mostly transparent, minor omissions
        - 0.4-0.6: Some transparency, some unclear aspects
        - 0.2-0.4: Limited transparency, hidden elements
        - 0.0-0.2: No transparency, deceptive or manipulative
        
        Return only a number between 0.0 and 1.0:
        """
        
        return self._get_llm_score(prompt)
    
    def _score_coherence(self, content: NormalizedContent, brand_context: Dict[str, Any]) -> float:
        """Score Coherence dimension: consistency across channels"""
        
        prompt = f"""
        Score the COHERENCE of this content on a scale of 0.0 to 1.0.
        
        Coherence evaluates: consistency with brand messaging, logical flow, professional quality
        
        Content:
        Title: {content.title}
        Body: {content.body}
        Source: {content.src}
        
        Brand Context: {brand_context.get('keywords', [])}
        
        Scoring criteria:
        - 0.8-1.0: Highly coherent, consistent with brand, professional quality
        - 0.6-0.8: Mostly coherent, good consistency
        - 0.4-0.6: Some coherence, minor inconsistencies
        - 0.2-0.4: Limited coherence, noticeable inconsistencies
        - 0.0-0.2: Incoherent, inconsistent, unprofessional
        
        Return only a number between 0.0 and 1.0:
        """
        
        return self._get_llm_score(prompt)
    
    def _score_resonance(self, content: NormalizedContent, brand_context: Dict[str, Any]) -> float:
        """Score Resonance dimension: cultural fit, organic engagement"""
        
        # Use engagement metrics for resonance scoring
        engagement_score = self._calculate_engagement_resonance(content)
        
        prompt = f"""
        Score the RESONANCE of this content on a scale of 0.0 to 1.0.
        
        Resonance evaluates: cultural fit, authentic engagement, organic appeal
        
        Content:
        Title: {content.title}
        Body: {content.body}
        
        Engagement Metrics:
        Rating: {content.rating}
        Upvotes: {content.upvotes}
        Helpful Count: {content.helpful_count}
        
        Brand Context: {brand_context.get('keywords', [])}
        
        Scoring criteria:
        - 0.8-1.0: High cultural fit, strong organic engagement
        - 0.6-0.8: Good resonance, positive engagement
        - 0.4-0.6: Moderate resonance, mixed engagement
        - 0.2-0.4: Low resonance, limited engagement
        - 0.0-0.2: No resonance, negative or artificial engagement
        
        Return only a number between 0.0 and 1.0:
        """
        
        llm_score = self._get_llm_score(prompt)
        
        # Combine LLM score with engagement metrics (70% LLM, 30% engagement)
        combined_score = (0.7 * llm_score) + (0.3 * engagement_score)
        
        return min(1.0, max(0.0, combined_score))
    
    def _calculate_engagement_resonance(self, content: NormalizedContent) -> float:
        """Calculate engagement-based resonance score"""
        score = 0.5  # Default neutral score
        
        # Rating-based scoring (0-1 scale)
        if content.rating is not None:
            if content.src == "amazon":
                # Amazon ratings are 1-5, convert to 0-1
                score += (content.rating - 3) * 0.1
            elif content.src == "reddit":
                # Reddit upvote ratio is 0-1, use directly
                score += (content.rating - 0.5) * 0.2
        
        # Upvotes-based scoring
        if content.upvotes is not None:
            # Normalize upvotes (log scale to prevent outliers from dominating)
            import math
            normalized_upvotes = math.log10(max(1, content.upvotes)) / 3  # Log base 10, max ~3
            score += normalized_upvotes * 0.1
        
        # Helpful count scoring (Amazon reviews)
        if content.helpful_count is not None:
            normalized_helpful = min(content.helpful_count / 20, 1.0)  # Cap at 20 helpful votes
            score += normalized_helpful * 0.1
        
        return min(1.0, max(0.0, score))
    
    def _get_llm_score(self, prompt: str) -> float:
        """Get score from LLM API"""
        try:
            # New API: client.chat.completions.create(...)
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are an expert content authenticity evaluator. Always respond with only a number between 0.0 and 1.0."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=10,
                temperature=0.1
            )

            # The new response shape still exposes choices with a message
            # Attempt to read the content defensively
            try:
                score_text = response.choices[0].message.content.strip()
            except Exception:
                # Fallback to dict-like access if needed
                score_text = str(response.choices[0].message.get('content', '')).strip()

            score = float(score_text)
            
            # Ensure score is in valid range
            return min(1.0, max(0.0, score))
            
        except Exception as e:
            logger.error(f"LLM scoring error: {e}")
            return 0.5  # Return neutral score on error
    
    def batch_score_content(self, content_list: List[NormalizedContent], 
                          brand_context: Dict[str, Any]) -> List[ContentScores]:
        """Score multiple content items in batch"""
        scores_list = []
        
        logger.info(f"Batch scoring {len(content_list)} content items")
        
        for i, content in enumerate(content_list):
            if i % 10 == 0:
                logger.info(f"Scoring progress: {i}/{len(content_list)}")
            
            # Score the content
            dimension_scores = self.score_content(content, brand_context)
            
            # Create ContentScores object
            content_scores = ContentScores(
                content_id=content.content_id,
                brand=brand_context.get('brand_name', 'unknown'),
                src=content.src,
                event_ts=content.event_ts,
                score_provenance=dimension_scores.provenance,
                score_resonance=dimension_scores.resonance,
                score_coherence=dimension_scores.coherence,
                score_transparency=dimension_scores.transparency,
                score_verification=dimension_scores.verification,
                class_label="pending",  # Will be set by classifier
                is_authentic=False,     # Will be set by classifier
                rubric_version=self.rubric_version,
                run_id=content.run_id,
                meta=json.dumps({
                    "scoring_timestamp": content.event_ts,
                    "brand_context": brand_context
                })
            )
            
            scores_list.append(content_scores)
        
        logger.info(f"Completed batch scoring: {len(scores_list)} items scored")
        return scores_list
