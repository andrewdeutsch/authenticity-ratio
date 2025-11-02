#!/usr/bin/env python3
"""
Test script to demonstrate Trust Stack Rating foundation
Shows attribute detection, rating calculations, and data models
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from data.models import (
    NormalizedContent,
    ContentScores,
    TrustStackRating,
    DetectedAttribute,
    RatingBand,
    AuthenticityRatio
)
# Import directly to avoid loading scorer dependencies
import importlib.util
spec = importlib.util.spec_from_file_location(
    "attribute_detector",
    os.path.join(os.path.dirname(os.path.dirname(__file__)), "scoring", "attribute_detector.py")
)
attribute_detector = importlib.util.module_from_spec(spec)
spec.loader.exec_module(attribute_detector)
TrustStackAttributeDetector = attribute_detector.TrustStackAttributeDetector

from config.settings import SETTINGS
import json


def print_section(title: str):
    """Print a formatted section header"""
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80 + "\n")


def test_rubric_loading():
    """Test that rubric loads with 36 enabled attributes"""
    print_section("1. RUBRIC CONFIGURATION")

    detector = TrustStackAttributeDetector()

    print(f"✓ Rubric Version: {detector.rubric['version']}")
    print(f"✓ Total Attributes in Rubric: {len(detector.rubric['attributes'])}")
    print(f"✓ Enabled Attributes: {len(detector.attributes)}")

    # Count by dimension
    dimension_counts = {}
    for attr in detector.attributes.values():
        dim = attr.get('dimension', 'unknown')
        dimension_counts[dim] = dimension_counts.get(dim, 0) + 1

    print(f"\nDimension Distribution:")
    for dim, count in sorted(dimension_counts.items()):
        print(f"  • {dim.capitalize()}: {count} attributes")

    return detector


def create_sample_content():
    """Create sample normalized content for testing"""
    print_section("2. SAMPLE CONTENT")

    samples = [
        # Reddit post - high quality
        NormalizedContent(
            content_id="reddit_001",
            src="reddit",
            platform_id="t3_abc123",
            author="verified_user",
            title="Nike's new sustainability initiative - AI-generated summary",
            body="This is a detailed post about Nike's commitment to sustainable manufacturing. "
                 "According to their official press release, they're reducing carbon emissions by 50%. "
                 "The initiative includes transparency reports and third-party verification. "
                 "Source: https://nike.com/sustainability",
            rating=0.95,  # Reddit upvote ratio
            upvotes=150,
            event_ts="2025-11-02T10:00:00Z",
            run_id="test_001",
            meta={
                "author_verified": "true",
                "language": "en",
                "url": "https://reddit.com/r/nike/comments/abc123",
                "canonical_url": "https://reddit.com/r/nike/comments/abc123",
                "verified": "true"
            }
        ),

        # Amazon review - verified purchase
        NormalizedContent(
            content_id="amazon_001",
            src="amazon",
            platform_id="R2ABC123",
            author="John D.",
            title="Great running shoes!",
            body="Excellent quality. Very comfortable for long runs. Highly recommend. "
                 "The breathable mesh is perfect for summer training.",
            rating=5.0,  # Star rating
            upvotes=25,
            helpful_count=20.0,
            event_ts="2025-11-01T15:30:00Z",
            run_id="test_001",
            meta={
                "verified_purchase": "true",
                "language": "en",
                "product_id": "B07XYZ"
            }
        ),

        # YouTube video - with captions
        NormalizedContent(
            content_id="youtube_001",
            src="youtube",
            platform_id="dQw4w9WgXcQ",
            author="Nike Official",
            title="Behind the Scenes: Nike Air Max Production",
            body="Take a look inside our manufacturing facilities. This video was created "
                 "with AI assistance for editing and captions. All footage is authentic "
                 "and shows our real production process.",
            rating=0.98,  # Like ratio
            upvotes=50000,
            event_ts="2025-10-30T12:00:00Z",
            run_id="test_001",
            meta={
                "verified": "true",
                "has_captions": "true",
                "language": "en",
                "author_verified": "true"
            }
        ),

        # Low quality content
        NormalizedContent(
            content_id="spam_001",
            src="brave",
            platform_id="spam123",
            author="unknown",
            title="Buy cheap Nike!",
            body="Click here now!!!",
            rating=0.0,
            upvotes=0,
            event_ts="2025-11-02T14:00:00Z",
            run_id="test_001",
            meta={}
        )
    ]

    for i, content in enumerate(samples, 1):
        print(f"{i}. {content.src.upper()}: {content.title[:60]}...")
        print(f"   Author: {content.author} | Upvotes: {content.upvotes} | Rating: {content.rating}")

    return samples


def test_attribute_detection(detector, samples):
    """Test attribute detection on sample content"""
    print_section("3. ATTRIBUTE DETECTION")

    all_results = []

    for content in samples:
        print(f"\n📄 Content: {content.content_id} ({content.src})")
        print(f"   Title: {content.title[:70]}...")

        detected = detector.detect_attributes(content)
        all_results.append((content, detected))

        if detected:
            print(f"   ✓ Detected {len(detected)} attributes:\n")

            # Group by dimension
            by_dimension = {}
            for attr in detected:
                if attr.dimension not in by_dimension:
                    by_dimension[attr.dimension] = []
                by_dimension[attr.dimension].append(attr)

            for dimension in sorted(by_dimension.keys()):
                attrs = by_dimension[dimension]
                print(f"   {dimension.upper()}:")
                for attr in attrs:
                    print(f"      • {attr.label}")
                    print(f"        Value: {attr.value}/10 | Evidence: {attr.evidence}")
        else:
            print("   ⚠ No attributes detected")

    return all_results


def test_rating_calculations(detector, detection_results):
    """Test rating calculations and data models"""
    print_section("4. TRUST STACK RATINGS")

    trust_ratings = []

    for content, detected_attrs in detection_results:
        print(f"\n📊 {content.content_id} ({content.src})")

        # Calculate dimension ratings based on detected attributes
        dimension_ratings = {
            'provenance': 50.0,  # Start with neutral baseline
            'resonance': 50.0,
            'coherence': 50.0,
            'transparency': 50.0,
            'verification': 50.0
        }

        # Adjust based on detected attributes
        for attr in detected_attrs:
            # Map 1-10 scale to adjustment (-50 to +50)
            adjustment = (attr.value - 5.5) * 10  # 1→-45, 10→+45
            dimension_ratings[attr.dimension] += adjustment

            # Clamp to 0-100
            dimension_ratings[attr.dimension] = max(0, min(100, dimension_ratings[attr.dimension]))

        # Calculate comprehensive rating (weighted average)
        weights = SETTINGS['scoring_weights']
        comprehensive = (
            dimension_ratings['provenance'] * weights.provenance +
            dimension_ratings['resonance'] * weights.resonance +
            dimension_ratings['coherence'] * weights.coherence +
            dimension_ratings['transparency'] * weights.transparency +
            dimension_ratings['verification'] * weights.verification
        )

        # Create TrustStackRating
        rating = TrustStackRating(
            content_id=content.content_id,
            digital_property_type=f"{content.src}_post",
            digital_property_url=content.meta.get('url', 'N/A'),
            brand_id="nike",
            run_id=content.run_id,
            rating_provenance=dimension_ratings['provenance'],
            rating_resonance=dimension_ratings['resonance'],
            rating_coherence=dimension_ratings['coherence'],
            rating_transparency=dimension_ratings['transparency'],
            rating_verification=dimension_ratings['verification'],
            rating_comprehensive=comprehensive,
            attributes_detected=detected_attrs,
            attributes_missing=[],
            event_ts=content.event_ts
        )

        trust_ratings.append(rating)

        # Display ratings
        print(f"   Dimension Ratings (0-100):")
        print(f"      Provenance:    {rating.rating_provenance:6.2f}")
        print(f"      Resonance:     {rating.rating_resonance:6.2f}")
        print(f"      Coherence:     {rating.rating_coherence:6.2f}")
        print(f"      Transparency:  {rating.rating_transparency:6.2f}")
        print(f"      Verification:  {rating.rating_verification:6.2f}")
        print(f"   ───────────────────────────")
        print(f"   Comprehensive: {rating.rating_comprehensive:6.2f}")
        print(f"   Rating Band:   {rating.get_rating_band().value.upper()}")

    return trust_ratings


def test_content_scores_model(trust_ratings):
    """Test ContentScores/ContentRatings model"""
    print_section("5. CONTENT SCORES MODEL")

    content_scores_list = []

    for rating in trust_ratings:
        # Convert TrustStackRating to ContentScores (for backward compatibility)
        scores = ContentScores(
            content_id=rating.content_id,
            brand="nike",
            src=rating.digital_property_type.split('_')[0],
            event_ts=rating.event_ts,
            score_provenance=rating.rating_provenance / 100,  # Store as 0-1
            score_resonance=rating.rating_resonance / 100,
            score_coherence=rating.rating_coherence / 100,
            score_transparency=rating.rating_transparency / 100,
            score_verification=rating.rating_verification / 100,
            rubric_version="v2.0-trust-stack",
            run_id=rating.run_id
        )

        content_scores_list.append(scores)

        print(f"\n{scores.content_id}:")
        print(f"   Internal Scores (0.0-1.0):")
        print(f"      Provenance: {scores.score_provenance:.3f}")
        print(f"      Overall:    {scores.overall_score:.3f}")
        print(f"\n   Rating Properties (0-100):")
        print(f"      Provenance:     {scores.rating_provenance:.2f}")
        print(f"      Comprehensive:  {scores.rating_comprehensive:.2f}")
        print(f"      Band:           {scores.rating_band.value.upper()}")

    return content_scores_list


def test_legacy_ar_synthesis(content_scores_list):
    """Test legacy AR synthesis from ratings"""
    print_section("6. LEGACY AR SYNTHESIS")

    if SETTINGS['enable_legacy_ar_mode']:
        print("✓ Legacy AR mode is ENABLED")
        print("\nSynthesizing AR from Trust Stack Ratings...")

        ar = AuthenticityRatio.from_ratings(
            ratings=content_scores_list,
            brand_id="nike",
            source="mixed",
            run_id="test_001"
        )

        print(f"\nLegacy Authenticity Ratio:")
        print(f"   Total Items:      {ar.total_items}")
        print(f"   Authentic:        {ar.authentic_items} (rating ≥ 75)")
        print(f"   Suspect:          {ar.suspect_items} (rating 40-74)")
        print(f"   Inauthentic:      {ar.inauthentic_items} (rating < 40)")
        print(f"   ───────────────────────────")
        print(f"   AR Percentage:    {ar.authenticity_ratio_pct:.1f}%")
        print(f"   Extended AR:      {ar.extended_ar:.1f}%")

        if not SETTINGS['show_ar_in_ui']:
            print("\n⚠ Note: AR is hidden in UI (show_ar_in_ui=False)")
    else:
        print("✗ Legacy AR mode is DISABLED")


def test_summary(trust_ratings):
    """Print summary statistics"""
    print_section("7. SUMMARY")

    avg_comprehensive = sum(r.rating_comprehensive for r in trust_ratings) / len(trust_ratings)

    band_counts = {}
    for rating in trust_ratings:
        band = rating.get_rating_band().value
        band_counts[band] = band_counts.get(band, 0) + 1

    print(f"Total Digital Properties Rated: {len(trust_ratings)}")
    print(f"Average Comprehensive Rating:   {avg_comprehensive:.2f}/100")
    print(f"\nRating Band Distribution:")
    for band, count in sorted(band_counts.items(), reverse=True):
        pct = (count / len(trust_ratings)) * 100
        print(f"   {band.upper():12} {count:2} ({pct:5.1f}%)")

    print(f"\nDimension Averages:")
    avg_dimensions = {
        'Provenance': sum(r.rating_provenance for r in trust_ratings) / len(trust_ratings),
        'Resonance': sum(r.rating_resonance for r in trust_ratings) / len(trust_ratings),
        'Coherence': sum(r.rating_coherence for r in trust_ratings) / len(trust_ratings),
        'Transparency': sum(r.rating_transparency for r in trust_ratings) / len(trust_ratings),
        'Verification': sum(r.rating_verification for r in trust_ratings) / len(trust_ratings)
    }

    for dim, avg in sorted(avg_dimensions.items()):
        print(f"   {dim:15} {avg:6.2f}/100")


def main():
    """Run all tests"""
    print("\n" + "█"*80)
    print("█" + " "*78 + "█")
    print("█" + " "*20 + "TRUST STACK RATING FOUNDATION TEST" + " "*24 + "█")
    print("█" + " "*78 + "█")
    print("█"*80)

    try:
        # Test 1: Rubric loading
        detector = test_rubric_loading()

        # Test 2: Sample content
        samples = create_sample_content()

        # Test 3: Attribute detection
        detection_results = test_attribute_detection(detector, samples)

        # Test 4: Trust Stack ratings
        trust_ratings = test_rating_calculations(detector, detection_results)

        # Test 5: ContentScores model
        content_scores_list = test_content_scores_model(trust_ratings)

        # Test 6: Legacy AR synthesis
        test_legacy_ar_synthesis(content_scores_list)

        # Test 7: Summary
        test_summary(trust_ratings)

        print_section("✓ ALL TESTS COMPLETED SUCCESSFULLY")

        return 0

    except Exception as e:
        print_section("✗ TEST FAILED")
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
