"""
Executive Summary Generator for Trust Stack Reports

This module provides comprehensive, LLM-powered executive summaries that:
- Analyze all dimensions, not just the weakest
- Provide specific, measurable recommendations
- Reference actual content examples
- Prioritize actions by impact
- Deliver actionable insights instead of generic advice
"""

import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


def generate_executive_summary(
    avg_rating: float,
    dimension_breakdown: Dict[str, Any],
    items: List[Dict[str, Any]],
    sources: List[str],
    model: str = 'gpt-4o-mini',
    use_llm: bool = True
) -> str:
    """
    Generate a comprehensive executive summary for a Trust Stack analysis.

    Args:
        avg_rating: Overall average rating (0-100 scale)
        dimension_breakdown: Dictionary of dimension statistics
        items: List of analyzed content items
        sources: List of data sources used
        model: LLM model to use (supports multi-provider)
        use_llm: If False, use template-based fallback

    Returns:
        Executive summary text (markdown formatted)
    """
    if use_llm:
        try:
            return _generate_llm_summary(
                avg_rating=avg_rating,
                dimension_breakdown=dimension_breakdown,
                items=items,
                sources=sources,
                model=model
            )
        except Exception as e:
            logger.warning(f"LLM summary generation failed, falling back to template: {e}")
            return _generate_template_summary(
                avg_rating=avg_rating,
                dimension_breakdown=dimension_breakdown,
                items=items
            )
    else:
        return _generate_template_summary(
            avg_rating=avg_rating,
            dimension_breakdown=dimension_breakdown,
            items=items
        )


