
import sys
import os
import json
import logging
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scoring.scorer import ContentScorer
from data.models import NormalizedContent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_triage():
    print("Testing Two-Stage Scoring (Triage)...")
    
    # Mock dependencies
    with patch('scoring.scorer.LLMScoringClient') as MockLLM, \
         patch('scoring.scorer.VerificationManager') as MockVerifier, \
         patch('scoring.scorer.LinguisticAnalyzer') as MockLinguistic, \
         patch.dict('config.settings.SETTINGS', {'triage_enabled': True}):
        
        # Setup mocks
        mock_llm = MockLLM.return_value
        mock_llm.get_score.return_value = 0.8
        mock_llm.get_score_with_reasoning.return_value = {'score': 0.8, 'issues': []}
        mock_llm.get_score_with_feedback.return_value = {'score': 0.8, 'issues': []}
        
        mock_verifier = MockVerifier.return_value
        mock_verifier.verify_content.return_value = {'score': 0.8, 'issues': []}
        
        mock_linguistic = MockLinguistic.return_value
        mock_linguistic.analyze.return_value = {'passive_voice': [], 'readability': {}}
        
        # Initialize scorer
        scorer = ContentScorer(use_attribute_detection=False)
        
        # Case 1: Short Content (Should Skip)
        short_content = NormalizedContent(
            content_id="short_1",
            src="web",
            platform_id="test",
            author="Test",
            title="Nav",
            body="Home About Contact", # Very short
            url="https://example.com"
        )
        
        print("\n--- Case 1: Short Content ---")
        scores_1 = scorer.score_content(short_content, {})
        meta_1 = short_content.meta
        
        if meta_1.get('triage_status') == 'skipped':
            print(f"✅ Correctly skipped short content. Reason: {meta_1.get('triage_reason')}")
            if scores_1.coherence == 0.5:
                 print("✅ Assigned default score 0.5")
            else:
                 print(f"❌ Wrong default score: {scores_1.coherence}")
        else:
            print(f"❌ Failed to skip short content. Status: {meta_1.get('triage_status')}")

        # Case 2: Login Page (Should Skip)
        login_content = NormalizedContent(
            content_id="login_1",
            src="web",
            platform_id="test",
            author="Test",
            title="Login to your account",
            body="Please enter your username and password to sign in.", # Short and functional
            url="https://example.com/login"
        )
        
        print("\n--- Case 2: Login Page ---")
        scores_2 = scorer.score_content(login_content, {})
        meta_2 = login_content.meta
        
        if meta_2.get('triage_status') == 'skipped':
            print(f"✅ Correctly skipped login page. Reason: {meta_2.get('triage_reason')}")
        else:
            print(f"❌ Failed to skip login page. Status: {meta_2.get('triage_status')}")

        # Case 3: Valid Content (Should Score)
        valid_content = NormalizedContent(
            content_id="valid_1",
            src="web",
            platform_id="test",
            author="Test",
            title="Detailed Product Review",
            body="This is a very long and detailed review of the product. " * 20, # Long enough
            url="https://example.com/review"
        )
        
        print("\n--- Case 3: Valid Content ---")
        scores_3 = scorer.score_content(valid_content, {})
        meta_3 = valid_content.meta
        
        if meta_3.get('triage_status') != 'skipped':
            print("✅ Correctly passed valid content to LLM scoring")
            # Check if LLM was actually called (score should be 0.8 from mock)
            # Note: Multipliers might apply, but base is 0.8
            if scores_3.coherence >= 0.8: 
                 print(f"✅ Scored with LLM (Score: {scores_3.coherence:.2f})")
            else:
                 print(f"❌ Unexpected score: {scores_3.coherence}")
        else:
            print(f"❌ Wrongly skipped valid content. Reason: {meta_3.get('triage_reason')}")

if __name__ == "__main__":
    test_triage()
