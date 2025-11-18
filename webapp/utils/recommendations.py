"""
Recommendation and remedy generation for Trust Stack Rating
"""
import json
from typing import Dict, List, Any


def extract_issues_from_items(items: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Extract specific issues from content items grouped by dimension.

    Args:
        items: List of analyzed content items with detected attributes

    Returns:
        Dictionary mapping dimension to list of specific issues found
    """
    dimension_issues = {
        'provenance': [],
        'verification': [],
        'transparency': [],
        'coherence': [],
        'resonance': []
    }

    for item in items:
        meta = item.get('meta', {})
        if isinstance(meta, str):
            try:
                meta = json.loads(meta)
            except:
                meta = {}
        elif meta is None:
            meta = {}

        # Extract detected attributes
        detected_attrs = meta.get('detected_attributes', [])
        title = meta.get('title', meta.get('name', 'Unknown content'))[:60]
        url = meta.get('source_url', meta.get('url', ''))

        for attr in detected_attrs:
            dimension = attr.get('dimension', 'unknown')
            value = attr.get('value', 5)
            evidence = attr.get('evidence', '')
            label = attr.get('label', '')

            # Only report low-scoring attributes (value <= 5 indicates problems)
            if dimension in dimension_issues and value <= 5:
                dimension_issues[dimension].append({
                    'title': title,
                    'url': url,
                    'issue': label,
                    'evidence': evidence,
                    'value': value
                })

    return dimension_issues


def get_remedy_for_issue(issue_type: str, dimension: str) -> str:
    """
    Get specific remedy recommendation for a detected issue type.

    Args:
        issue_type: Type of issue detected (e.g., "Privacy Policy Link Availability Clarity")
        dimension: Dimension the issue belongs to

    Returns:
        Specific actionable remedy recommendation
    """
    # Map specific issues to remedies
    remedies = {
        # Provenance
        'AI vs Human Labeling Clarity': 'Add clear labels indicating whether content is AI-generated or human-created. Use schema.org markup to embed this metadata.',
        'Author Brand Identity Verified': '''Implement appropriate author attribution based on content type:

**For Blog Posts & Articles:** Add visible bylines with author names and optional author bio pages.

**For Corporate Landing Pages:** Consider these options:
• **Structured Data (Recommended):** Add schema.org markup with author/publisher info using JSON-LD format (invisible to users, visible to search engines)
• **Meta Tags:** Add <meta name="author" content="Team/Organization"> tags
• **Subtle Footer Attribution:** Include "Content by [Team]" or "Maintained by [Name/Team]" in page footer
• **About/Credits Pages:** Create dedicated /about or /team page and link discretely from main pages
• **Expandable Page Info:** Add a small "ⓘ" icon or "About this page" link showing contributors

Example Schema.org markup for landing pages:
```html
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "WebPage",
  "author": {
    "@type": "Organization",
    "name": "Acme Corp Marketing Team"
  },
  "publisher": {
    "@type": "Organization",
    "name": "Acme Corporation"
  }
}
</script>
```''',
        'C2PA CAI Manifest Present': 'Implement Content Authenticity Initiative (C2PA) manifests for media files to provide cryptographic provenance.',
        'Canonical URL Matches Declared Source': 'Ensure canonical URLs match the declared source. Add proper <link rel="canonical"> tags to all pages.',
        'Digital Watermark Fingerprint Detected': 'Add digital watermarks or fingerprints to images and videos for traceability.',
        'EXIF Metadata Integrity': 'Preserve EXIF metadata in images. Ensure metadata includes creator, date, and copyright information.',
        'Source Domain Trust Baseline': 'Improve domain reputation by adding SSL certificates, privacy policies, and contact information.',
        'Schema Compliance': 'Implement schema.org structured data markup (JSON-LD) for all content types.',
        'Metadata Completeness': 'Add complete metadata including title, description, author, date, and Open Graph/Twitter Card tags.',

        # Verification
        'Ad Sponsored Label Consistency': 'Clearly label all sponsored content and advertisements with "Sponsored" or "Ad" labels.',
        'Agent Safety Guardrail Presence': 'Implement content safety guardrails and moderation policies. Document them publicly.',
        'Claim to Source Traceability': 'Add citations and references for all claims. Link to authoritative sources.',
        'Engagement Authenticity Ratio': 'Monitor and remove fake engagement (bots, fake reviews). Encourage authentic user interactions.',
        'Influencer Partner Identity Verified': 'Verify influencer and partner identities. Display verification badges or certificates.',
        'Review Authenticity Confidence': 'Implement verified review systems. Flag or remove suspicious reviews.',
        'Seller Product Verification Rate': 'Verify seller identities and product authenticity. Display verification status prominently.',
        'Verified Purchaser Review Rate': 'Mark reviews from verified purchasers. Implement purchase verification in your review system.',

        # Transparency
        'AI Explainability Disclosure': 'When using AI, explain how it works and what data it uses. Add an AI transparency page.',
        'AI Generated Assisted Disclosure Present': 'Clearly disclose when content is AI-generated or AI-assisted. Add disclosure statements to all AI content.',
        'Bot Disclosure Response Audit': 'Clearly identify bot-generated responses. Add "This is an automated response" disclaimers.',
        'Caption Subtitle Availability Accuracy': 'Add accurate captions and subtitles to all video content. Use human review for accuracy.',
        'Data Source Citations for Claims': 'Add inline citations for all data-driven claims. Link to primary sources and datasets.',
        'Privacy Policy Link Availability Clarity': 'Add a clear Privacy Policy link to your footer and make it easily accessible. Ensure the policy is clear and up-to-date.',

        # Coherence
        'Brand Voice Consistency Score': 'Audit content for consistent brand voice. Create and enforce brand voice guidelines.',
        'Broken Link Rate': 'Regularly audit and fix broken links. Use automated link checkers weekly.',
        'Claim Consistency Across Pages': 'Ensure claims are consistent across all content. Create a single source of truth for key claims.',
        'Email Asset Consistency Check': 'Standardize email templates and branding. Ensure consistency with website branding.',
        'Engagement to Trust Correlation': 'Monitor how engagement patterns correlate with trust metrics. Address suspicious patterns.',
        'Multimodal Consistency Score': 'Ensure text, images, and videos tell a consistent story. Audit multimedia content for alignment.',
        'Temporal Continuity Versions': 'Maintain version history for content updates. Show update dates and change logs.',
        'Trust Fluctuation Index': 'Monitor trust score changes over time. Investigate and address sudden drops.',

        # Resonance
        'Community Alignment Index': 'Engage with your community authentically. Monitor sentiment and adjust messaging to align with community values.',
        'Creative Recency vs Trend': 'Stay current with trends while maintaining brand authenticity. Update content regularly.',
        'Cultural Context Alignment': 'Ensure content is culturally appropriate and relevant. Work with cultural consultants for diverse markets.',
        'Language Locale Match': 'Provide content in appropriate languages for your target markets. Use professional translation services.',
        'Personalization Relevance Embedding Similarity': 'Improve personalization algorithms to better match user interests while respecting privacy.',
        'Readability Grade Level Fit': 'Adjust content readability to match your target audience. Use readability tools to test and optimize.',
        'Tone Sentiment Appropriateness': 'Ensure content tone matches the context and audience expectations. Avoid overly promotional language.'
    }

    return remedies.get(issue_type, f'Address this {dimension} issue by improving content quality and adding relevant metadata.')


def generate_rating_recommendation(avg_rating: float, dimension_breakdown: Dict[str, Any], items: List[Dict[str, Any]]) -> str:
    """
    Generate data-driven recommendation based on dimension analysis with specific examples.

    Args:
        avg_rating: Average rating score (0-100)
        dimension_breakdown: Dictionary with dimension averages
        items: List of analyzed content items

    Returns:
        Comprehensive recommendation string with concrete examples
    """
    # Define dimension details
    dimension_info = {
        'provenance': {
            'name': 'Provenance',
            'recommendation': 'implement structured metadata (schema.org markup), add clear author attribution, and include publication timestamps on all content',
            'description': 'origin tracking and metadata'
        },
        'verification': {
            'name': 'Verification',
            'recommendation': 'fact-check claims against authoritative sources, add citations and references, and link to verifiable external data',
            'description': 'factual accuracy'
        },
        'transparency': {
            'name': 'Transparency',
            'recommendation': 'add disclosure statements, clearly identify sponsored content, and provide detailed attribution for all sources',
            'description': 'disclosure and clarity'
        },
        'coherence': {
            'name': 'Coherence',
            'recommendation': 'audit messaging consistency across all channels, align visual branding, and ensure unified voice in customer communications',
            'description': 'cross-channel consistency'
        },
        'resonance': {
            'name': 'Resonance',
            'recommendation': 'increase authentic engagement with your audience, reduce promotional language, and ensure cultural relevance in messaging',
            'description': 'audience engagement'
        }
    }

    # Find lowest-performing dimension
    dimension_keys = ['provenance', 'verification', 'transparency', 'coherence', 'resonance']
    dimension_scores = {
        key: dimension_breakdown.get(key, {}).get('average', 0.5) * 100  # Convert to 0-100 scale
        for key in dimension_keys
    }

    # Extract specific issues from items
    dimension_issues = extract_issues_from_items(items)

    # Find the dimension with the lowest score
    if dimension_scores:
        lowest_dim_key = min(dimension_scores, key=dimension_scores.get)
        lowest_dim_score = dimension_scores[lowest_dim_key]
        lowest_dim_info = dimension_info[lowest_dim_key]

        # Get example issues for the lowest dimension
        issues_for_dim = dimension_issues.get(lowest_dim_key, [])
        example_text = ""
        if issues_for_dim:
            # Get first unique issue as example
            example = issues_for_dim[0]
            example_text = f" For example, on \"{example['title']}\", there was an issue with {example['issue'].lower()}: {example['evidence']}."

        # Generate comprehensive summary based on rating band
        if avg_rating >= 80:
            # Excellent - maintain standards with minor optimization
            return f"Your brand content demonstrates high quality with an average rating of {avg_rating:.1f}/100. To reach even greater heights, consider optimizing {lowest_dim_info['name']} (currently at {lowest_dim_score:.1f}/100) by continuing to {lowest_dim_info['recommendation']}.{example_text}"

        elif avg_rating >= 60:
            # Good - focus on improvement area
            return f"Your content shows solid quality with an average rating of {avg_rating:.1f}/100. To improve from Good to Excellent, focus on enhancing {lowest_dim_info['name']} (currently at {lowest_dim_score:.1f}/100) by taking action to {lowest_dim_info['recommendation']}.{example_text}"

        elif avg_rating >= 40:
            # Fair - requires focused attention
            return f"Your content quality is moderate with an average rating of {avg_rating:.1f}/100, requiring attention. To mitigate weak {lowest_dim_info['description']}, you should {lowest_dim_info['recommendation']}.{example_text} This will help move your rating from Fair to Good or Excellent."

        else:
            # Poor - immediate action needed
            return f"Your content quality is low with an average rating of {avg_rating:.1f}/100, requiring immediate action. Critical issue detected in {lowest_dim_info['name']} (scoring only {lowest_dim_score:.1f}/100). You must {lowest_dim_info['recommendation']}.{example_text}"

    else:
        # Fallback if no dimension data available
        return f"Your content has an average rating of {avg_rating:.1f}/100. Comprehensive dimension analysis is needed to provide specific recommendations."