def _generate_llm_summary(
    avg_rating: float,
    dimension_breakdown: Dict[str, Any],
    items: List[Dict[str, Any]],
    sources: List[str],
    model: str
) -> str:
    """
    Generate executive summary using LLM with comprehensive context.

    This provides significantly better quality than templates by:
    - Analyzing patterns across all dimensions
    - Providing specific, context-aware recommendations
    - Referencing actual content issues
    - Prioritizing by impact
    """
    from scoring.llm_client import ChatClient

    # Prepare dimension scores (0-100 scale)
    dimension_keys = ['provenance', 'verification', 'transparency', 'coherence', 'resonance']
    dimension_scores = {
        key: dimension_breakdown.get(key, {}).get('average', 0.5) * 100
        for key in dimension_keys
    }

    # Find weakest and strongest dimensions
    sorted_dims = sorted(dimension_scores.items(), key=lambda x: x[1])
    weakest_3 = sorted_dims[:3]
    strongest_2 = sorted(dimension_scores.items(), key=lambda x: x[1], reverse=True)[:2]

    # Determine rating band
    if avg_rating >= 80:
        band = "🟢 Excellent"
        band_name = "Excellent"
    elif avg_rating >= 60:
        band = "🟡 Good"
        band_name = "Good"
    elif avg_rating >= 40:
        band = "🟠 Fair"
        band_name = "Fair"
    else:
        band = "🔴 Poor"
        band_name = "Poor"

    # Extract low-scoring items for examples
    low_scoring_items = sorted(
        [item for item in items if item.get('final_score', 1.0) < 0.60],
        key=lambda x: x.get('final_score', 0)
    )[:5]

    # Build comprehensive prompt
    prompt = f"""You are an expert Trust Stack analyst writing an executive summary for a brand's content quality audit.

OVERALL PERFORMANCE:
- Average Rating: {avg_rating:.1f}/100
- Rating Band: {band} ({band_name})
- Total Content Analyzed: {len(items)} items
- Data Sources: {', '.join(sources) if sources else 'Multiple sources'}

DIMENSION BREAKDOWN (0-100 scale):
"""

    # Add all dimensions with status indicators
    for dim, score in sorted(dimension_scores.items(), key=lambda x: x[1]):
        status = "🟢" if score >= 80 else "🟡" if score >= 60 else "🟠" if score >= 40 else "🔴"
        prompt += f"  {status} {dim.title()}: {score:.1f}/100\n"

    prompt += f"""
WEAKEST AREAS (Priority for improvement):
"""
    for i, (dim, score) in enumerate(weakest_3, 1):
        gap = 60 - score  # Gap to "Good" threshold
        prompt += f"  {i}. {dim.title()}: {score:.1f}/100 (gap of {gap:.1f} points to Good threshold)\n"

    prompt += f"""
STRONGEST AREAS (Maintain these):
"""
    for i, (dim, score) in enumerate(strongest_2, 1):
        prompt += f"  {i}. {dim.title()}: {score:.1f}/100\n"

    # Add specific problematic content examples
    if low_scoring_items:
        prompt += f"""
PROBLEMATIC CONTENT EXAMPLES (Low Trust items requiring attention):
"""
        for i, item in enumerate(low_scoring_items, 1):
            title = item.get('title', 'Untitled')[:80]
            score = item.get('final_score', 0) * 100
            source = item.get('source', 'unknown')

            # Get URL safely
            meta = item.get('meta', {})
            if isinstance(meta, str):
                try:
                    import json
                    meta = json.loads(meta) if meta else {}
                except Exception:
                    meta = {}
            url = meta.get('source_url', 'No URL') if isinstance(meta, dict) else 'No URL'

            # Extract specific dimension issues
            dim_scores = item.get('dimension_scores', {})
            if dim_scores:
                weak_dims = sorted(
                    [(k, float(v) if v else 0) for k, v in dim_scores.items()],
                    key=lambda x: x[1]
                )[:2]
                weak_dims_str = ', '.join([f"{d[0].title()}({d[1]*100:.0f})" for d in weak_dims if d[1] is not None])
            else:
                weak_dims_str = "Unknown"

            prompt += f"""
  {i}. "{title}"
     Score: {score:.1f}/100 | Source: {source}
     Weak Dimensions: {weak_dims_str}
     URL: {url}
"""

    prompt += f"""
TASK: Write a comprehensive 3-4 paragraph executive summary that:

1. **Opening Assessment** (2-3 sentences):
   - State the overall rating ({avg_rating:.1f}/100) and what the {band_name} rating means
   - Provide immediate context about the content quality across {len(items)} items
   - Set the tone: is this concerning, satisfactory, or excellent?

2. **Root Cause Analysis** (3-4 sentences):
   - Identify the 2-3 weakest dimensions and explain WHY they're scoring low
   - Reference specific patterns you see in the problematic items listed above
   - Explain the IMPACT these weaknesses have on brand trust and credibility
   - Connect the dots between dimension scores and real content issues

3. **Actionable Recommendations** (4-5 sentences):
   - Provide SPECIFIC, MEASURABLE actions to improve the weakest dimensions
   - Prioritize by impact - what will move the overall rating most?
   - Reference actual examples from the problematic items
   - Be concrete with numbers: "Add disclosure tags to the 15 items lacking transparency"
   - Avoid vague advice like "improve quality" - give specific remediation steps

4. **Expected Outcomes** (1-2 sentences):
   - State: "By following the remedies listed below, you can improve your rating from {avg_rating:.1f}/100 to approximately [target range]/100"
   - Mention which dimensions will see the most improvement
   - DO NOT mention specific timeframes (days, weeks, months) - the organization will determine their own pace

CRITICAL REQUIREMENTS:
✓ Be SPECIFIC - use actual numbers, dimensions, and examples from the data
✓ Be ACTIONABLE - provide concrete steps with clear targets
✓ Be PRIORITIZED - explicitly tell them what to fix FIRST
✓ Be REALISTIC - acknowledge platform constraints where relevant
✓ Be QUANTITATIVE - include numbers and targets throughout
✓ Use a professional, direct tone appropriate for executives
✓ Keep it concise but comprehensive (3-4 paragraphs, ~250-300 words)
✓ DO NOT include specific timeframes - just say "By following the remedies listed below"

Write the executive summary now:"""

    # Call LLM
    try:
        client = ChatClient()
        response = client.chat(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=800,
            temperature=0.5
        )

        summary = response.get('content') or response.get('text')

        if not summary:
            raise ValueError("LLM returned empty response")

        # Add model attribution
        provider = response.get('provider', 'LLM')
        summary += f"\n\n*Executive summary generated by {model} ({provider})*"

        return summary

    except Exception as e:
        logger.error(f"LLM summary generation failed: {e}")
        raise


