
import logging
import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from scoring.scorer import ContentScorer
from data.models import NormalizedContent

# Configure logging
logging.basicConfig(level=logging.INFO)

def test_hybrid_scoring():
    print("Initializing Scorer...")
    scorer = ContentScorer()
    
    # Create sample content with:
    # 1. A verifiable claim (inflation rate)
    # 2. A false claim (made up stat)
    # 3. Passive voice ("Mistakes were made")
    content = NormalizedContent(
        content_id="test_123",
        title="Test Article on Economics",
        body="""
        The US inflation rate dropped to 3.2% in late 2023. 
        However, mistakes were made by the central bank. 
        We are the only company in the world that offers 150% returns on savings.
        The decision was taken to raise rates.
        """,
        url="https://example.com/economy",
        src="web",
        platform_id="example.com",
        author="Test Author"
    )
    
    brand_context = {
        "keywords": ["finance", "economics"],
        "brand_name": "TestBrand"
    }
    
    print("\nScoring Content...")
    scores = scorer.score_content(content, brand_context)
    
    print("\n--- SCORES ---")
    print(f"Verification: {scores.verification:.2f}")
    print(f"Coherence: {scores.coherence:.2f}")
    
    print("\n--- ISSUES (Internal) ---")
    if hasattr(content, '_llm_issues'):
        for dim, issues in content._llm_issues.items():
            print(f"\nDimension: {dim}")
            for issue in issues:
                print(f"- {issue.get('type')}: {issue.get('evidence')}")
                if 'suggestion' in issue:
                    print(f"  Suggestion: {issue['suggestion']}")

if __name__ == "__main__":
    test_hybrid_scoring()
