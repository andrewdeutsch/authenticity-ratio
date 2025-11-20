"""
LLM Scoring Client for Trust Stack Rating Tool
Centralizes all OpenAI API interactions for content scoring
"""

from openai import OpenAI
from typing import Dict, Any
import logging
import json

from config.settings import APIConfig
from data.models import NormalizedContent

logger = logging.getLogger(__name__)


class LLMScoringClient:
    """
    Client for LLM-based content scoring
    Handles all OpenAI API interactions with different scoring patterns
    """
    
    def __init__(self, model: str = "gpt-3.5-turbo"):
        """
        Initialize LLM scoring client
        
        Args:
            model: OpenAI model to use (default: gpt-3.5-turbo)
        """
        self.client = OpenAI(api_key=APIConfig.openai_api_key)
        self.model = model
    
    def get_score(self, prompt: str) -> float:
        """
        Get a simple numeric score from LLM
        
        Args:
            prompt: Scoring prompt
        
        Returns:
            Score between 0.0 and 1.0
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert content authenticity evaluator. Always respond with only a number between 0.0 and 1.0."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=10,
                temperature=0.1
            )
            
            # Parse response
            try:
                score_text = response.choices[0].message.content.strip()
            except Exception:
                score_text = str(response.choices[0].message.get('content', '')).strip()
            
            score = float(score_text)
            
            # Ensure score is in valid range
            return min(1.0, max(0.0, score))
            
        except Exception as e:
            logger.error(f"LLM scoring error: {e}")
            return 0.5  # Return neutral score on error
    
    def get_score_with_reasoning(self, prompt: str) -> Dict[str, Any]:
        """
        Get score AND reasoning from LLM with structured JSON output
        
        Args:
            prompt: Scoring prompt that requests JSON response
        
        Returns:
            Dictionary with 'score' (float) and 'issues' (list of dicts)
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert content authenticity evaluator. Always respond with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            
            # Parse JSON response
            try:
                response_text = response.choices[0].message.content.strip()
                result = json.loads(response_text)
            except Exception:
                response_text = str(response.choices[0].message.get('content', '{}')).strip()
                result = json.loads(response_text)
            
            # Validate and normalize
            score = float(result.get('score', 0.5))
            score = min(1.0, max(0.0, score))
            
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
    
    def get_score_with_feedback(self, score_prompt: str, content: NormalizedContent,
                                dimension: str, context_guidance: str = "") -> Dict[str, Any]:
        """
        Two-step LLM scoring: Get score first, then get feedback based on score
        
        Args:
            score_prompt: Prompt to get the score (0.0-1.0)
            content: Content being scored
            dimension: Dimension name (for logging)
            context_guidance: Optional context about content type
        
        Returns:
            Dictionary with 'score' (float) and 'issues' (list of dicts)
        """
        # Step 1: Get the score
        score = self.get_score(score_prompt)
        logger.debug(f"{dimension} base score: {score:.2f}")
        
        # Step 2: Get feedback based on score
        if score < 0.9:
            # Low/medium score: Ask for specific issues with concrete rewrites
            feedback_prompt = f"""
            You scored this content's {dimension} as {score:.1f} out of 1.0.
            
            {context_guidance}
            
            What specific issues caused this lower score? Provide actionable feedback with CONCRETE REWRITES.
            
            Content:
            Title: {content.title}
            Body: {content.body[:2000]}
            
            Respond with JSON in this exact format:
            {{
                "issues": [
                    {{
                        "type": "issue_type",
                        "confidence": 0.85,
                        "severity": "high",
                        "evidence": "EXACT QUOTE: 'specific problematic text from content'",
                        "suggestion": "Change '[exact problematic text]' → '[improved version]'. This improves [dimension] because [brief explanation]."
                    }}
                ]
            }}
            
            CRITICAL REQUIREMENTS:
            1. Provide EXACT QUOTES in evidence field
            2. In suggestion field, show CONCRETE REWRITE using format: "Change 'X' → 'Y'"
            3. Include brief explanation of WHY the change improves {dimension}
            4. Only report issues you can support with specific text
            
            EXAMPLE GOOD SUGGESTION:
            "Change 'Find the right type of Mastercard payment card for you' → 'Discover the perfect Mastercard for your needs'. This improves coherence by using more consistent, engaging brand voice."
            
            EXAMPLE BAD SUGGESTION (DO NOT DO THIS):
            "Improve the wording" or "Make it more professional" (too vague, no concrete rewrite)
            """
        else:
            # High score: Ask for improvement suggestions with concrete rewrites
            # MANDATE at least one suggestion - users need to understand "why not 100%?"
            feedback_prompt = f"""
            You scored this content's {dimension} as {score:.1f} out of 1.0 - this is good!
            
            {context_guidance}
            
            The client wants to know: "Why didn't I get 100%? What specific thing could make this even better?"
            
            You MUST provide at least ONE specific, actionable improvement with a CONCRETE REWRITE that would move the score closer to 100%.
            
            Even excellent content can be refined through micro-optimizations, A/B testing opportunities, or advanced best practices.
            
            Content:
            Title: {content.title}
            Body: {content.body[:2000]}
            
            CRITICAL REQUIREMENTS:
            1. You MUST provide at least ONE improvement (empty array is NOT acceptable)
            2. Identify ONE specific area for improvement (not multiple)
            3. Provide a SINGLE exact quote showing what could be improved
            4. Show CONCRETE REWRITE using format: "Change 'X' → 'Y'"
            5. Explain WHY this change would improve the score
            
            Respond with JSON in this exact format:
            {{
                "issues": [
                    {{
                        "type": "improvement_opportunity",
                        "confidence": 0.75,
                        "severity": "low",
                        "evidence": "EXACT QUOTE: 'single specific text that could be improved'",
                        "suggestion": "Change '[exact text from evidence]' → '[improved version]'. This would improve {dimension} by [brief explanation]."
                    }}
                ]
            }}
            
            EXAMPLES OF GOOD SUGGESTIONS WITH CONCRETE REWRITES:
            - "Change 'Click here to learn more' → 'Explore our complete product guide'. This improves coherence by providing specific, descriptive CTAs."
            - "Change 'Posted recently' → 'Published on January 15, 2024'. This improves transparency by adding specific timestamps."
            - "Change 'Our product is the best' → 'Our product has been rated #1 by TechReview (2024)'. This improves verification by adding credible sources."
            
            EXAMPLES OF BAD SUGGESTIONS (DO NOT DO THIS):
            - "Add a call-to-action" (no concrete rewrite shown)
            - "Improve the wording" (too vague)
            - Listing multiple improvements instead of ONE concrete rewrite
            - Returning an empty issues array (NOT ALLOWED - you MUST provide at least one suggestion)
            
            REMEMBER: You MUST provide at least ONE improvement opportunity. Empty arrays are not acceptable for high scores.
            """
        
        # Get feedback from LLM
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert content evaluator. Always respond with valid JSON."},
                    {"role": "user", "content": feedback_prompt}
                ],
                max_tokens=500,
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            feedback_text = response.choices[0].message.content.strip()
            feedback_data = json.loads(feedback_text)
            
            return {
                'score': score,
                'issues': feedback_data.get('issues', [])
            }
            
        except Exception as e:
            logger.error(f"LLM feedback error for {dimension}: {e}")
            return {'score': score, 'issues': []}