def _generate_template_summary(
    avg_rating: float,
    dimension_breakdown: Dict[str, Any],
    items: List[Dict[str, Any]]
) -> str:
    """
    Fallback template-based summary when LLM is unavailable or disabled.

    This is less sophisticated but provides a baseline summary.
    """
    # Dimension information
    dimension_info = {
        'provenance': {
            'name': 'Provenance',
            'recommendation': 'improve source attribution and content traceability',
            'description': 'source traceability'
        },
        'verification': {
            'name': 'Verification',
            'recommendation': 'add authoritative citations and link to verifiable data',
            'description': 'factual accuracy'
        },
        'transparency': {
            'name': 'Transparency',
            'recommendation': 'add disclosure statements and clear attribution',
            'description': 'disclosure and clarity'
        },
        'coherence': {
            'name': 'Coherence',
            'recommendation': 'ensure consistent messaging across all channels',
            'description': 'cross-channel consistency'
        },
        'resonance': {
            'name': 'Resonance',
            'recommendation': 'increase authentic audience engagement',
            'description': 'audience engagement'
        }
    }

    # Calculate dimension scores
    dimension_keys = ['provenance', 'verification', 'transparency', 'coherence', 'resonance']
    dimension_scores = {
        key: dimension_breakdown.get(key, {}).get('average', 0.5) * 100
        for key in dimension_keys
    }

    # Find lowest performing dimension
    if dimension_scores:
        lowest_dim_key = min(dimension_scores, key=dimension_scores.get)
        lowest_dim_score = dimension_scores[lowest_dim_key]
        lowest_dim_info = dimension_info[lowest_dim_key]
    else:
        return f"Your content has an average rating of {avg_rating:.1f}/100. Comprehensive dimension analysis is needed to provide specific recommendations."

    # Find an example issue
    example_text = ""
    low_items = [item for item in items if item.get('final_score', 1.0) < 0.60]
    if low_items:
        example = low_items[0]
        title = example.get('title', 'Untitled')[:60]
        example_text = f" For example, \"{title}\" scored low in {lowest_dim_info['name']}."

    # Generate summary based on rating band
    if avg_rating >= 80:
        summary = f"""Your brand content demonstrates high quality with an average rating of {avg_rating:.1f}/100 across {len(items)} analyzed items.

To reach even greater heights, consider optimizing {lowest_dim_info['name']} (currently at {lowest_dim_score:.1f}/100) by continuing to {lowest_dim_info['recommendation']}.{example_text}

By following the remedies listed below, you can improve your rating even further and maintain excellence across all Trust Stack dimensions."""

    elif avg_rating >= 60:
        summary = f"""Your content shows solid quality with an average rating of {avg_rating:.1f}/100 across {len(items)} analyzed items.

To improve from Good to Excellent, focus on enhancing {lowest_dim_info['name']} (currently at {lowest_dim_score:.1f}/100) by taking action to {lowest_dim_info['recommendation']}.{example_text}

By following the remedies listed below, you can improve your rating from {avg_rating:.1f}/100 to 80+/100 (Excellent range)."""

    elif avg_rating >= 40:
        summary = f"""Your content quality is moderate with an average rating of {avg_rating:.1f}/100 across {len(items)} analyzed items, requiring attention.

The primary issue is weak {lowest_dim_info['description']}, particularly in {lowest_dim_info['name']} (scoring {lowest_dim_score:.1f}/100). You should {lowest_dim_info['recommendation']}.{example_text}

By following the remedies listed below, you can improve your rating from {avg_rating:.1f}/100 to 60+/100 (Good range)."""

    else:
        summary = f"""Your content quality is low with an average rating of {avg_rating:.1f}/100 across {len(items)} analyzed items, requiring immediate action.

Critical issue detected in {lowest_dim_info['name']} (scoring only {lowest_dim_score:.1f}/100). You must {lowest_dim_info['recommendation']}.{example_text}

By following the remedies listed below, you can improve your rating significantly and establish a foundation for better brand trust."""

    summary += "\n\n*Executive summary generated using template (LLM unavailable)*"

    return summary
