"""
5D Trust Dimensions scorer for Trust Stack Rating tool
Scores content on Provenance, Verification, Transparency, Coherence, Resonance
Integrates with TrustStackAttributeDetector for comprehensive ratings
"""

from openai import OpenAI
from typing import Dict, Any, List, Optional
import logging
import json
from dataclasses import dataclass

from config.settings import SETTINGS, APIConfig
from data.models import NormalizedContent, ContentScores, DetectedAttribute
from scoring.attribute_detector import TrustStackAttributeDetector

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
    """
    Scores content on 5D Trust Dimensions
    Combines LLM-based scoring with Trust Stack attribute detection
    """

    def __init__(self, use_attribute_detection: bool = True):
        """
        Initialize scorer

        Args:
            use_attribute_detection: If True, combine LLM scores with attribute detection
        """
        # Use the new OpenAI client (openai>=1.0.0)
        # If API key is None or empty, the client will fall back to environment variables.
        self.client = OpenAI(api_key=APIConfig.openai_api_key)
        self.rubric_version = SETTINGS['rubric_version']
        self.use_attribute_detection = use_attribute_detection

        # Initialize attribute detector if enabled
        if self.use_attribute_detection:
            try:
                self.attribute_detector = TrustStackAttributeDetector()
                logger.info(f"Attribute detector initialized with {len(self.attribute_detector.attributes)} attributes")
            except Exception as e:
                logger.warning(f"Could not initialize attribute detector: {e}. Falling back to LLM-only scoring.")
                self.use_attribute_detection = False
                self.attribute_detector = None
        else:
            self.attribute_detector = None
    
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
        Score the VERIFICATION of this content and identify specific issues.
        
        Verification evaluates: factual accuracy, consistency with known facts
        
        Content:
        Title: {content.title}
        Body: {content.body}
        
        Brand Context: {brand_context.get('keywords', [])}
        
        Respond with JSON in this exact format:
        {{
            "score": 0.5,
            "issues": [
                {{
                    "type": "unverified_claims",
                    "severity": "high",
                    "evidence": "Claims made without supporting evidence",
                    "suggestion": "Add citations to authoritative sources"
                }}
            ]
        }}
        
        Scoring criteria:
        - 0.8-1.0: Highly verifiable facts, consistent with known information
        - 0.6-0.8: Mostly accurate, minor inconsistencies
        - 0.4-0.6: Some accurate info, some questionable claims
        - 0.2-0.4: Several inaccuracies or unverifiable claims
        - 0.0-0.2: Major inaccuracies or completely unverifiable
        
        Common verification issues to check for:
        - Unverified claims without sources
        - Fake or suspicious engagement patterns
        - Unlabeled sponsored content
        - Missing fact-check references
        
        Return valid JSON with score (0.0-1.0) and issues array.
        """
        
        result = self._get_llm_score_with_reasoning(prompt)
        
        # Store LLM-identified issues in content metadata for later merging
        if not hasattr(content, '_llm_issues'):
            content._llm_issues = {}
        content._llm_issues['verification'] = result.get('issues', [])
        
        return result.get('score', 0.5)
    
    def _score_transparency(self, content: NormalizedContent, brand_context: Dict[str, Any]) -> float:
        """Score Transparency dimension: disclosures, clarity"""
        
        prompt = f"""
        Score the TRANSPARENCY of this content and identify specific issues.
        
        Transparency evaluates: clear disclosures, honest communication, no hidden agendas
        
        Content:
        Title: {content.title}
        Body: {content.body}
        Author: {content.author}
        
        Respond with JSON in this exact format:
        {{
            "score": 0.6,
            "issues": [
                {{
                    "type": "missing_privacy_policy",
                    "severity": "medium",
                    "evidence": "No privacy policy link found",
                    "suggestion": "Add privacy policy link to footer"
                }}
            ]
        }}
        
        Scoring criteria:
        - 0.8-1.0: Clear disclosures, honest communication, transparent intent
        - 0.6-0.8: Mostly transparent, minor omissions
        - 0.4-0.6: Some transparency, some unclear aspects
        - 0.2-0.4: Limited transparency, hidden elements
        - 0.0-0.2: No transparency, deceptive or manipulative
        
        Common transparency issues to check for:
        - Missing privacy policy links
        - Unclear AI-generated content disclosure
        - Missing data source citations
        - Hidden sponsored content
        
        Return valid JSON with score (0.0-1.0) and issues array.
        """
        
        result = self._get_llm_score_with_reasoning(prompt)
        
        # Store LLM-identified issues in content metadata for later merging
        if not hasattr(content, '_llm_issues'):
            content._llm_issues = {}
        content._llm_issues['transparency'] = result.get('issues', [])
        
        return result.get('score', 0.5)
    
    def _score_coherence(self, content: NormalizedContent, brand_context: Dict[str, Any]) -> float:
        """Score Coherence dimension: consistency across channels"""
        
        prompt = f"""
        Score the COHERENCE of this content and identify ALL specific issues.
        
        Coherence evaluates: consistency with brand messaging, logical flow, professional quality
        
        Content:
        Title: {content.title}
        Body: {content.body}
        Source: {content.src}
        
        Brand Context: {brand_context.get('keywords', [])}
        
        Respond with JSON in this exact format:
        {{
            "score": 0.6,
            "issues": [
                {{
                    "type": "inconsistent_voice",
                    "severity": "medium",
                    "evidence": "Tone shifts from formal to casual",
                    "suggestion": "Maintain consistent brand voice throughout"
                }},
                {{
                    "type": "broken_links",
                    "severity": "high",
                    "evidence": "Found 3 broken links in content",
                    "suggestion": "Update or remove broken links"
                }}
            ]
        }}
        
        Scoring criteria:
        - 0.8-1.0: Highly coherent, consistent with brand, professional quality
        - 0.6-0.8: Mostly coherent, good consistency
        - 0.4-0.6: Some coherence, minor inconsistencies
        - 0.2-0.4: Limited coherence, noticeable inconsistencies
        - 0.0-0.2: Incoherent, inconsistent, unprofessional
        
        IMPORTANT: Check for ALL of these specific coherence issues and report each one found:
        
        1. **Brand Voice Issues**:
           - "inconsistent_voice" or "brand_voice_inconsistency": Tone/style inconsistencies
        
        2. **Link Quality**:
           - "broken_links" or "outdated_links": Non-functional or outdated URLs
        
        3. **Claim Consistency**:
           - "contradictory_claims" or "inconsistent_claims": Conflicting information
        
        4. **Cross-Channel Issues**:
           - "email_inconsistency" or "cross_channel_mismatch": Email vs web inconsistencies
        
        5. **Engagement-Trust Alignment**:
           - "engagement_trust_mismatch" or "low_engagement_high_trust": Suspicious engagement patterns
        
        6. **Multimodal Consistency**:
           - "multimodal_inconsistency" or "text_image_mismatch": Text doesn't match images/media
        
        7. **Version/Update Issues**:
           - "version_inconsistency" or "outdated_content": Old or conflicting versions
        
        8. **Trust Signal Fluctuation**:
           - "trust_fluctuation" or "inconsistent_trust_signals": Varying trust indicators
        
        Return valid JSON with score (0.0-1.0) and issues array. Report EVERY issue you find, even if minor.
        """
        
        result = self._get_llm_score_with_reasoning(prompt)
        
        # Store LLM-identified issues in content metadata for later merging
        if not hasattr(content, '_llm_issues'):
            content._llm_issues = {}
        content._llm_issues['coherence'] = result.get('issues', [])
        
        return result.get('score', 0.5)
    
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

    def _adjust_scores_with_attributes(self, llm_scores: DimensionScores,
                                      detected_attrs: List[DetectedAttribute]) -> DimensionScores:
        """
        Adjust LLM-based dimension scores using detected Trust Stack attributes

        Args:
            llm_scores: Base scores from LLM (0.0-1.0 scale)
            detected_attrs: List of detected attributes from TrustStackAttributeDetector

        Returns:
            Adjusted dimension scores (0.0-1.0 scale)
        """
        # Start with LLM scores (convert to 0-100 for adjustment calculation)
        adjusted = {
            'provenance': llm_scores.provenance * 100,
            'resonance': llm_scores.resonance * 100,
            'coherence': llm_scores.coherence * 100,
            'transparency': llm_scores.transparency * 100,
            'verification': llm_scores.verification * 100
        }

        # Group attributes by dimension
        attrs_by_dimension = {}
        for attr in detected_attrs:
            if attr.dimension not in attrs_by_dimension:
                attrs_by_dimension[attr.dimension] = []
            attrs_by_dimension[attr.dimension].append(attr)

        # Adjust each dimension based on its detected attributes
        for dimension, attrs in attrs_by_dimension.items():
            if dimension not in adjusted:
                continue

            # Calculate adjustment from attributes (1-10 scale → adjustment)
            # Strategy: Blend attribute signals with LLM baseline
            # Attributes with high confidence and extreme values have more impact
            total_adjustment = 0.0
            total_weight = 0.0

            for attr in attrs:
                # Map 1-10 scale to adjustment (-50 to +50)
                # 1 = -45, 5.5 = 0, 10 = +45
                attr_adjustment = (attr.value - 5.5) * 9

                # Weight by confidence
                weight = attr.confidence
                total_adjustment += attr_adjustment * weight
                total_weight += weight

            if total_weight > 0:
                # Average weighted adjustment
                avg_adjustment = total_adjustment / total_weight

                # Apply adjustment with dampening (70% LLM, 30% attributes)
                # This ensures LLM baseline is respected while attributes provide nuance
                adjusted[dimension] = (
                    0.7 * adjusted[dimension] +
                    0.3 * max(0, min(100, adjusted[dimension] + avg_adjustment))
                )

                # Clamp to valid range
                adjusted[dimension] = max(0, min(100, adjusted[dimension]))

        # Convert back to 0.0-1.0 scale
        return DimensionScores(
            provenance=adjusted['provenance'] / 100,
            resonance=adjusted['resonance'] / 100,
            coherence=adjusted['coherence'] / 100,
            transparency=adjusted['transparency'] / 100,
            verification=adjusted['verification'] / 100
        )
    
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
    
    def _get_llm_score_with_reasoning(self, prompt: str) -> Dict[str, Any]:
        """
        Get score AND reasoning from LLM API with structured JSON output
        
        Returns:
            Dictionary with 'score' (float) and 'issues' (list of dicts)
        """
        try:
            # Request structured JSON output from LLM
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are an expert content authenticity evaluator. Always respond with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.1,
                response_format={"type": "json_object"}  # Force JSON output
            )

            # Parse JSON response
            try:
                response_text = response.choices[0].message.content.strip()
                result = json.loads(response_text)
            except Exception:
                # Fallback to dict-like access if needed
                response_text = str(response.choices[0].message.get('content', '{}')).strip()
                result = json.loads(response_text)

            # Validate and normalize the response
            score = float(result.get('score', 0.5))
            score = min(1.0, max(0.0, score))  # Clamp to valid range
            
            issues = result.get('issues', [])
            if not isinstance(issues, list):
                issues = []
            
            return {
                'score': score,
                'issues': issues
            }
            
        except Exception as e:
            logger.error(f"LLM structured scoring error: {e}")
            return {
                'score': 0.5,
                'issues': []
            }
    
    def _merge_llm_and_detector_issues(self, content: NormalizedContent, 
                                      detected_attrs: List[DetectedAttribute]) -> List[DetectedAttribute]:
        """
        Merge LLM-identified issues with detector-found attributes
        
        Args:
            content: Content object (may have _llm_issues attribute)
            detected_attrs: List of attributes detected by attribute detector
        
        Returns:
            Merged list of DetectedAttribute objects with source tracking
        """
        from scoring.issue_mapper import map_llm_issue_to_attribute
        
        merged_attrs = []
        
        # Track which attributes we've seen from the detector
        detector_attr_ids = {attr.attribute_id for attr in detected_attrs}
        
        # Add all detector-found attributes (mark as detector-only or both)
        for attr in detected_attrs:
            merged_attrs.append(attr)
        
        # Process LLM issues if they exist
        if hasattr(content, '_llm_issues'):
            for dimension, llm_issues in content._llm_issues.items():
                for llm_issue in llm_issues:
                    issue_type = llm_issue.get('type', '')
                    
                    # Map LLM issue type to attribute ID
                    attr_id = map_llm_issue_to_attribute(issue_type)
                    
                    if not attr_id:
                        # Log unmapped issues for debugging
                        logger.warning(f"Unmapped LLM issue type '{issue_type}' in {dimension} dimension for content {content.content_id}")
                        continue
                    
                    # Check if detector also found this issue
                    if attr_id in detector_attr_ids:
                        # Both found it - increase confidence of existing attribute
                        for attr in merged_attrs:
                            if attr.attribute_id == attr_id:
                                # Boost confidence when both LLM and detector agree
                                attr.confidence = min(1.0, attr.confidence * 1.2)
                                # Enhance evidence with LLM reasoning
                                llm_evidence = llm_issue.get('evidence', '')
                                if llm_evidence and llm_evidence not in attr.evidence:
                                    attr.evidence = f"{attr.evidence} | LLM: {llm_evidence}"
                                break
                    else:
                        # Only LLM found it - create new attribute
                        # Get label from rubric or use issue type
                        label = llm_issue.get('type', '').replace('_', ' ').title()
                        
                        # Determine value based on severity
                        severity = llm_issue.get('severity', 'medium')
                        if severity == 'high':
                            value = 2.0
                        elif severity == 'medium':
                            value = 5.0
                        else:  # low
                            value = 7.0
                        
                        new_attr = DetectedAttribute(
                            attribute_id=attr_id,
                            dimension=dimension,
                            label=label,
                            value=value,
                            evidence=f"LLM: {llm_issue.get('evidence', 'Issue detected')}",
                            confidence=0.6  # Lowered from 0.7 for more LLM-only attributes
                        )
                        merged_attrs.append(new_attr)
                        detector_attr_ids.add(attr_id)
                        logger.info(f"Added LLM-only attribute '{label}' (value={value}) for {dimension} dimension")
        
        return merged_attrs
    
    def batch_score_content(self, content_list: List[NormalizedContent],
                          brand_context: Dict[str, Any]) -> List[ContentScores]:
        """
        Score multiple content items in batch
        Combines LLM scoring with Trust Stack attribute detection

        Args:
            content_list: List of content to score
            brand_context: Brand-specific context

        Returns:
            List of ContentScores with dimension ratings
        """
        scores_list = []

        logger.info(f"Batch scoring {len(content_list)} content items (attribute detection: {self.use_attribute_detection})")

        for i, content in enumerate(content_list):
            if i % 10 == 0:
                logger.info(f"Scoring progress: {i}/{len(content_list)}")

            # Step 1: Get base LLM scores
            dimension_scores = self.score_content(content, brand_context)

            # Step 2: Detect Trust Stack attributes (if enabled)
            detected_attrs = []
            if self.use_attribute_detection and self.attribute_detector:
                try:
                    detected_attrs = self.attribute_detector.detect_attributes(content)
                    logger.debug(f"Detected {len(detected_attrs)} attributes for {content.content_id}")

                    # Step 2.5: Merge LLM issues with detector attributes
                    detected_attrs = self._merge_llm_and_detector_issues(content, detected_attrs)
                    logger.debug(f"After merging: {len(detected_attrs)} total attributes")

                    # Adjust LLM scores with attribute signals
                    dimension_scores = self._adjust_scores_with_attributes(dimension_scores, detected_attrs)
                except Exception as e:
                    logger.warning(f"Attribute detection failed for {content.content_id}: {e}")

            # Step 3: Create ContentScores object
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
                class_label="",  # Optional - for backward compatibility
                is_authentic=False,  # Optional - for backward compatibility
                rubric_version=self.rubric_version,
                run_id=content.run_id,
                # Enhanced Trust Stack fields
                modality=getattr(content, 'modality', 'text'),
                channel=getattr(content, 'channel', 'unknown'),
                platform_type=getattr(content, 'platform_type', 'unknown'),
                meta=json.dumps(
                    # Build a meta dict that includes scoring info and detected attributes
                    (lambda cm: {
                        "scoring_timestamp": content.event_ts,
                        "brand_context": brand_context,
                        "title": getattr(content, 'title', '') or None,
                        "description": getattr(content, 'body', '') or None,
                        "source_url": (cm.get('source_url') if isinstance(cm, dict) else None) or getattr(content, 'platform_id', None),
                        # Enhanced Trust Stack metadata
                        "modality": getattr(content, 'modality', 'text'),
                        "channel": getattr(content, 'channel', 'unknown'),
                        "platform_type": getattr(content, 'platform_type', 'unknown'),
                        "url": getattr(content, 'url', ''),
                        # Include detected attributes for downstream analysis
                        "detected_attributes": [
                            {
                                "id": attr.attribute_id,
                                "dimension": attr.dimension,
                                "label": attr.label,
                                "value": attr.value,
                                "evidence": attr.evidence,
                                "confidence": attr.confidence
                            }
                            for attr in detected_attrs
                        ] if detected_attrs else [],
                        "attribute_count": len(detected_attrs),
                        # preserve any existing content.meta under orig_meta
                        "orig_meta": cm if isinstance(cm, dict) else None,
                        # propagate explicit footer links if present so downstream reporting can use them
                        **({
                            'terms': cm.get('terms'),
                            'privacy': cm.get('privacy')
                        } if isinstance(cm, dict) and (cm.get('terms') or cm.get('privacy')) else {})
                    })(content.meta if hasattr(content, 'meta') else {})
                )
            )

            scores_list.append(content_scores)

        logger.info(f"Completed batch scoring: {len(scores_list)} items scored")
        return scores_list
