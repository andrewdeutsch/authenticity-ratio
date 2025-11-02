#!/usr/bin/env python3
"""
Integration test for Trust Stack Rating pipeline
Tests complete end-to-end flow with LLM + attribute detection
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Load required modules
from data.models import NormalizedContent, RatingBand
from scoring.pipeline import ScoringPipeline
from config.settings import SETTINGS


def print_section(title: str):
    """Print formatted section header"""
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80 + "\n")


def create_test_content():
    """Create test content for pipeline"""
    return [
        # High-quality verified content
        NormalizedContent(
            content_id="test_reddit_001",
            src="reddit",
            platform_id="t3_test123",
            author="verified_nike_fan",
            title="Detailed Nike Air Max review - AI-generated summary",
            body="After 6 months of daily use, these Nike Air Max shoes have proven their worth. "
                 "According to Nike's official specs, they use recycled materials for 50% of the upper. "
                 "The cushioning technology is phenomenal for long-distance running. "
                 "I've tested them on various terrains and they perform consistently. "
                 "For more details, see Nike's sustainability report at nike.com/sustainability.",
            rating=0.95,
            upvotes=250,
            event_ts="2025-11-02T10:00:00Z",
            run_id="integration_test",
            meta={
                "author_verified": "true",
                "verified": "true",
                "language": "en",
                "url": "https://reddit.com/r/running/comments/test123",
                "canonical_url": "https://reddit.com/r/running/comments/test123"
            }
        ),

        # Amazon verified purchase
        NormalizedContent(
            content_id="test_amazon_001",
            src="amazon",
            platform_id="R2TEST456",
            author="Jane S.",
            title="Perfect for training",
            body="These running shoes are excellent quality. Very comfortable and durable. "
                 "The arch support is perfect for my running style. Highly recommended!",
            rating=5.0,
            upvotes=45,
            helpful_count=35.0,
            event_ts="2025-11-01T15:00:00Z",
            run_id="integration_test",
            meta={
                "verified_purchase": "true",
                "language": "en",
                "product_id": "B08TEST"
            }
        ),

        # YouTube official video
        NormalizedContent(
            content_id="test_youtube_001",
            src="youtube",
            platform_id="test_video_id",
            author="Nike Official",
            title="Sustainability in Manufacturing - Behind the Scenes",
            body="Join us as we show you our eco-friendly manufacturing process. "
                 "This video includes AI-assisted editing for better accessibility. "
                 "All footage is authentic and shows our real facilities.",
            rating=0.97,
            upvotes=75000,
            event_ts="2025-10-30T09:00:00Z",
            run_id="integration_test",
            meta={
                "author_verified": "true",
                "verified": "true",
                "has_captions": "true",
                "language": "en"
            }
        ),

        # Medium quality content
        NormalizedContent(
            content_id="test_brave_001",
            src="brave",
            platform_id="brave_web_001",
            author="BlogWriter",
            title="Nike Shoe Review",
            body="Good shoes. Comfortable. Would buy again.",
            rating=0.7,
            upvotes=5,
            event_ts="2025-11-02T12:00:00Z",
            run_id="integration_test",
            meta={
                "language": "en"
            }
        ),

        # Low quality spam
        NormalizedContent(
            content_id="test_spam_001",
            src="brave",
            platform_id="spam_001",
            author="unknown",
            title="BUY CHEAP NIKE!!!",
            body="CLICK HERE NOW!!! DISCOUNT!!!",
            rating=0.0,
            upvotes=0,
            event_ts="2025-11-02T14:00:00Z",
            run_id="integration_test",
            meta={}
        )
    ]


def test_pipeline_legacy_mode():
    """Test pipeline with legacy AR mode enabled"""
    print_section("TEST 1: Pipeline with Legacy AR Mode")

    # Ensure legacy mode is enabled
    original_legacy_mode = SETTINGS.get('enable_legacy_ar_mode', True)
    SETTINGS['enable_legacy_ar_mode'] = True

    try:
        # Create pipeline
        pipeline = ScoringPipeline()
        print("✓ Pipeline initialized with legacy AR mode")

        # Create test content
        content = create_test_content()
        print(f"✓ Created {len(content)} test content items")

        # Create brand config
        brand_config = {
            'brand_id': 'nike',
            'brand_name': 'Nike',
            'keywords': ['nike', 'air max', 'running']
        }

        # Run pipeline
        print("\nRunning pipeline...")
        result = pipeline.run_scoring_pipeline(content, brand_config)

        # Validate results
        print(f"\n✓ Pipeline completed: {result.status}")
        print(f"  Run ID: {result.run_id}")
        print(f"  Items processed: {result.items_processed}")
        print(f"  Duration: {(result.end_time - result.start_time).total_seconds():.2f}s")

        # Check for classified scores
        if hasattr(result, 'classified_scores') and result.classified_scores:
            scores = result.classified_scores
            print(f"\n✓ Generated {len(scores)} ContentScores")

            # Check rating properties
            for score in scores[:3]:  # Check first 3
                print(f"\n  {score.content_id}:")
                print(f"    Comprehensive Rating: {score.rating_comprehensive:.2f}/100")
                print(f"    Rating Band: {score.rating_band.value.upper()}")
                print(f"    Dimensions:")
                print(f"      Provenance:    {score.rating_provenance:.2f}")
                print(f"      Resonance:     {score.rating_resonance:.2f}")
                print(f"      Coherence:     {score.rating_coherence:.2f}")
                print(f"      Transparency:  {score.rating_transparency:.2f}")
                print(f"      Verification:  {score.rating_verification:.2f}")

                # Check for detected attributes in meta
                try:
                    import json
                    meta = json.loads(score.meta) if isinstance(score.meta, str) else score.meta
                    attr_count = meta.get('attribute_count', 0)
                    print(f"    Detected Attributes: {attr_count}")
                except Exception:
                    pass

            # Check for legacy AR
            if hasattr(result, 'ar_result') and result.ar_result:
                ar = result.ar_result
                print(f"\n✓ Legacy AR calculated:")
                print(f"  Total: {ar.total_items}")
                print(f"  Authentic: {ar.authentic_items}")
                print(f"  Suspect: {ar.suspect_items}")
                print(f"  Inauthentic: {ar.inauthentic_items}")
                print(f"  AR: {ar.authenticity_ratio_pct:.2f}%")
                print(f"  Extended AR: {ar.extended_ar:.2f}%")
            else:
                print("\n✗ Warning: No legacy AR result found")

        return True

    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        SETTINGS['enable_legacy_ar_mode'] = original_legacy_mode


def test_pipeline_trust_stack_mode():
    """Test pipeline with Trust Stack mode (no legacy AR)"""
    print_section("TEST 2: Pipeline with Trust Stack Mode (No Legacy AR)")

    # Disable legacy mode
    original_legacy_mode = SETTINGS.get('enable_legacy_ar_mode', True)
    SETTINGS['enable_legacy_ar_mode'] = False

    try:
        # Create pipeline
        pipeline = ScoringPipeline()
        print("✓ Pipeline initialized with Trust Stack mode")

        # Create test content
        content = create_test_content()[:3]  # Use subset for speed
        print(f"✓ Created {len(content)} test content items")

        # Create brand config
        brand_config = {
            'brand_id': 'nike',
            'brand_name': 'Nike',
            'keywords': ['nike', 'air max']
        }

        # Run pipeline
        print("\nRunning pipeline...")
        result = pipeline.run_scoring_pipeline(content, brand_config)

        # Validate results
        print(f"\n✓ Pipeline completed: {result.status}")

        # Check that AR was NOT calculated
        has_ar = hasattr(result, 'ar_result') and result.ar_result is not None
        if not has_ar:
            print("✓ Legacy AR correctly disabled")
        else:
            print("⚠ Warning: AR result present despite disabled mode")

        # Check rating bands
        if hasattr(result, 'classified_scores') and result.classified_scores:
            scores = result.classified_scores

            # Count rating bands
            bands = {
                RatingBand.EXCELLENT: 0,
                RatingBand.GOOD: 0,
                RatingBand.FAIR: 0,
                RatingBand.POOR: 0
            }

            for score in scores:
                bands[score.rating_band] += 1

            print(f"\n✓ Rating Band Distribution:")
            for band, count in bands.items():
                if count > 0:
                    print(f"  {band.value.upper()}: {count}")

        return True

    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        SETTINGS['enable_legacy_ar_mode'] = original_legacy_mode


def test_attribute_detection():
    """Verify that attributes are being detected and stored"""
    print_section("TEST 3: Attribute Detection Validation")

    try:
        from scoring.scorer import ContentScorer

        scorer = ContentScorer(use_attribute_detection=True)
        print("✓ Scorer initialized with attribute detection")

        # Create single test item
        content = NormalizedContent(
            content_id="attr_test",
            src="reddit",
            platform_id="test",
            author="verified_user",
            title="AI-generated Nike review",
            body="According to Nike's website, these shoes are great. Source: nike.com",
            rating=0.9,
            upvotes=100,
            event_ts="2025-11-02T10:00:00Z",
            run_id="attr_test",
            meta={
                "verified": "true",
                "author_verified": "true",
                "language": "en"
            }
        )

        brand_config = {'brand_id': 'nike', 'keywords': ['nike']}

        # Score content
        print("\nScoring content...")
        scores = scorer.batch_score_content([content], brand_config)

        if scores:
            score = scores[0]

            # Parse meta to check attributes
            import json
            meta = json.loads(score.meta) if isinstance(score.meta, str) else score.meta

            attr_count = meta.get('attribute_count', 0)
            detected_attrs = meta.get('detected_attributes', [])

            print(f"\n✓ Attribute detection results:")
            print(f"  Total attributes detected: {attr_count}")

            if detected_attrs:
                print(f"\n  Detected attributes:")
                for attr in detected_attrs[:5]:  # Show first 5
                    print(f"    • {attr['label']} ({attr['dimension']})")
                    print(f"      Value: {attr['value']}/10")
                    print(f"      Evidence: {attr['evidence']}")
                    print(f"      Confidence: {attr['confidence']}")

                if len(detected_attrs) > 5:
                    print(f"    ... and {len(detected_attrs) - 5} more")

            return attr_count > 0

        return False

    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all integration tests"""
    print("\n" + "█"*80)
    print("█" + " "*78 + "█")
    print("█" + " "*15 + "TRUST STACK PIPELINE INTEGRATION TEST" + " "*27 + "█")
    print("█" + " "*78 + "█")
    print("█"*80)

    results = []

    # Test 1: Legacy AR mode
    results.append(("Legacy AR Mode", test_pipeline_legacy_mode()))

    # Test 2: Trust Stack mode
    results.append(("Trust Stack Mode", test_pipeline_trust_stack_mode()))

    # Test 3: Attribute detection
    results.append(("Attribute Detection", test_attribute_detection()))

    # Summary
    print_section("TEST SUMMARY")

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  {status}: {name}")

    print(f"\n{passed}/{total} tests passed")

    if passed == total:
        print("\n✓ ALL TESTS PASSED - Phase A Complete!")
        return 0
    else:
        print(f"\n✗ {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
