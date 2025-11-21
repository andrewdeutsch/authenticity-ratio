
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

def test_score_transparency():
    print("Testing Score Transparency...")
    
    # Mock dependencies
    with patch('scoring.scorer.LLMScoringClient') as MockLLM, \
         patch('scoring.scorer.VerificationManager') as MockVerifier, \
         patch('scoring.scorer.LinguisticAnalyzer') as MockLinguistic:
        
        # Setup mocks
        mock_llm = MockLLM.return_value
        # Return 0.5 for all scores
        mock_llm.get_score.return_value = 0.5
        mock_llm.get_score_with_reasoning.return_value = {'score': 0.5, 'issues': []}
        mock_llm.get_score_with_feedback.return_value = {'score': 0.5, 'issues': []}
        
        mock_verifier = MockVerifier.return_value
        mock_verifier.verify_content.return_value = {'score': 0.5, 'issues': []}
        
        mock_linguistic = MockLinguistic.return_value
        mock_linguistic.analyze.return_value = {'passive_voice': [], 'readability': {}}
        
        # Initialize scorer
        scorer = ContentScorer(use_attribute_detection=False)
        
        # Create test content (Landing Page)
        content = NormalizedContent(
            content_id="test_1",
            src="web",
            platform_id="test",
            author="Test Brand",
            title="Test Product Landing Page",
            body="Buy our amazing product. It is the best.",
            url="https://example.com/product/amazing-thing" # Should trigger landing_page type
        )
        
        brand_context = {'keywords': ['test'], 'brand_name': 'Test Brand'}
        
        # Run scoring
        scores = scorer.score_content(content, brand_context)
        
        # Verify Coherence Multiplier (Landing Page = 1.25)
        # Base 0.5 * 1.25 = 0.625
        print(f"\nCoherence Score: {scores.coherence:.3f}")
        if abs(scores.coherence - 0.625) < 0.001:
            print("✅ Coherence multiplier applied correctly (0.5 * 1.25 = 0.625)")
        else:
            print(f"❌ Coherence multiplier failed. Expected 0.625, got {scores.coherence}")
            
        # Verify Verification Multiplier (Landing Page = 1.30)
        # Base 0.5 * 1.30 = 0.65
        print(f"Verification Score: {scores.verification:.3f}")
        if abs(scores.verification - 0.65) < 0.001:
            print("✅ Verification multiplier applied correctly (0.5 * 1.30 = 0.65)")
        else:
            print(f"❌ Verification multiplier failed. Expected 0.65, got {scores.verification}")
            
        # Verify Metadata Logging
        print(f"\nMetadata: {content.meta}")
        
        if 'score_debug' in content.meta:
            debug_info = json.loads(content.meta['score_debug'])
            print(f"Debug Info: {json.dumps(debug_info, indent=2)}")
            
            # Check Coherence Debug
            coh_debug = debug_info.get('coherence', {})
            if coh_debug.get('base_score') == 0.5 and coh_debug.get('multiplier') == 1.25:
                print("✅ Coherence debug info correct")
            else:
                print("❌ Coherence debug info incorrect")
                
            # Check Verification Debug
            ver_debug = debug_info.get('verification', {})
            if ver_debug.get('base_score') == 0.5 and ver_debug.get('multiplier') == 1.30:
                print("✅ Verification debug info correct")
            else:
                print("❌ Verification debug info incorrect")
        else:
            print("❌ score_debug missing from metadata")

if __name__ == "__main__":
    test_score_transparency()
