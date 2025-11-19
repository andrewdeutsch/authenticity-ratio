
import sys
import os
import json
import logging

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from webapp.utils.recommendations import extract_issues_from_items, get_remedy_for_issue
from scoring.attribute_detector import TrustStackAttributeDetector
from data.models import NormalizedContent

def test_remedy_generation():
    print("Testing Remedy Generation...")

    # Simulate an item with an issue from applied_rules (current behavior in pipeline.py)
    # Note: pipeline.py currently does NOT include 'label' in applied_rules, which is the bug.
    # But recommendations.py currently only looks at 'detected_attributes' in meta.
    
    # Scenario 1: Issue in applied_rules (simulating what pipeline.py produces)
    # We need to simulate what pipeline.py produces. 
# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_detectors_and_remedies():
    print("\nTesting Detectors and Remedy Generation...\n")
    
    detector = TrustStackAttributeDetector()
    
    # Test Case 1: Coherence - Brand Voice Consistency
    # Content with casual slang to trigger brand voice detector
    content_coherence = NormalizedContent(
        content_id="test_1",
        src="test_src",
        platform_id="test_platform",
        author="test_author",
        url="http://example.com/blog/post1",
        title="My Awesome Post",
        body="We are gonna launch this product soon. It's gonna be lit! lol.",
        channel="blog",
        platform_type="owned",
        source_type="brand_owned",
        meta={"broken_links": "0"}
    )
    
    print("--- Testing Coherence Detector (Brand Voice) ---")
    detected_coherence = detector.detect_attributes(content_coherence)
    brand_voice_attr = next((a for a in detected_coherence if a.attribute_id == "brand_voice_consistency_score"), None)
    
    if brand_voice_attr:
        print(f"✅ Detected: {brand_voice_attr.label}")
        print(f"   Value: {brand_voice_attr.value}")
        print(f"   Evidence: {brand_voice_attr.evidence}")
        
        # Simulate pipeline item structure
        item = {
            "meta": {
                "detected_attributes": [attr.__dict__ for attr in detected_coherence],
                "title": content_coherence.title,
                "url": content_coherence.url
            }
        }
        
        issues = extract_issues_from_items([item])
        coherence_issues = issues.get('coherence', [])
        
        if coherence_issues:
            print(f"✅ Extracted {len(coherence_issues)} coherence issues")
            first_issue = coherence_issues[0]
            remedy = get_remedy_for_issue(first_issue['issue'], 'coherence', [first_issue])
            print(f"✅ Remedy Generated: {remedy[:100]}...")
        else:
            print("❌ Failed to extract issues")
    else:
        print("❌ Failed to detect Brand Voice Consistency issue")

    # Test Case 2: Verification - Ad Label Consistency
    # Content with commercial intent but no ad label
    content_verification = NormalizedContent(
        content_id="test_2",
        src="test_src",
        platform_id="test_platform",
        author="test_author",
        url="http://example.com/promo",
        title="Special Offer",
        body="Buy now for a limited time offer! Click here for discount code.",
        channel="social_post",
        platform_type="social",
        source_type="influencer",
        meta={}
    )
    
    print("\n--- Testing Verification Detector (Ad Labels) ---")
    detected_verification = detector.detect_attributes(content_verification)
    ad_attr = next((a for a in detected_verification if a.attribute_id == "ad_sponsored_label_consistency"), None)
    
    if ad_attr:
        print(f"✅ Detected: {ad_attr.label}")
        print(f"   Value: {ad_attr.value}")
        print(f"   Evidence: {ad_attr.evidence}")
        
        # Simulate pipeline item structure
        item = {
            "meta": {
                "detected_attributes": [attr.__dict__ for attr in detected_verification],
                "title": content_verification.title,
                "url": content_verification.url
            }
        }
        
        issues = extract_issues_from_items([item])
        verification_issues = issues.get('verification', [])
        
        if verification_issues:
            print(f"✅ Extracted {len(verification_issues)} verification issues")
            first_issue = verification_issues[0]
            remedy = get_remedy_for_issue(first_issue['issue'], 'verification', [first_issue])
            print(f"✅ Remedy Generated: {remedy[:100]}...")
        else:
            print("❌ Failed to extract issues")
    else:
        print("❌ Failed to detect Ad Label Consistency issue")

if __name__ == "__main__":
    test_detectors_and_remedies()
