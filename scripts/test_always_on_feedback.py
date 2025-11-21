
import unittest
from unittest.mock import MagicMock, patch
import sys
import os
import json

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scoring.scoring_llm_client import LLMScoringClient
from data.models import NormalizedContent

class TestAlwaysOnFeedback(unittest.TestCase):
    def setUp(self):
        self.client = LLMScoringClient()
        self.content = NormalizedContent(
            content_id="test_1",
            body="This is excellent content that perfectly aligns with the brand voice.",
            title="Perfect Content",
            src="web",
            event_ts="2023-01-01"
        )

    @patch('scoring.scoring_llm_client.OpenAI')
    def test_high_score_feedback(self, mock_openai):
        """Test that a score >= 0.95 still requests and returns feedback"""
        
        # Mock the OpenAI client and response
        mock_instance = mock_openai.return_value
        mock_completion = MagicMock()
        
        # Setup the mock to return a high score first, then the feedback
        # The client makes two calls: one for score, one for feedback
        
        # We need to mock the create method to return different values based on the prompt or call order
        # But since we are mocking the *client instance* inside the class, it's easier to just mock the 
        # internal methods if we were testing the flow, but here we want to test the prompt construction 
        # and response handling.
        
        # Let's mock the response for the feedback call specifically.
        # The get_score_with_feedback method calls get_score first.
        
        with patch.object(self.client, 'get_score', return_value=0.98) as mock_get_score:
            # Mock the feedback response
            feedback_response = {
                "issues": [
                    {
                        "type": "improvement_opportunity",
                        "confidence": 0.6,
                        "severity": "low",
                        "evidence": "EXACT QUOTE: 'perfectly aligns'",
                        "suggestion": "Change 'perfectly aligns' -> 'seamlessly integrates'. This is a minor optimization."
                    }
                ]
            }
            
            mock_message = MagicMock()
            mock_message.content = json.dumps(feedback_response)
            mock_choice = MagicMock()
            mock_choice.message = mock_message
            mock_completion.choices = [mock_choice]
            
            mock_instance.chat.completions.create.return_value = mock_completion
            
            # Run the method
            result = self.client.get_score_with_feedback(
                score_prompt="Score this",
                content=self.content,
                dimension="Coherence"
            )
            
            # Verify score is high
            self.assertEqual(result['score'], 0.98)
            
            # Verify we got issues back
            self.assertTrue(len(result['issues']) > 0)
            self.assertEqual(result['issues'][0]['type'], 'improvement_opportunity')
            
            # Verify the prompt contained the new instruction
            # Get the call args for the feedback call (which is the only call to chat.completions.create since we mocked get_score)
            call_args = mock_instance.chat.completions.create.call_args
            self.assertIsNotNone(call_args)
            
            messages = call_args[1]['messages']
            user_prompt = messages[1]['content']
            
            # Check for key phrases from the new prompt
            self.assertIn("Even excellent content can be optimized", user_prompt)
            self.assertIn("Provide exactly ONE optimization tip", user_prompt)
            self.assertIn("improvement_opportunity", user_prompt)

if __name__ == '__main__':
    unittest.main()
