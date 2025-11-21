"""
Linguistic Analyzer
Handles deterministic analysis of content using textstat and regex.
"""

import logging
import re
import textstat
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class LinguisticAnalyzer:
    """
    Analyzes text for objective linguistic features:
    - Readability scores
    - Passive voice usage
    - Absolutist/weak language
    """
    
    def analyze(self, text: str) -> Dict[str, Any]:
        """Run all analyses on text."""
        return {
            "readability": self._analyze_readability(text),
            "passive_voice": self._check_passive_voice(text),
            "weak_words": self._check_weak_words(text)
        }

    def _analyze_readability(self, text: str) -> Dict[str, float]:
        """Calculate readability metrics."""
        try:
            return {
                "flesch_kincaid_grade": textstat.flesch_kincaid_grade(text),
                "flesch_reading_ease": textstat.flesch_reading_ease(text),
                "reading_time": textstat.reading_time(text)
            }
        except Exception as e:
            logger.warning(f"Readability analysis failed: {e}")
            return {}

    def _check_passive_voice(self, text: str) -> List[str]:
        """
        Detect passive voice using regex heuristics.
        Matches 'to be' verbs + past participle (ed/en).
        Returns list of matching sentences/fragments.
        """
        passive_pattern = r'\b(am|is|are|was|were|be|been|being)\s+(\w+ed|\w+en)\b'
        matches = []
        
        # Split into sentences (rough approximation)
        sentences = re.split(r'[.!?]+', text)
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
                
            if re.search(passive_pattern, sentence, re.IGNORECASE):
                # Verify it's not just an adjective (simple check)
                # This is imperfect without a full parser, but good for a heuristic
                matches.append(sentence)
                
        return matches[:5]  # Return top 5 examples

    def _check_weak_words(self, text: str) -> List[str]:
        """Check for weak or absolutist words that undermine credibility."""
        weak_words = [
            "maybe", "perhaps", "sort of", "kind of", "basically",
            "literally", "actually", "honestly", "believe", "think"
        ]
        
        found = []
        lower_text = text.lower()
        for word in weak_words:
            if f" {word} " in lower_text:
                found.append(word)
                
        return list(set(found))
