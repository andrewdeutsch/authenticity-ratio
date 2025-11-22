#!/usr/bin/env python3
"""
Quick test to verify coherence issue remedies are now displayed
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from webapp.utils.recommendations import get_remedy_for_issue

def test_coherence_remedies():
    """Test that coherence issues now show remedies"""
    
    print("Testing Coherence Issue Remedies...")
    print("=" * 80)
    
    # Test 1: Inconsistent Voice with general guidance (no concrete rewrite)
    print("\n1. Testing 'Inconsistent Voice' with general guidance:")
    print("-" * 80)
    
    issue_items = [
        {
            'suggestion': 'Maintain consistent brand voice across all content. The tone varies between formal and casual.',
            'url': 'http://example.com/page1',
            'title': 'About Us Page',
            'evidence': 'Voice inconsistency detected',
            'confidence': 0.85,
            'issue': 'Inconsistent Voice'
        }
    ]
    
    remedy = get_remedy_for_issue('Inconsistent Voice', 'coherence', issue_items)
    print(remedy)
    
    # Check that both the LLM suggestion AND the predefined remedy are shown
    if remedy and 'Maintain consistent brand voice' in remedy and 'General Best Practice' in remedy:
        print("\n✅ PASS: Remedy displayed for general guidance")
    else:
        print("\n❌ FAIL: No remedy or wrong remedy")
        return False
    
    # Test 2: Tone Shift with predefined remedy
    print("\n\n2. Testing 'Tone Shift' predefined remedy:")
    print("-" * 80)
    
    remedy = get_remedy_for_issue('Tone Shift', 'coherence', issue_items=[])
    print(remedy)
    
    if remedy and 'Review content for abrupt changes in tone' in remedy:
        print("\n✅ PASS: Predefined remedy displayed")
    else:
        print("\n❌ FAIL: No predefined remedy")
        return False
    
    # Test 3: Issue with concrete rewrite (should still work)
    print("\n\n3. Testing issue with concrete rewrite (should still work):")
    print("-" * 80)
    
    issue_items = [
        {
            'suggestion': "Change 'click here' → 'learn more about our services'",
            'url': 'http://example.com/page2',
            'title': 'Services Page',
            'evidence': "EXACT QUOTE: 'click here'",
            'confidence': 0.9,
            'issue': 'Brand Voice Consistency Score'
        }
    ]
    
    remedy = get_remedy_for_issue('Brand Voice Consistency Score', 'coherence', issue_items)
    print(remedy)
    
    if remedy and "Change 'click here'" in remedy:
        print("\n✅ PASS: Concrete rewrite still works")
    else:
        print("\n❌ FAIL: Concrete rewrite broken")
        return False
    
    print("\n" + "=" * 80)
    print("✅ ALL TESTS PASSED!")
    return True

if __name__ == '__main__':
    success = test_coherence_remedies()
    sys.exit(0 if success else 1)
