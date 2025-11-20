#!/usr/bin/env python3
"""
Diagnostic script to understand why Coherence and Verification scores are high
without returning suggested improvements.

This script analyzes recent pipeline runs to show:
1. Base LLM scores vs adjusted scores
2. Content type distribution
3. Brand-owned vs third-party content
4. Feedback generation patterns
"""

import sys
import json
import logging
from pathlib import Path
from typing import Dict, List, Any

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from data.models import NormalizedContent
from scoring.scorer import ContentScorer
from config.settings import SETTINGS

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def analyze_score_adjustments(content: NormalizedContent, brand_context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze how scores are adjusted for a piece of content
    
    Returns detailed breakdown of:
    - Content type detection
    - Brand ownership detection
    - Base LLM scores
    - Adjusted scores
    - Multipliers applied
    """
    scorer = ContentScorer(use_attribute_detection=False)
    
    # Determine content type
    content_type = scorer._determine_content_type(content)
    
    # Check if brand-owned
    content_url = getattr(content, 'url', '').lower()
    brand_keywords = [kw.lower() for kw in brand_context.get('keywords', [])]
    is_brand_owned = any(keyword in content_url for keyword in brand_keywords if keyword)
    
    # Get base scores (we'll need to temporarily disable adjustments)
    # For now, just score normally and log what we see
    logger.info(f"\n{'='*80}")
    logger.info(f"ANALYZING: {content.title[:60]}...")
    logger.info(f"URL: {content.url}")
    logger.info(f"Content Type: {content_type}")
    logger.info(f"Brand Owned: {is_brand_owned}")
    logger.info(f"{'='*80}\n")
    
    # Score the content
    scores = scorer.score_content(content, brand_context)
    
    # Calculate expected multipliers
    coherence_multiplier = 1.25 if content_type in ['landing_page', 'product_page', 'other'] else 1.0
    verification_multiplier = 1.30 if content_type in ['landing_page', 'product_page', 'other'] else 1.0
    
    # Check for LLM issues
    llm_issues = {}
    if hasattr(content, '_llm_issues'):
        llm_issues = content._llm_issues
    
    analysis = {
        'content_id': content.content_id,
        'title': content.title[:100],
        'url': content.url,
        'content_type': content_type,
        'is_brand_owned': is_brand_owned,
        'scores': {
            'coherence': {
                'final': scores.coherence,
                'expected_multiplier': coherence_multiplier,
                'estimated_base': scores.coherence / coherence_multiplier if coherence_multiplier > 1 else scores.coherence,
            },
            'verification': {
                'final': scores.verification,
                'expected_multiplier': verification_multiplier,
                'estimated_base': scores.verification / verification_multiplier if verification_multiplier > 1 else scores.verification,
            },
            'provenance': scores.provenance,
            'transparency': scores.transparency,
            'resonance': scores.resonance,
        },
        'llm_issues': {
            'coherence': len(llm_issues.get('coherence', [])),
            'verification': len(llm_issues.get('verification', [])),
            'transparency': len(llm_issues.get('transparency', [])),
        },
        'llm_issue_details': llm_issues
    }
    
    return analysis


def print_analysis(analysis: Dict[str, Any]):
    """Pretty print the analysis"""
    print(f"\n{'='*100}")
    print(f"CONTENT: {analysis['title']}")
    print(f"{'='*100}")
    print(f"URL: {analysis['url']}")
    print(f"Content Type: {analysis['content_type']}")
    print(f"Brand Owned: {analysis['is_brand_owned']}")
    print()
    
    print("COHERENCE ANALYSIS:")
    coh = analysis['scores']['coherence']
    print(f"  Final Score: {coh['final']:.3f} ({coh['final']*100:.1f}%)")
    print(f"  Multiplier Applied: {coh['expected_multiplier']:.2f}x")
    print(f"  Estimated Base Score: {coh['estimated_base']:.3f} ({coh['estimated_base']*100:.1f}%)")
    print(f"  LLM Issues Found: {analysis['llm_issues']['coherence']}")
    if coh['final'] >= 0.9:
        print(f"  ⚠️  HIGH SCORE (≥90%) - LLM asked for 'improvement opportunities'")
    print()
    
    print("VERIFICATION ANALYSIS:")
    ver = analysis['scores']['verification']
    print(f"  Final Score: {ver['final']:.3f} ({ver['final']*100:.1f}%)")
    print(f"  Multiplier Applied: {ver['expected_multiplier']:.2f}x")
    print(f"  Estimated Base Score: {ver['estimated_base']:.3f} ({ver['estimated_base']*100:.1f}%)")
    print(f"  LLM Issues Found: {analysis['llm_issues']['verification']}")
    if analysis['is_brand_owned']:
        print(f"  ℹ️  Brand-owned content - lenient verification criteria applied")
    if ver['final'] >= 0.9:
        print(f"  ⚠️  HIGH SCORE (≥90%) - LLM asked for 'improvement opportunities'")
    print()
    
    print("OTHER DIMENSIONS:")
    print(f"  Provenance: {analysis['scores']['provenance']:.3f} ({analysis['scores']['provenance']*100:.1f}%)")
    print(f"  Transparency: {analysis['scores']['transparency']:.3f} ({analysis['scores']['transparency']*100:.1f}%)")
    print(f"  Resonance: {analysis['scores']['resonance']:.3f} ({analysis['scores']['resonance']*100:.1f}%)")
    print()
    
    # Show LLM issue details if any
    if any(analysis['llm_issues'].values()):
        print("LLM ISSUE DETAILS:")
        for dimension, issues in analysis['llm_issue_details'].items():
            if issues:
                print(f"\n  {dimension.upper()} ({len(issues)} issues):")
                for i, issue in enumerate(issues, 1):
                    print(f"    {i}. Type: {issue.get('type', 'unknown')}")
                    print(f"       Confidence: {issue.get('confidence', 0):.2f}")
                    print(f"       Evidence: {issue.get('evidence', 'N/A')[:100]}...")
                    print(f"       Suggestion: {issue.get('suggestion', 'N/A')[:100]}...")
    else:
        print("⚠️  NO LLM ISSUES FOUND - This is why you're not seeing suggestions!")
    
    print(f"{'='*100}\n")


def create_test_content() -> List[tuple[NormalizedContent, Dict[str, Any]]]:
    """Create test content samples to analyze"""
    
    # Test case 1: Brand-owned landing page (should get high scores)
    content1 = NormalizedContent(
        content_id="test_brand_landing",
        src="web",
        platform_id="https://www.mastercard.com/",
        author="Mastercard",
        url="https://www.mastercard.com/solutions/payment-processing",
        title="Mastercard Payment Processing Solutions",
        body="""
        Mastercard Engage offers a directory of approved specialists who can help you 
        integrate our payment processing solutions. Our platform provides secure, 
        reliable payment processing for businesses of all sizes. Learn more about 
        how we can help your business grow.
        """,
        channel="web",
        event_ts="2024-01-15T10:00:00Z"
    )
    brand_context1 = {
        'brand_name': 'Mastercard',
        'keywords': ['mastercard', 'mastercard.com'],
        'use_guidelines': False
    }
    
    # Test case 2: Third-party blog post (should get normal scores)
    content2 = NormalizedContent(
        content_id="test_thirdparty_blog",
        src="web",
        platform_id="https://techcrunch.com/",
        author="TechCrunch",
        url="https://techcrunch.com/2024/01/15/mastercard-launches-new-feature",
        title="Mastercard Launches New Payment Feature",
        body="""
        Mastercard announced today a new payment processing feature that promises to 
        revolutionize online transactions. The company claims this will reduce fraud 
        by 50% and increase transaction speed by 3x. Industry experts are skeptical 
        of these claims, noting that similar promises have been made before.
        """,
        channel="web",
        event_ts="2024-01-15T10:00:00Z"
    )
    brand_context2 = {
        'brand_name': 'Mastercard',
        'keywords': ['mastercard', 'mastercard.com'],
        'use_guidelines': False
    }
    
    # Test case 3: Product page with marketing claims
    content3 = NormalizedContent(
        content_id="test_product_page",
        src="web",
        platform_id="https://www.mastercard.com/",
        author="Mastercard",
        url="https://www.mastercard.com/products/credit-cards",
        title="Mastercard Credit Cards - Find Your Perfect Card",
        body="""
        Find the right type of Mastercard payment card for you. We offer a wide range 
        of credit cards with benefits including cashback, travel rewards, and low APR. 
        Our cards are accepted worldwide and come with fraud protection. Apply now 
        and get approved in minutes.
        """,
        channel="web",
        event_ts="2024-01-15T10:00:00Z"
    )
    brand_context3 = {
        'brand_name': 'Mastercard',
        'keywords': ['mastercard', 'mastercard.com'],
        'use_guidelines': False
    }
    
    return [
        (content1, brand_context1),
        (content2, brand_context2),
        (content3, brand_context3),
    ]


def main():
    """Run diagnostic analysis"""
    print("\n" + "="*100)
    print("HIGH SCORE DIAGNOSTIC TOOL")
    print("Analyzing why Coherence and Verification scores are high without suggestions")
    print("="*100 + "\n")
    
    # Create test content
    test_cases = create_test_content()
    
    print(f"Running analysis on {len(test_cases)} test cases...\n")
    
    # Analyze each test case
    results = []
    for content, brand_context in test_cases:
        analysis = analyze_score_adjustments(content, brand_context)
        results.append(analysis)
        print_analysis(analysis)
    
    # Summary statistics
    print("\n" + "="*100)
    print("SUMMARY STATISTICS")
    print("="*100 + "\n")
    
    total = len(results)
    high_coherence = sum(1 for r in results if r['scores']['coherence']['final'] >= 0.9)
    high_verification = sum(1 for r in results if r['scores']['verification']['final'] >= 0.9)
    brand_owned = sum(1 for r in results if r['is_brand_owned'])
    marketing_content = sum(1 for r in results if r['content_type'] in ['landing_page', 'product_page', 'other'])
    no_issues = sum(1 for r in results if sum(r['llm_issues'].values()) == 0)
    
    print(f"Total Content Analyzed: {total}")
    print(f"High Coherence (≥90%): {high_coherence} ({high_coherence/total*100:.1f}%)")
    print(f"High Verification (≥90%): {high_verification} ({high_verification/total*100:.1f}%)")
    print(f"Brand-Owned Content: {brand_owned} ({brand_owned/total*100:.1f}%)")
    print(f"Marketing Content (gets multipliers): {marketing_content} ({marketing_content/total*100:.1f}%)")
    print(f"No LLM Issues Found: {no_issues} ({no_issues/total*100:.1f}%)")
    print()
    
    # Average scores
    avg_coherence = sum(r['scores']['coherence']['final'] for r in results) / total
    avg_verification = sum(r['scores']['verification']['final'] for r in results) / total
    avg_coherence_base = sum(r['scores']['coherence']['estimated_base'] for r in results) / total
    avg_verification_base = sum(r['scores']['verification']['estimated_base'] for r in results) / total
    
    print("AVERAGE SCORES:")
    print(f"Coherence (Final): {avg_coherence:.3f} ({avg_coherence*100:.1f}%)")
    print(f"Coherence (Estimated Base): {avg_coherence_base:.3f} ({avg_coherence_base*100:.1f}%)")
    print(f"Verification (Final): {avg_verification:.3f} ({avg_verification*100:.1f}%)")
    print(f"Verification (Estimated Base): {avg_verification_base:.3f} ({avg_verification_base*100:.1f}%)")
    print()
    
    print("KEY INSIGHTS:")
    if marketing_content / total > 0.5:
        print("  • Majority of content is marketing/landing pages → 25-30% score boosts applied")
    if brand_owned / total > 0.5:
        print("  • Majority of content is brand-owned → Lenient verification criteria")
    if no_issues / total > 0.5:
        print("  ⚠️  Majority of content has NO LLM issues → This is why you're not seeing suggestions!")
    if high_coherence / total > 0.5 or high_verification / total > 0.5:
        print("  • Majority of scores are ≥90% → LLM asked for 'improvement opportunities' not 'issues'")
    
    print("\n" + "="*100 + "\n")


if __name__ == "__main__":
    main()
