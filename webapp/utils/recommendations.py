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


def get_remedy_for_issue(issue_type: str, dimension: str, issue_items: List[Dict[str, Any]] = None) -> str:
    """
    Get specific remedy recommendation for a detected issue type with contextual examples.

    Args:
        issue_type: Type of issue detected (e.g., "Privacy Policy Link Availability Clarity")
        dimension: Dimension the issue belongs to
        issue_items: Optional list of specific issue instances with evidence

    Returns:
        Specific actionable remedy recommendation with concrete examples
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
        'C2PA/CAI manifest present': 'Implement Content Authenticity Initiative (C2PA) manifests for media files to provide cryptographic provenance. C2PA embeds tamper-proof metadata in images and videos showing who created them, when, and with what tools. This is especially important for AI-generated media.',
        'Canonical URL matches declared source': 'Ensure canonical URLs match the declared source to avoid duplicate content issues. Add proper <link rel="canonical"> tags to all pages pointing to the preferred version. Common issues: HTTP vs HTTPS mismatches, www vs non-www, trailing slashes, URL parameters. Choose one canonical version and stick to it.',
        'Digital watermark/fingerprint detected': 'Add digital watermarks or fingerprints to images and videos for traceability. Watermarks help prove ownership and detect unauthorized use of your media assets.',
        'EXIF/metadata integrity': 'Preserve EXIF metadata in images. Ensure metadata includes creator, date, location (if relevant), and copyright information. Avoid stripping metadata when processing images for web use.',
        'Source domain trust baseline': 'Improve domain reputation. Ensure you have: valid SSL certificate (HTTPS), accessible privacy policy, clear contact information, professional domain age, and no association with spam or malware. Consider third-party verification badges.',
        'Schema Compliance': 'Implement schema.org structured data markup (JSON-LD) for all content types. This helps search engines understand your content and can improve visibility and trust signals.',
        'Metadata Completeness': 'Add complete metadata to all pages. Required elements: title tag, meta description, author attribution, publication/modified date, Open Graph tags (og:title, og:description, og:image), and Twitter Card tags.',

        # Verification
        'Ad/Sponsored Label Consistency': 'Clearly label all sponsored content and advertisements. Use consistent, prominent labels: "Sponsored", "Ad", "Paid Partnership", or "Promoted". Ensure labels appear: on social media posts, in email campaigns, on website promotional content. Labels must be visible before user interaction.',
        'Agent Safety Guardrail Presence': 'Implement content safety guardrails and moderation policies for AI systems. Document publicly: what topics AI will/won\'t discuss, how harmful content is filtered, escalation procedures. Test guardrails regularly with adversarial inputs.',
        'Claim-to-source traceability': 'Add citations and inline references for all factual claims. Each claim should link to an authoritative, verifiable source (research papers, official statistics, primary sources). Avoid unsourced assertions.',
        'Engagement Authenticity Ratio': 'Monitor engagement metrics for bot activity and fake engagement. Look for: sudden spikes in followers/likes, accounts with no profile pictures, generic comments, engagement from inactive accounts. Remove fake engagement and report bot accounts. Focus on organic community building.',
        'Influencer/partner identity verified': 'Verify all influencer and partner identities before collaboration. Check for: platform verification badges (blue checkmarks), consistent presence across platforms, genuine audience engagement, professional credentials. Display verification status on partnership content.',
        'Review Authenticity Confidence': 'Implement verified review systems with purchase verification. Flag suspicious patterns: multiple reviews from same IP, identical phrasing, reviews posted in rapid succession, overly promotional language. Consider implementing CAPTCHA or email verification for reviewers.',
        'Seller & Product Verification Rate': 'Verify seller identities and product authenticity. Implement: business license verification, product authenticity certificates, GTIN/UPC matching, seller reputation scoring. Display verification badges prominently on product pages.',
        'Verified purchaser review rate': 'Mark reviews from verified purchasers with a badge or label. Implement purchase verification by matching order numbers to review submissions. Prioritize verified purchase reviews in display rankings.',

        # Transparency
        'AI Explainability Disclosure': 'When using AI, explain how it works and what data it uses. Create an AI transparency page covering: what AI systems you use, how they make decisions, what data they process, how users can opt out. Add "Powered by AI" disclosures on AI-generated content.',
        'AI-generated/assisted disclosure present': 'Clearly disclose when content is AI-generated or AI-assisted. Add disclosure statements prominently: "This content was created with AI assistance" or "AI-generated summary". Use visual indicators (badges, labels) and schema.org markup (digital-document-permission property).',
        'Bot Disclosure + Response Audit': 'Clearly identify bot-generated responses with disclaimers like "This is an automated response" or "AI assistant". Ensure bots: self-identify in first interaction, explain their limitations, offer clear path to human support. Audit bot responses for accuracy and helpfulness.',
        'Caption/Subtitle Availability & Accuracy': 'Add accurate captions and subtitles to all video content. Use professional captioning services or human review to verify auto-generated captions. Ensure captions include: speaker identification, relevant sound effects, music descriptions for accessibility.',
        'Data source citations for claims': 'Add inline citations for all data-driven claims. Each statistic, fact, or research finding should link to: primary source (research paper, official report), publication date, credible organization. Format citations consistently (footnotes, inline links, or reference section).',
        'Privacy policy link availability & clarity': 'Add a clear Privacy Policy link to your footer and top navigation. Ensure the policy: is written in plain language (avoid legalese), clearly explains data collection practices, is updated regularly (review annually), is mobile-friendly. Consider adding a summary or FAQ section.',

        # Coherence
        'Brand voice consistency score': 'Audit all content for consistent brand voice and tone. Create written brand voice guidelines covering: vocabulary preferences, sentence structure, formality level, personality traits (e.g., professional vs. casual). Train all content creators on these guidelines and review content before publishing.',
        'Broken link rate': 'Regularly audit and fix broken links using automated link checkers. Recommended tools: Broken Link Checker, Screaming Frog, or Ahrefs. Run checks weekly and fix broken links within 24-48 hours. Set up monitoring alerts for broken links.',
        'Claim consistency across pages': 'Ensure factual claims are consistent across all pages and channels. Identify contradictions where different pages state different facts, figures, or positions. Create a content style guide with a single source of truth for key claims (pricing, product specs, company facts).',
        'Email-Asset Consistency Check': 'Standardize email templates to match website branding. Ensure consistency in: logo usage, color schemes, typography, button styles, promotional claims, pricing. Verify that email links point to landing pages with matching offers and messaging.',
        'Engagement-to-Trust Correlation': 'Monitor how engagement metrics (CTR, time on site, bounce rate) correlate with trust indicators. Investigate pages with high engagement but low trust scores, or vice versa. This may indicate misleading headlines, clickbait, or poor user experience.',
        'Multimodal Consistency Score': 'Ensure text, images, videos, and audio tell a consistent story. Check that: video transcripts match spoken content, image captions accurately describe visuals, infographic data matches text claims. Avoid contradictions between different media types on the same page.',
        'Temporal continuity (versions)': 'Maintain version history for content updates. Display "Last updated" dates prominently. For significant changes, provide a change log or "What\'s new" section. Consider using version control for important documents and showing edit history.',
        'Trust Fluctuation Index': 'Monitor trust score changes over time using analytics. Investigate sudden drops or spikes. Common causes: security incidents, negative press, policy changes, service outages. Set up alerts for trust score changes >10% and respond quickly.',

        # Resonance
        'Community Alignment Index': 'Engage with your community authentically and align content with community values. Monitor: social media sentiment, comment tone, shared values in discussions. Address misalignment by: listening to community feedback, adjusting messaging to reflect audience concerns, avoiding tone-deaf marketing during sensitive periods.',
        'Creative recency vs trend': 'Stay current with relevant trends while maintaining brand authenticity. Audit content freshness quarterly. Update outdated statistics, remove references to past events/trends, refresh visuals to current design standards. Balance trending topics with evergreen content.',
        'Cultural Context Alignment': 'Ensure content is culturally appropriate and relevant for target markets. Before launching in new regions: research local customs and sensitivities, verify color/symbol meanings, check for cultural references that may not translate. Work with cultural consultants and native speakers for diverse markets.',
        'Language/locale match': 'Provide content in appropriate languages for target markets. Avoid auto-translation for critical content. Use professional translation services with native speakers. Ensure: correct date/time formats, appropriate currency symbols, culturally relevant examples, localized imagery.',
        'Personalization relevance (embedding similarity)': 'Improve content personalization to better match user interests while respecting privacy. Analyze: user behavior patterns, content topic clusters, recommendation accuracy. Improve relevance by: better user preference models, contextual content suggestions, A/B testing personalization algorithms.',
        'Readability grade level fit': 'Adjust content readability to match your target audience. Test with tools like Flesch-Kincaid or Hemingway Editor. For general audiences: aim for 8th-10th grade reading level, use short sentences (15-20 words), choose simple words over jargon. For technical audiences: adjust accordingly but maintain clarity.',
        'Tone & sentiment appropriateness': 'Ensure content tone matches context and audience expectations. Avoid overly promotional language in educational content. Match tone to platform: professional on LinkedIn, casual on TikTok. Review content for: appropriate emotion level, avoiding manipulation tactics, balancing enthusiasm with authenticity.'
    }

    base_remedy = remedies.get(issue_type, f'Address this {dimension} issue by improving content quality and adding relevant metadata.')

    # Add specific examples from evidence if provided
    if issue_items and len(issue_items) > 0:
        examples = []
        max_examples = 3  # Limit to first 3 examples for clarity

        for item in issue_items[:max_examples]:
            evidence = item.get('evidence', '').strip()
            title = item.get('title', '').strip()
            url = item.get('url', '').strip()

            if evidence:
                # Create a specific example with evidence
                example_parts = []
                if title:
                    example_parts.append(f"**{title}**")
                example_parts.append(f"{evidence}")
                if url:
                    # Truncate long URLs for readability
                    display_url = url if len(url) <= 60 else url[:57] + "..."
                    example_parts.append(f"({display_url})")

                examples.append(" - ".join(example_parts))
            elif title or url:
                # If no evidence but have title/url, still show it
                if title and url:
                    display_url = url if len(url) <= 60 else url[:57] + "..."
                    examples.append(f"**{title}** ({display_url})")
                elif title:
                    examples.append(f"**{title}**")

        if examples:
            example_text = "\n\n**Specific issues detected:**\n" + "\n".join(f"• {ex}" for ex in examples)

            # Show count if there are more issues
            total_count = len(issue_items)
            if total_count > max_examples:
                example_text += f"\n\n*...and {total_count - max_examples} more instance{'s' if total_count - max_examples > 1 else ''}*"

            return base_remedy + example_text

    return base_remedy


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
