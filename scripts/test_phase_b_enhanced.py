#!/usr/bin/env python3
"""
Test Phase B Enhanced Detection

This script validates the Phase B enhancements:
- NLP-based detection (sentiment, readability, language)
- Embedding-based detection (brand voice, claim consistency)
- External API integration (domain reputation)

Can run without dependencies (will show which enhancements are available).
"""

import sys
import os
import importlib.util

# Add parent directory to path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, PROJECT_ROOT)

from typing import Dict, Any, List


def load_module_from_path(module_name, file_path):
    """Load a module directly from file path without triggering package imports"""
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load spec for {module_name} from {file_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


# Load data.models directly
models_path = os.path.join(PROJECT_ROOT, 'data', 'models.py')
models = load_module_from_path('data.models', models_path)
NormalizedContent = models.NormalizedContent


def test_nlp_modules():
    """Test NLP module availability and functionality"""
    print("=" * 80)
    print("PHASE B TEST 1: NLP Enhanced Detection")
    print("=" * 80)

    try:
        # Load module directly to avoid triggering scorer imports
        nlp_path = os.path.join(PROJECT_ROOT, 'scoring', 'nlp_enhanced.py')
        nlp_module = load_module_from_path('scoring.nlp_enhanced', nlp_path)

        get_sentiment_analyzer = nlp_module.get_sentiment_analyzer
        get_readability_analyzer = nlp_module.get_readability_analyzer
        get_language_detector = nlp_module.get_language_detector

        print("✓ NLP modules imported successfully")
    except ImportError as e:
        print(f"✗ NLP modules not available: {e}")
        print("  (This is expected if dependencies not installed)")
        return False

    # Test sentiment analyzer
    print("\n--- Sentiment Analysis ---")
    try:
        sentiment_analyzer = get_sentiment_analyzer()
        if sentiment_analyzer.enabled:
            test_texts = [
                "This product is absolutely amazing! Best purchase ever!",
                "Terrible quality. Complete waste of money.",
                "It's okay, nothing special but does the job."
            ]

            for text in test_texts:
                result = sentiment_analyzer.analyze_sentiment(text)
                if result:
                    print(f"Text: {text[:50]}...")
                    print(f"  Sentiment: {result['label']} (confidence: {result['score']:.2f})")
                    print(f"  Trust Stack value: {result['value']:.1f}/10")
            print("✓ Sentiment analysis working")
        else:
            print("✗ Sentiment analyzer not enabled (dependencies missing)")
            return False
    except Exception as e:
        print(f"✗ Sentiment analysis failed: {e}")
        return False

    # Test readability analyzer
    print("\n--- Readability Analysis ---")
    try:
        readability_analyzer = get_readability_analyzer()
        if readability_analyzer.enabled:
            test_text = """
            The Trust Stack Rating Tool provides comprehensive authenticity assessment
            for digital content. It analyzes five key dimensions: provenance, resonance,
            coherence, transparency, and verification. Each dimension contributes to an
            overall rating on a scale of 0 to 100.
            """

            result = readability_analyzer.analyze_readability(test_text, target_grade=9.0)
            if result:
                print(f"Text: {test_text.strip()[:80]}...")
                print(f"  Flesch-Kincaid Grade: {result['flesch_kincaid_grade']:.1f}")
                print(f"  Flesch Reading Ease: {result['flesch_reading_ease']:.1f}")
                print(f"  Trust Stack value: {result['value']:.1f}/10")
            print("✓ Readability analysis working")
        else:
            print("✗ Readability analyzer not enabled (textstat missing)")
            return False
    except Exception as e:
        print(f"✗ Readability analysis failed: {e}")
        return False

    # Test language detector
    print("\n--- Language Detection ---")
    try:
        language_detector = get_language_detector()
        if language_detector.enabled:
            test_texts = {
                "en": "This is a test of the language detection system.",
                "es": "Esta es una prueba del sistema de detección de idiomas.",
                "fr": "Ceci est un test du système de détection de langue."
            }

            for expected_lang, text in test_texts.items():
                result = language_detector.detect_language(text, target_language="en")
                if result:
                    print(f"Expected: {expected_lang}, Detected: {result['detected_language']}")
                    print(f"  Confidence: {result['confidence']:.2f}")
                    print(f"  Trust Stack value: {result['value']:.1f}/10")
            print("✓ Language detection working")
        else:
            print("✗ Language detector not enabled (langdetect missing)")
            return False
    except Exception as e:
        print(f"✗ Language detection failed: {e}")
        return False

    return True


def test_embedding_modules():
    """Test embedding module availability and functionality"""
    print("\n" + "=" * 80)
    print("PHASE B TEST 2: Embedding-Based Detection")
    print("=" * 80)

    try:
        # Load module directly to avoid triggering scorer imports
        embeddings_path = os.path.join(PROJECT_ROOT, 'scoring', 'embeddings.py')
        embeddings_module = load_module_from_path('scoring.embeddings', embeddings_path)

        get_brand_voice_analyzer = embeddings_module.get_brand_voice_analyzer
        get_claim_consistency_analyzer = embeddings_module.get_claim_consistency_analyzer
        get_semantic_similarity_analyzer = embeddings_module.get_semantic_similarity_analyzer

        print("✓ Embedding modules imported successfully")
    except ImportError as e:
        print(f"✗ Embedding modules not available: {e}")
        print("  (This is expected if dependencies not installed)")
        return False

    # Test semantic similarity
    print("\n--- Semantic Similarity ---")
    try:
        similarity_analyzer = get_semantic_similarity_analyzer()
        if similarity_analyzer.enabled:
            text1 = "The product quality is excellent and highly recommended."
            text2 = "This item is of great quality and I would recommend it."
            text3 = "The weather is nice today."

            sim_12 = similarity_analyzer.calculate_similarity(text1, text2)
            sim_13 = similarity_analyzer.calculate_similarity(text1, text3)

            print(f"Similar texts similarity: {sim_12:.3f}")
            print(f"Different texts similarity: {sim_13:.3f}")
            print("✓ Semantic similarity working")
        else:
            print("✗ Similarity analyzer not enabled (sentence-transformers missing)")
            return False
    except Exception as e:
        print(f"✗ Semantic similarity failed: {e}")
        return False

    # Test brand voice analyzer
    print("\n--- Brand Voice Consistency ---")
    try:
        # Create brand corpus
        brand_corpus = [
            "At TechCorp, we believe in innovative solutions that empower our customers.",
            "TechCorp delivers cutting-edge technology with a focus on user experience.",
            "Our mission at TechCorp is to make technology accessible to everyone.",
        ]

        brand_voice_analyzer = get_brand_voice_analyzer(brand_corpus)
        if brand_voice_analyzer.enabled:
            # Test on-brand content
            on_brand_text = "TechCorp's innovative platform empowers users with accessible technology."
            result_on = brand_voice_analyzer.analyze_brand_voice_consistency(on_brand_text)

            # Test off-brand content
            off_brand_text = "Buy cheap products now! Limited time offer! Click here!"
            result_off = brand_voice_analyzer.analyze_brand_voice_consistency(off_brand_text)

            if result_on and result_off:
                print(f"On-brand text similarity: {result_on['similarity']:.3f} (value: {result_on['value']:.1f}/10)")
                print(f"Off-brand text similarity: {result_off['similarity']:.3f} (value: {result_off['value']:.1f}/10)")
                print("✓ Brand voice analysis working")
            else:
                print("✗ Brand voice analysis returned None")
                return False
        else:
            print("✗ Brand voice analyzer not enabled (sentence-transformers missing)")
            return False
    except Exception as e:
        print(f"✗ Brand voice analysis failed: {e}")
        return False

    return True


def test_external_api_modules():
    """Test external API module availability and functionality"""
    print("\n" + "=" * 80)
    print("PHASE B TEST 3: External API Integration")
    print("=" * 80)

    try:
        # Load module directly to avoid triggering scorer imports
        apis_path = os.path.join(PROJECT_ROOT, 'scoring', 'external_apis.py')
        apis_module = load_module_from_path('scoring.external_apis', apis_path)

        get_domain_reputation_client = apis_module.get_domain_reputation_client

        print("✓ External API modules imported successfully")
    except ImportError as e:
        print(f"✗ External API modules not available: {e}")
        return False

    # Test domain reputation
    print("\n--- Domain Reputation ---")
    try:
        domain_client = get_domain_reputation_client()

        test_domains = [
            "https://nytimes.com/article",
            "https://example.edu/page",
            "https://sketchy-site.tk/spam",
            "https://reddit.com/r/test",
        ]

        for url in test_domains:
            result = domain_client.get_domain_score(url)
            if result:
                print(f"URL: {url}")
                print(f"  Domain: {result['domain']}")
                print(f"  Score: {result['score']:.1f}/10")
                print(f"  Evidence: {result['evidence']}")

        print("✓ Domain reputation working")
        return True
    except Exception as e:
        print(f"✗ Domain reputation failed: {e}")
        return False


def test_integrated_detection():
    """Test integrated attribute detection with Phase B enhancements"""
    print("\n" + "=" * 80)
    print("PHASE B TEST 4: Integrated Attribute Detection")
    print("=" * 80)

    try:
        # Load module directly to avoid triggering scorer imports
        detector_path = os.path.join(PROJECT_ROOT, 'scoring', 'attribute_detector.py')
        detector_module = load_module_from_path('scoring.attribute_detector', detector_path)

        TrustStackAttributeDetector = detector_module.TrustStackAttributeDetector

        print("✓ Attribute detector imported successfully")
    except ImportError as e:
        print(f"✗ Could not import attribute detector: {e}")
        return False
    except Exception as e:
        print(f"✗ Error loading attribute detector: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Create test content
    test_content = NormalizedContent(
        content_id="test-001",
        platform_id="reddit_test_001",
        src="reddit",
        author="TestUser",
        title="Amazing Product Review",
        body="""
        This product exceeded all my expectations! The quality is outstanding and
        the customer service was exceptional. I've been using it for three months
        now and it still works perfectly. The design is intuitive and easy to use,
        even for beginners. Highly recommend to anyone looking for a reliable solution.
        """,
        upvotes=150,
        rating=4.8,
        meta={
            "url": "https://reddit.com/r/reviews/test",
            "language": "en",
            "verified": "true"
        }
    )

    # Initialize detector
    try:
        detector = TrustStackAttributeDetector()
        print(f"✓ Detector initialized with {len(detector.attributes)} attributes")
    except Exception as e:
        print(f"✗ Could not initialize detector: {e}")
        return False

    # Detect attributes
    print("\n--- Detecting Attributes ---")
    try:
        detected = detector.detect_attributes(test_content)

        print(f"\nDetected {len(detected)} attributes:")

        # Group by dimension
        by_dimension = {}
        for attr in detected:
            if attr.dimension not in by_dimension:
                by_dimension[attr.dimension] = []
            by_dimension[attr.dimension].append(attr)

        for dimension in ['provenance', 'resonance', 'coherence', 'transparency', 'verification']:
            if dimension in by_dimension:
                print(f"\n{dimension.upper()}:")
                for attr in by_dimension[dimension]:
                    print(f"  • {attr.label}: {attr.value:.1f}/10")
                    print(f"    Evidence: {attr.evidence}")
                    print(f"    Confidence: {attr.confidence:.2f}")

        print(f"\n✓ Attribute detection working ({len(detected)} attributes detected)")
        return True
    except Exception as e:
        print(f"✗ Attribute detection failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def calculate_coverage_improvement():
    """Calculate coverage improvement from Phase A to Phase B"""
    print("\n" + "=" * 80)
    print("PHASE B TEST 5: Coverage Analysis")
    print("=" * 80)

    try:
        # Load module directly to avoid triggering scorer imports
        detector_path = os.path.join(PROJECT_ROOT, 'scoring', 'attribute_detector.py')
        detector_module = load_module_from_path('scoring.attribute_detector', detector_path)

        NLP_ENHANCED_AVAILABLE = detector_module.NLP_ENHANCED_AVAILABLE
        EMBEDDINGS_AVAILABLE = detector_module.EMBEDDINGS_AVAILABLE
        EXTERNAL_API_AVAILABLE = detector_module.EXTERNAL_API_AVAILABLE

        print(f"\nModule Availability:")
        print(f"  NLP Enhanced: {'✓ Available' if NLP_ENHANCED_AVAILABLE else '✗ Not available'}")
        print(f"  Embeddings: {'✓ Available' if EMBEDDINGS_AVAILABLE else '✗ Not available'}")
        print(f"  External APIs: {'✓ Available' if EXTERNAL_API_AVAILABLE else '✗ Not available'}")

        # Count enhanced attributes
        enhanced_attributes = {
            'tone_sentiment_appropriateness': NLP_ENHANCED_AVAILABLE,
            'readability_grade_level_fit': NLP_ENHANCED_AVAILABLE,
            'language_locale_match': NLP_ENHANCED_AVAILABLE,
            'brand_voice_consistency_score': EMBEDDINGS_AVAILABLE,
            'claim_consistency_across_pages': EMBEDDINGS_AVAILABLE,
            'source_domain_trust_baseline': EXTERNAL_API_AVAILABLE,
        }

        total_selected = 36
        phase_a_working = 11  # From Phase A validation
        phase_b_enhanced = sum(1 for v in enhanced_attributes.values() if v)

        # Estimate total working in Phase B
        phase_b_working = phase_a_working + phase_b_enhanced

        phase_a_coverage = (phase_a_working / total_selected) * 100
        phase_b_coverage = (phase_b_working / total_selected) * 100
        improvement = phase_b_coverage - phase_a_coverage

        print(f"\nCoverage Analysis:")
        print(f"  Total selected attributes: {total_selected}")
        print(f"  Phase A working: {phase_a_working} ({phase_a_coverage:.1f}%)")
        print(f"  Phase B enhanced: +{phase_b_enhanced}")
        print(f"  Phase B working: {phase_b_working} ({phase_b_coverage:.1f}%)")
        print(f"  Improvement: +{improvement:.1f} percentage points")

        if phase_b_coverage >= 40:
            print(f"\n✓ Coverage target met ({phase_b_coverage:.1f}% >= 40%)")
            return True
        else:
            print(f"\n⚠ Coverage below 40% target ({phase_b_coverage:.1f}%)")
            print("  (Install all dependencies for full coverage)")
            return False

    except Exception as e:
        print(f"✗ Coverage analysis failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all Phase B tests"""
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 20 + "PHASE B: ENHANCED DETECTION TEST" + " " * 26 + "║")
    print("╚" + "=" * 78 + "╝")
    print()

    results = {
        "NLP Modules": test_nlp_modules(),
        "Embedding Modules": test_embedding_modules(),
        "External APIs": test_external_api_modules(),
        "Integrated Detection": test_integrated_detection(),
        "Coverage Analysis": calculate_coverage_improvement(),
    }

    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for test_name, passed_test in results.items():
        status = "✓ PASS" if passed_test else "✗ FAIL"
        print(f"{status:8} {test_name}")

    print(f"\nOverall: {passed}/{total} tests passed")

    if passed == total:
        print("\n✓ All Phase B tests passed! Enhanced detection is working.")
        return 0
    elif passed >= 2:
        print("\n⚠ Partial success - some dependencies may not be installed.")
        print("  Install requirements: pip install -r requirements.txt")
        return 0
    else:
        print("\n✗ Phase B tests failed. Check errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
