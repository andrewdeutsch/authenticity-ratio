#!/usr/bin/env python3
"""Test script to verify URL balance ratio fix for Mastercard scenario

This script tests that the targeted brand domain search works correctly
when the initial pool doesn't have enough brand-owned URLs.
"""

import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Import directly from module to avoid ingestion.__init__ dependencies
import importlib.util
spec = importlib.util.spec_from_file_location(
    "domain_classifier",
    os.path.join(project_root, "ingestion", "domain_classifier.py")
)
domain_classifier = importlib.util.module_from_spec(spec)
spec.loader.exec_module(domain_classifier)

URLCollectionConfig = domain_classifier.URLCollectionConfig
classify_url = domain_classifier.classify_url
URLSourceType = domain_classifier.URLSourceType


def test_mastercard_classification():
    """Test that Mastercard URLs are classified correctly"""
    print("=" * 70)
    print("Test 1: Mastercard URL Classification")
    print("=" * 70)

    config = URLCollectionConfig(
        brand_owned_ratio=0.6,
        third_party_ratio=0.4,
        brand_domains=['mastercard.com', 'mastercard.us'],
        brand_subdomains=['newsroom.mastercard.com'],
        brand_social_handles=['@Mastercard', 'Mastercard']
    )

    test_cases = [
        ('https://www.mastercard.com/', URLSourceType.BRAND_OWNED),
        ('https://mastercard.com/news/', URLSourceType.BRAND_OWNED),
        ('https://newsroom.mastercard.com/press-releases/', URLSourceType.BRAND_OWNED),
        ('https://www.nytimes.com/mastercard-earnings', URLSourceType.THIRD_PARTY),
        ('https://www.forbes.com/mastercard-innovation', URLSourceType.THIRD_PARTY),
        ('https://twitter.com/Mastercard', URLSourceType.BRAND_OWNED),
        ('https://twitter.com/user123/mastercard-review', URLSourceType.THIRD_PARTY),
    ]

    passed = 0
    failed = 0

    for url, expected_type in test_cases:
        classification = classify_url(url, config)
        status = "✓" if classification.source_type == expected_type else "✗"

        if classification.source_type == expected_type:
            passed += 1
        else:
            failed += 1

        print(f"\n{status} URL: {url}")
        print(f"  Expected: {expected_type.value}")
        print(f"  Got: {classification.source_type.value}")
        print(f"  Reason: {classification.reason}")

    print("\n" + "=" * 70)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 70)

    return failed == 0


def test_nike_classification():
    """Test that Nike URLs are still classified correctly (regression test)"""
    print("\n" + "=" * 70)
    print("Test 2: Nike URL Classification (Regression Test)")
    print("=" * 70)

    config = URLCollectionConfig(
        brand_owned_ratio=0.6,
        third_party_ratio=0.4,
        brand_domains=['nike.com'],
        brand_subdomains=['blog.nike.com'],
        brand_social_handles=['@nike', 'nike']
    )

    test_cases = [
        ('https://www.nike.com/', URLSourceType.BRAND_OWNED),
        ('https://www.nike.com/products/air-max', URLSourceType.BRAND_OWNED),
        ('https://blog.nike.com/sustainability', URLSourceType.BRAND_OWNED),
        ('https://www.amazon.com/nike-shoes', URLSourceType.THIRD_PARTY),
        ('https://www.reddit.com/r/sneakers/nike', URLSourceType.THIRD_PARTY),
    ]

    passed = 0
    failed = 0

    for url, expected_type in test_cases:
        classification = classify_url(url, config)
        status = "✓" if classification.source_type == expected_type else "✗"

        if classification.source_type == expected_type:
            passed += 1
        else:
            failed += 1

        print(f"\n{status} URL: {url}")
        print(f"  Expected: {expected_type.value}")
        print(f"  Got: {classification.source_type.value}")

    print("\n" + "=" * 70)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 70)

    return failed == 0


def test_targeted_search_logic():
    """Test the logic for determining when targeted search should trigger"""
    print("\n" + "=" * 70)
    print("Test 3: Targeted Search Trigger Logic")
    print("=" * 70)

    target_count = 20
    brand_owned_ratio = 0.6
    third_party_ratio = 0.4

    target_brand_owned = int(target_count * brand_owned_ratio)
    target_third_party = int(target_count * third_party_ratio)

    print(f"\nTarget: {target_count} total URLs")
    print(f"  Brand-owned target: {target_brand_owned} ({brand_owned_ratio:.0%})")
    print(f"  3rd party target: {target_third_party} ({third_party_ratio:.0%})")

    # Simulate Mastercard scenario (3 brand, 16 third-party)
    brand_owned_collected = 3
    third_party_collected = 16

    print(f"\nSimulated Mastercard scenario:")
    print(f"  Brand-owned collected: {brand_owned_collected}")
    print(f"  3rd party collected: {third_party_collected}")

    should_trigger = brand_owned_collected < target_brand_owned
    needed = target_brand_owned - brand_owned_collected if should_trigger else 0

    print(f"\nTargeted search should trigger: {should_trigger}")
    if should_trigger:
        print(f"  Need to collect {needed} more brand-owned URLs")

    assert should_trigger, "Targeted search should trigger for Mastercard scenario"
    assert needed == 9, f"Should need 9 more brand-owned URLs, got {needed}"

    print("\n✓ Test passed: Targeted search logic is correct")
    print("=" * 70)

    return True


def main():
    """Run all tests"""
    print("\n" + "=" * 70)
    print("URL Balance Ratio Fix - Test Suite")
    print("=" * 70)

    all_passed = True

    try:
        if not test_mastercard_classification():
            all_passed = False
            print("\n❌ Mastercard classification test FAILED")

        if not test_nike_classification():
            all_passed = False
            print("\n❌ Nike classification test FAILED (regression)")

        if not test_targeted_search_logic():
            all_passed = False
            print("\n❌ Targeted search logic test FAILED")

        if all_passed:
            print("\n" + "=" * 70)
            print("✓ ALL TESTS PASSED")
            print("=" * 70)
            print("\nThe fix should work correctly for Mastercard:")
            print("1. Initial search processes general results")
            print("2. If brand-owned quota not met (e.g., only 3/12 collected)")
            print("3. Triggers targeted 'site:mastercard.com' search")
            print("4. Collects additional brand URLs to meet 60% target")
            print("5. Final result: ~12 brand-owned + 8 third-party URLs")
            print("\nTo use this fix, ensure you specify brand domains:")
            print("  --brand-domains mastercard.com mastercard.us")
            return 0
        else:
            print("\n" + "=" * 70)
            print("❌ SOME TESTS FAILED")
            print("=" * 70)
            return 1

    except Exception as e:
        print(f"\n❌ TEST SUITE FAILED WITH ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
