#!/usr/bin/env python3
"""
Test script to verify Always-On Feedback implementation
Ensures high-scoring content (>= 0.95) receives optimization tips
"""

import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scoring.scoring_llm_client import LLMScoringClient
from data.models import NormalizedContent

def test_high_score_prompt():
    """Verify that the prompt for high scores requests optimization tips"""
    
    print("Testing Always-On Feedback...")
    print("\n--- Verifying Prompt Content ---")
    
    # Read the source code to verify the prompt
    client_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'scoring',
        'scoring_llm_client.py'
    )
    
    with open(client_path, 'r') as f:
        source_code = f.read()
    
    # Check for the new prompt language
    checks = [
        ("Even excellent content can be optimized", "Optimization mindset"),
        ("Provide exactly ONE optimization tip", "Mandatory tip requirement"),
        ("improvement_opportunity", "Correct issue type"),
        ("Change 'X' → 'Y'", "Concrete rewrite format")
    ]
    
    all_passed = True
    for phrase, description in checks:
        if phrase in source_code:
            print(f"✅ Found: {description}")
        else:
            print(f"❌ Missing: {description} ('{phrase}')")
            all_passed = False
    
    # Verify the old "OPTIONAL" language is removed
    if "Suggestions are OPTIONAL" in source_code:
        print("❌ Old 'OPTIONAL' language still present")
        all_passed = False
    else:
        print("✅ Old 'OPTIONAL' language removed")
    
    print("\n--- Summary ---")
    if all_passed:
        print("✅ All checks passed! Always-On Feedback is implemented correctly.")
        return 0
    else:
        print("❌ Some checks failed. Review the implementation.")
        return 1

if __name__ == '__main__':
    exit(test_high_score_prompt())
