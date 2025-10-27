"""
Markdown report generator for AR tool
Creates markdown reports for easy sharing and documentation
"""

from typing import Dict, Any, List, Optional
import math
import logging
from datetime import datetime
import os
import re
import json
from statistics import mean

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

logger = logging.getLogger(__name__)

try:
    # Optional: use scikit-learn TF-IDF if installed for better scoring
    from sklearn.feature_extraction.text import TfidfVectorizer
    _HAVE_SKLEARN = True
except Exception:
    TfidfVectorizer = None
    _HAVE_SKLEARN = False


def _summarize_text(text: str, max_lines: int = 2, max_chars: int = 240, meta_desc: str = None) -> str:
    """Produce a short summary for text.

    Strategy:
      - Prefer meta/OG description when available and sufficiently long.
      - Clean boilerplate/UI fragments.
      - Extract 1-2 representative sentences using TF-IDF/TextRank-style scoring.
      - Enforce max_chars safely.
    """
    if not text:
        return ''

    # 1) Prefer meta description if provided
    if meta_desc:
        md = meta_desc.strip()
        if len(md) >= 30:
            return _trim_summary(md, max_chars)

    # 2) Clean input text
    clean = _clean_text(text)
    if not clean:
        return ''
    if len(clean) <= max_chars:
        return clean

    # 3) Split into candidate sentences
    sentences = _split_sentences(clean)
    if not sentences:
        return _trim_summary(clean, max_chars)
    if len(sentences) <= max_lines:
        joined = ' '.join(sentences)
        return _trim_summary(joined, max_chars)

    # 4) Score and select best sentences
    chosen = _score_and_select(sentences, max_lines=max_lines)

    # Preserve original order
    ordered = [s for s in sentences if s in chosen]
    out = ' '.join(ordered[:max_lines])
    return _trim_summary(out, max_chars)


def _clean_text(text: str) -> str:
    s = html_unescape(text)
    s = re.sub(r"\s+", ' ', s).strip()
    # remove common UI/boilerplate fragments
    stop_phrases = [
        'Learn more', 'Read more', 'Close', 'Cookie settings', 'Subscribe',
        'Sign in', 'Log in', 'What can I help with', 'Show more'
    ]
    for p in stop_phrases:
        s = s.replace(p, '')
    # Drop very short fragments and multilingual short UI snippets often scraped from interactive widgets
    # e.g., small phrases or single-word bullets
    s = re.sub(r"(?:\b[A-Za-z]{1,3}\b\s*){1,4}", '', s)
    # Remove leftover sequences of non-word punctuation often found in nav bars
    s = re.sub(r"[\-_=]{2,}", ' ', s)
    s = s.strip(' \t\n\r\u200b\ufeff')
    return s


def html_unescape(text: str) -> str:
    try:
        import html
        return html.unescape(text)
    except Exception:
        return text


def _split_sentences(text: str) -> List[str]:
    # Simple but pragmatic sentence splitter
    parts = re.split(r'(?<=[\.\!\?])\s+', text)
    parts = [p.strip() for p in parts if len(p.strip()) > 10]
    return parts


def clean_text_for_llm(meta: Dict[str, Any]) -> str:
    """Build a reasonable text blob for LLM summarization from metadata dict."""
    parts = []
    if not isinstance(meta, dict):
        return ''
    for key in ('title', 'name', 'headline'):
        v = meta.get(key)
        if v:
            parts.append(str(v))
    for key in ('description', 'snippet', 'summary', 'body'):
        v = meta.get(key)
        if v:
            parts.append(str(v))
    # fallback to URL if nothing else
    url = meta.get('source_url') or meta.get('url')
    if url:
        parts.append(url)
    return '\n\n'.join(parts)


def _score_and_select(sentences: List[str], max_lines: int = 2) -> List[str]:
    # Use sklearn TF-IDF if available, otherwise a simple heuristic
    scores = []
    if _HAVE_SKLEARN and len(sentences) > 0:
        try:
            vec = TfidfVectorizer(stop_words='english')
            X = vec.fit_transform(sentences)
            scores = X.sum(axis=1).A1.tolist()
        except Exception:
            scores = [_simple_score(s) for s in sentences]
    else:
        scores = [_simple_score(s) for s in sentences]

    ranked = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
    selected = [sentences[i] for i in ranked[: max_lines * 3]]
    # dedupe and keep up to max_lines
    out = []
    seen = set()
    for s in selected:
        key = s.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(s)
        if len(out) >= max_lines:
            break
    return out


def _simple_score(s: str) -> float:
    words = re.findall(r"\w+", s.lower())
    if not words:
        return 0.0
    freq = {}
    for w in words:
        freq[w] = freq.get(w, 0) + 1
    score = sum(1.0 / math.sqrt(v) for v in freq.values())
    score *= min(1.5, len(words) / 10)
    return score


def _trim_summary(text: str, max_chars: int) -> str:
    t = text.strip()
    if len(t) <= max_chars:
        return t
    cut = t[: max_chars]
    # try to end at sentence boundary
    idx = cut.rfind('.')
    if idx > int(max_chars * 0.5):
        return cut[: idx + 1].strip() + '…'
    # else cut on word boundary
    safe = cut.rsplit(' ', 1)[0].rstrip('.,;:')
    return safe + '…'


def _llm_summarize(text: str, *, model: str = 'gpt-3.5-turbo', max_words: int = 120) -> Optional[str]:
    """Optional abstractive summarizer using internal ChatClient wrapper.

    Returns None if LLM client is not available/configured.
    """
    try:
        # Lazy import to avoid hard dependency
        from scoring.llm_client import ChatClient
    except Exception:
        return None
    prompt = (
        f"Write a concise {max_words}-word human-readable summary (1-2 lines) of the following content.\n\nContent:\n{text}\n\nSummary:")
    client = ChatClient()
    try:
        resp = client.chat(model=model, messages=[{"role": "user", "content": prompt}], max_tokens=300)
        return resp.get('text') or resp.get('content') or None
    except Exception:
        return None

class MarkdownReportGenerator:
    """Generates Markdown reports for AR analysis"""
    
    def generate_report(self, report_data: Dict[str, Any], output_path: str) -> str:
        """
        Generate Markdown report from report data
        
        Args:
            report_data: Dictionary containing report data
            output_path: Path to save the Markdown file
            
        Returns:
            Path to generated Markdown file
        """
        logger.info(f"Generating Markdown report: {output_path}")
        
        markdown_content = self._build_markdown_content(report_data)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        
        logger.info(f"Markdown report generated successfully: {output_path}")
        return output_path
    
    def _build_markdown_content(self, report_data: Dict[str, Any]) -> str:
        """Build the complete markdown content"""
        content = []
        
        # Title and metadata
        content.append(self._create_header(report_data))
        content.append(self._create_metadata(report_data))
        
        # Executive summary
        content.append(self._create_executive_summary(report_data))
        
        # Authenticity Ratio analysis
        content.append(self._create_ar_analysis(report_data))
        
        # Dimension breakdown
        content.append(self._create_dimension_breakdown(report_data))
        
        # Classification analysis
        content.append(self._create_classification_analysis(report_data))
        
        # Recommendations
        content.append(self._create_recommendations(report_data))

        # Appendix (per-item diagnostics)
        content.append(self._create_appendix(report_data))

        # Footer
        content.append(self._create_footer(report_data))

        return "\n\n".join(content)
    
    def _create_header(self, report_data: Dict[str, Any]) -> str:
        """Create report header"""
        brand_id = report_data.get('brand_id', 'Unknown Brand')
        run_id = report_data.get('run_id', 'unknown')
        generated_at = report_data.get('generated_at', datetime.now().isoformat())
        return f"# Authenticity Ratio™ Report\n\n## Brand: {brand_id}\n\n*Run ID:* `{run_id}`  \n*Generated:* {generated_at}"
    
    def _create_metadata(self, report_data: Dict[str, Any]) -> str:
        """Create metadata section"""
        run_id = report_data.get('run_id', 'Unknown')
        generated_at = report_data.get('generated_at', datetime.now().isoformat())
        rubric_version = report_data.get('rubric_version', 'v1.0')
        
        return f"""## Report Metadata

| Field | Value |
|-------|-------|
| Report ID | `{run_id}` |
| Generated | {generated_at} |
| Analysis Period | Current Run |
| Data Sources | {', '.join(report_data.get('sources', [])) if report_data.get('sources') else 'Unknown'} |
| Rubric Version | {rubric_version} |"""
    
    def _create_executive_summary(self, report_data: Dict[str, Any]) -> str:
        """Create executive summary section"""
        ar_data = report_data.get('authenticity_ratio', {})
        total_items = ar_data.get('total_items', 0)
        authentic_items = ar_data.get('authentic_items', 0)
        suspect_items = ar_data.get('suspect_items', 0)
        inauthentic_items = ar_data.get('inauthentic_items', 0)
        ar_pct = ar_data.get('authenticity_ratio_pct', 0.0)
        extended_ar = ar_data.get('extended_ar_pct', 0.0)

        # Plain English interpretation paragraph (templated)
        interp = (
            f"Out of {total_items} items analyzed, {ar_pct:.1f}% met authenticity standards, "
            f"indicating that most brand-related content lacks verifiable provenance or transparency. "
            f"The low Verification and Transparency scores suggest the brand’s messaging is being reused or misrepresented by third parties."
        )

        # Short one-line summary for non-technical stakeholders
        executive_one_liner = f"Executive Summary: {ar_pct:.1f}% Core AR — {total_items} items analyzed."

        # Build images (heatmap, trendline, channel breakdown) and include them if created
        visuals_md = []
        # Heatmap from dimension breakdown
        heatmap_path = self._create_dimension_heatmap(report_data)
        if heatmap_path:
            visuals_md.append(f"![5D Heatmap]({heatmap_path})")

        # Trendline from previous reports (optional)
        trend_path = self._create_trendline(report_data)
        if trend_path:
            visuals_md.append(f"![AR Trend]({trend_path})")

        # Channel breakdown (if provided)
        channel_path = self._create_channel_breakdown(report_data)
        if channel_path:
            visuals_md.append(f"![Channel Breakdown]({channel_path})")

        # Content-type breakdown visualization
        ctype_path = self._create_content_type_breakdown(report_data)
        if ctype_path:
            visuals_md.append(f"![Content Type Breakdown]({ctype_path})")

        visuals_block = "\n\n".join(visuals_md)

        # Include a short list of example items (up to 3) for the executive.
        # Prefer the detailed per-item diagnostics from the appendix when available
        # so we can show title, description, short analysis, and link.
        examples_md = ''
        appendix = report_data.get('appendix') or []
        items = report_data.get('items', [])
        max_examples = 3

        def _get_meta_from_item(it):
            meta = it.get('meta') or {}
            # meta may be a JSON string in some cases
            if isinstance(meta, str):
                try:
                    import json as _json
                    meta = _json.loads(meta) if meta else {}
                except Exception:
                    meta = {}
            return meta if isinstance(meta, dict) else {}

        # Choose candidate pool: prefer appendix (richer), fallback to items
        pool = appendix if appendix else items
        if pool:
            # Build a mapping of sources in preferred order
            preferred_sources = report_data.get('sources') or sorted({it.get('source') for it in pool if it.get('source')})

            selected = []
            # Try to pick at least one example per source (up to max_examples)
            for src in preferred_sources:
                if len(selected) >= max_examples:
                    break
                for it in pool:
                    if it.get('source') == src and it not in selected:
                        selected.append(it)
                        break

            # Fill remaining slots with top-scoring items (highest final_score)
            if len(selected) < max_examples:
                remaining = [it for it in pool if it not in selected]
                try:
                    remaining.sort(key=lambda x: float(x.get('final_score') or 0.0), reverse=True)
                except Exception:
                    pass
                for it in remaining:
                    if len(selected) >= max_examples:
                        break
                    selected.append(it)

            example_lines = []
            for ex in selected:
                meta = _get_meta_from_item(ex)
                # Robust title fallback: meta title/name/og/headline, then first words of body, then content_id
                title = (
                    meta.get('title') or meta.get('name') or meta.get('headline') or meta.get('og:title')
                    or (meta.get('source_url') if meta.get('source_url') and isinstance(meta.get('source_url'), str) else None)
                )
                if not title:
                    # Try to derive from body/snippet
                    body_text = (meta.get('body') or meta.get('description') or meta.get('snippet') or ex.get('body') or '')
                    if body_text:
                        title = ' '.join(body_text.strip().split()[:7]) + ('...' if len(body_text.split()) > 7 else '')
                    else:
                        title = ex.get('content_id')
                score = float(ex.get('final_score', 0.0) or 0.0)
                label = (ex.get('label') or '').title()
                # description/snippet
                raw_desc = meta.get('description') or meta.get('snippet') or meta.get('summary') or ''
                # Optionally use LLM for executive examples (small curated set)
                use_llm = bool(report_data.get('use_llm_for_examples') or report_data.get('use_llm_for_descriptions'))
                desc = None
                if use_llm:
                    # prefer LLM abstractive summary for the executive example
                    try:
                        desc_llm = _llm_summarize(raw_desc or clean_text_for_llm(meta), model=report_data.get('llm_model', 'gpt-3.5-turbo'), max_words=120)
                        if desc_llm:
                            # Append an explicit provenance label for clarity
                            desc = desc_llm.strip()
                            desc += f" (Generated by {report_data.get('llm_model', 'gpt-3.5-turbo')})"
                    except Exception:
                        desc = None
                if not desc:
                    # fallback to extractive summarizer
                    # Prefer body when snippet is thin/noisy
                    body_text = meta.get('body') or ex.get('body') or ''
                    desc = _summarize_text(raw_desc or body_text, max_lines=2, max_chars=240)

                # Short analysis: list top 2 dimension signals
                dims = ex.get('dimension_scores') or {}
                dims_parsed = {}
                if isinstance(dims, dict):
                    for k, v in dims.items():
                        try:
                            dims_parsed[k] = float(v)
                        except Exception:
                            pass
                top_dims = sorted(dims_parsed.items(), key=lambda x: x[1], reverse=True)[:2]
                top_dims_str = ', '.join([f"{k.title()}: {v:.2f}" for k, v in top_dims]) if top_dims else ''
                analysis = f"Label: {label} ({score:.1f})"
                if top_dims_str:
                    analysis += f" — Key signals: {top_dims_str}"

                # Ensure we expose some useful URL when available (terms/privacy may indicate domain)
                url = meta.get('source_url') or meta.get('url') or meta.get('source_link') or ''
                if not url:
                    # Try platform id or fall back to terms/privacy links if they point to same site
                    url = meta.get('platform_id') or ''
                    if not url:
                        # prefer privacy/terms as a last-resort visited URL
                        url = meta.get('privacy') or meta.get('terms') or ''

                line = f"- **{title}**\n\n  {analysis}"
                if desc:
                    line += f"\n\n  Description: {desc}"
                if url:
                    line += f"\n\n  Link: {url}"

                example_lines.append(line)

            examples_md = "\n\n**Examples from this run:**\n" + "\n\n".join(example_lines) + "\n"

        score_based = report_data.get('score_based_ar_pct')

        # Add a short definitions block to explain Core vs Extended AR
        defs_block = (
            "**Definitions:**\n\n"
            "- Core AR (classification): Percentage of items explicitly classified as 'Authentic' by the classifier (count of Authentic / total * 100).\n"
            "- Score-based AR (mean 5D score): The arithmetic mean of the per-item 5D composite scores (0-100). Useful as a continuous measure.\n"
            "- Extended AR: A blended metric that combines classification counts and score-based signals (rubric-dependent adjustments).\n"
        )

        # Small computation table to show the numbers used to form Core/Extended AR
        computation_table = (
            "\n**Computation (values used):**\n\n"
            f"- Total items = {total_items}\n"
            f"- Authentic = {authentic_items}\n"
            f"- Suspect = {suspect_items}\n"
            f"- Inauthentic = {inauthentic_items}\n"
            f"- Core AR = Authentic / Total * 100 = {ar_pct:.1f}%\n"
            f"- Score-based AR (mean 5D) = {score_based:.1f}%\n"
            f"- Extended AR = rubric-adjusted blend (see AR Analysis section) = {extended_ar:.1f}%\n"
        )

        return f"""## Summary

**Core Authenticity Ratio (classification):** {ar_pct:.1f}%  
**Score-based Authenticity Ratio (mean 5D score):** {score_based:.1f}%  
**Extended Authenticity Ratio:** {extended_ar:.1f}%  
**Total content analyzed:** {total_items:,}  
**Distribution:** Authentic: {authentic_items:,} | Suspect: {suspect_items:,} | Inauthentic: {inauthentic_items:,}

{defs_block}

{computation_table}

{interp}

**Executive (one-liner):** {executive_one_liner}

{examples_md}

{visuals_block}

"""
    
    def _create_ar_analysis(self, report_data: Dict[str, Any]) -> str:
        """Create Authenticity Ratio analysis section"""
        ar_data = report_data.get('authenticity_ratio', {})
        # Build per-dimension subsections
        dimension_breakdown = report_data.get('dimension_breakdown', {})
        dimension_sections = []
        defs = {
            'provenance': 'How traceable and source-verified the content is.',
            'verification': 'Alignment with verifiable brand or regulatory data.',
            'transparency': 'Clarity of ownership, disclosure, and intent.',
            'coherence': 'Consistency of messaging and tone with known brand assets.',
            'resonance': 'Audience engagement that aligns with brand values.'
        }

        for dim in ['provenance', 'verification', 'transparency', 'coherence', 'resonance']:
            stats = dimension_breakdown.get(dim, {})
            avg = stats.get('average', 0.0)
            lo = stats.get('min', 0.0)
            hi = stats.get('max', 0.0)
            interp = ''
            # Use provided plain-language interpretations from spec where helpful
            if dim == 'provenance':
                interp = 'Moderate provenance indicates some content includes brand-linked metadata or source signals (e.g., official product listings or verified user accounts), but most lacks clear traceability.'
            elif dim == 'verification':
                interp = 'Verification is the weakest pillar. Few posts or listings reference authoritative identifiers (such as verified domains, SSL certificates, or official brand handles).'
            elif dim == 'transparency':
                interp = 'Transparency remains low, likely due to missing disclosure tags or ambiguous authorship.'
            elif dim == 'coherence':
                interp = 'Inconsistent tone or visual style may indicate unofficial reshares or imitations.'
            elif dim == 'resonance':
                interp = 'Resonance is relatively stable but not strongly correlated with authenticity, suggesting popular content may not be brand-originated.'

            section = f"### {dim.title()}\n\n**Definition:** {defs.get(dim)}\n\n**Key Stats:** Average: {avg:.3f} | Range: {lo:.2f}–{hi:.2f}\n\n**Interpretation:** {interp}\n"
            dimension_sections.append(section)

        dimension_text = '\n'.join(dimension_sections)

        # Summary block
        total_items = ar_data.get('total_items', 0)
        authentic_items = ar_data.get('authentic_items', 0)
        suspect_items = ar_data.get('suspect_items', 0)
        inauthentic_items = ar_data.get('inauthentic_items', 0)

        summary = f"""## Authenticity Ratio Analysis\n\n**Total:** {total_items:,} | **Authentic:** {authentic_items} | **Suspect:** {suspect_items} | **Inauthentic:** {inauthentic_items}\n\n**Core AR:** {ar_data.get('authenticity_ratio_pct', 0.0):.1f}% | **Extended AR:** {ar_data.get('extended_ar_pct', 0.0):.1f}%\n\n{dimension_text}"""

        return summary
    
    def _create_dimension_breakdown(self, report_data: Dict[str, Any]) -> str:
        """Create dimension breakdown section"""
        dimension_data = report_data.get('dimension_breakdown', {})
        
        if not dimension_data:
            return "## 5D Trust Dimensions Analysis\n\n*No dimension data available*"
        
        # Create dimension scores table
        table_rows = ["| Dimension | Average | Min | Max | Std Dev |"]
        table_rows.append("|-----------|---------|-----|-----|---------|")
        
        for dimension, stats in dimension_data.items():
            table_rows.append(f"| {dimension.title()} | {stats.get('average', 0):.3f} | {stats.get('min', 0):.3f} | {stats.get('max', 0):.3f} | {stats.get('std_dev', 0):.3f} |")
        
        dimension_table = "\n".join(table_rows)
        
        # Add dimension descriptions
        descriptions = {
            'provenance': 'Origin clarity, traceability, and metadata completeness',
            'verification': 'Factual accuracy and consistency with trusted sources',
            'transparency': 'Clear disclosures and honest communication',
            'coherence': 'Consistency with brand messaging and professional quality',
            'resonance': 'Cultural fit and authentic engagement patterns'
        }
        
        dimension_details = []
        for dimension, stats in dimension_data.items():
            avg_score = stats.get('average', 0)
            description = descriptions.get(dimension, 'No description available')
            
            # Add performance indicator
            if avg_score >= 0.8:
                indicator = "🟢 Excellent"
            elif avg_score >= 0.6:
                indicator = "🟡 Good"
            elif avg_score >= 0.4:
                indicator = "🟠 Moderate"
            else:
                indicator = "🔴 Poor"
            
            dimension_details.append(f"**{dimension.title()}** ({indicator}): {description}")
        
        return f"""## 5D Trust Dimensions Analysis

### Dimension Scores

{dimension_table}

### Dimension Performance

{chr(10).join(dimension_details)}

### Scoring Methodology

Each dimension is scored on a scale of 0.0 to 1.0:
- **0.8-1.0**: Excellent performance
- **0.6-0.8**: Good performance  
- **0.4-0.6**: Moderate performance
- **0.0-0.4**: Poor performance

The overall Authenticity Ratio is calculated as a weighted average of all five dimensions, with each dimension contributing 20% to the final score."""
    
    def _create_classification_analysis(self, report_data: Dict[str, Any]) -> str:
        """Create classification analysis section"""
        classification_data = report_data.get('classification_analysis', {})
        
        if not classification_data:
            return "## Content Classification Analysis\n\n*No classification data available*"
        
        dist = classification_data.get('classification_distribution', {})
        total = sum(dist.values())
        
        if total == 0:
            return "## Content Classification Analysis\n\n*No classification data available*"
        
        # Create classification summary
        authentic_pct = dist.get('authentic', 0) / total * 100
        suspect_pct = dist.get('suspect', 0) / total * 100
        inauthentic_pct = dist.get('inauthentic', 0) / total * 100
        
        return f"""## Content Classification Analysis

### Classification Distribution

| Classification | Count | Percentage | Status |
|----------------|-------|------------|---------|
| **Authentic** | {dist.get('authentic', 0):,} | {authentic_pct:.1f}% | ✅ Strengthens brand |
| **Suspect** | {dist.get('suspect', 0):,} | {suspect_pct:.1f}% | ⚠️ Needs verification |
| **Inauthentic** | {dist.get('inauthentic', 0):,} | {inauthentic_pct:.1f}% | ❌ Requires attention |

### Classification Definitions

- **Authentic**: Content that meets all authenticity criteria with high confidence
- **Suspect**: Content that may be genuine but lacks sufficient verification
- **Inauthentic**: Content that fails authenticity criteria or shows signs of manipulation

### Action Items by Classification

#### 🟢 Authentic Content ({dist.get('authentic', 0):,} items)
- **Action**: Amplify and promote
- **Strategy**: Use as examples of authentic brand engagement
- **Goal**: Increase visibility and reach

#### 🟡 Suspect Content ({dist.get('suspect', 0):,} items)  
- **Action**: Investigate and verify
- **Strategy**: Apply additional verification steps
- **Goal**: Move to authentic classification or flag for removal

#### 🔴 Inauthentic Content ({dist.get('inauthentic', 0):,} items)
- **Action**: Remove or flag for removal
- **Strategy**: Report to platform administrators
- **Goal**: Eliminate from brand ecosystem"""
    
    def _create_recommendations(self, report_data: Dict[str, Any]) -> str:
        """Create recommendations section"""
        ar_data = report_data.get('authenticity_ratio', {})
        ar_pct = ar_data.get('authenticity_ratio_pct', 0.0)
        
        # Generate recommendations based on AR score
        if ar_pct >= 80:
            priority = "Low"
            focus = "Maintain current standards"
            recommendations = [
                "Continue monitoring content quality",
                "Amplify authentic content examples",
                "Share best practices across teams"
            ]
        elif ar_pct >= 60:
            priority = "Medium"
            focus = "Improve verification processes"
            recommendations = [
                "Implement stricter content verification",
                "Increase monitoring of suspect content",
                "Develop content guidelines for brand teams"
            ]
        elif ar_pct >= 40:
            priority = "High"
            focus = "Address authenticity issues"
            recommendations = [
                "Immediate review of inauthentic content",
                "Implement content moderation protocols",
                "Train teams on authenticity standards",
                "Consider content removal campaigns"
            ]
        else:
            priority = "Critical"
            focus = "Emergency authenticity intervention"
            recommendations = [
                "Immediate removal of inauthentic content",
                "Crisis communication strategy",
                "Full audit of content creation processes",
                "External authenticity consultation",
                "Platform partnership for content verification"
            ]
        
        recommendations_list = "\n".join([f"- {rec}" for rec in recommendations])
        
        return f"""## Recommendations

### Priority Level: {priority}
**Focus Area**: {focus}

### Recommended Actions

{recommendations_list}

### Next Steps

1. **Immediate (1-7 days)**:
   - Review and address inauthentic content
   - Implement content monitoring alerts

2. **Short-term (1-4 weeks)**:
   - Develop content authenticity guidelines
   - Train teams on verification processes

3. **Long-term (1-3 months)**:
   - Establish ongoing monitoring systems
   - Create authenticity performance metrics
   - Regular Authenticity Ratio reporting

### Success Metrics

- Increase Authenticity Ratio by 10+ percentage points
- Reduce inauthentic content by 50%+
- Improve average dimension scores across all 5D metrics"""
    
    def _create_footer(self, report_data: Dict[str, Any]) -> str:
        """Create report footer"""
        generated_at = report_data.get('generated_at', datetime.now().isoformat())
        brand_id = report_data.get('brand_id', 'Unknown Brand')
        
        return f"""---

## About This Report

**Authenticity Ratio™** is a proprietary KPI that measures authentic vs. inauthentic brand-linked content across channels. This analysis provides actionable insights for brand health and content strategy.

### Methodology

This report analyzes content using the 5D Trust Dimensions framework:
- **Provenance**: Origin clarity and traceability
- **Verification**: Factual accuracy and consistency  
- **Transparency**: Clear disclosures and honesty
- **Coherence**: Consistency with brand messaging
- **Resonance**: Cultural fit and authentic engagement

### Data Sources

This run used the following data sources: {', '.join(report_data.get('sources', [])) if report_data.get('sources') else 'Unknown'}.\
The tool supports additional sources (Reddit, Amazon, YouTube, Yelp) in other runs; this section is populated per-run.

### Report Generation

- **Generated**: {generated_at}
- **Brand**: {brand_id}
- **Version**: Authenticity Ratio Tool v1.0

---

*This report is confidential and proprietary. For questions or additional analysis, contact the Authenticity Ratio team.*"""

    def _create_appendix(self, report_data: Dict[str, Any]) -> str:
        """Render an appendix with per-item diagnostics if available"""
        appendix = report_data.get('appendix', []) or []

        # If pipeline didn't attach a rich appendix, fall back to the items list
        # which contains the minimal per-item summaries (meta, final_score, label).
        items_fallback = report_data.get('items', []) or []
        if not appendix and not items_fallback:
            return "## Appendix: Per-item Diagnostics\n\n*No per-item diagnostics available for this run.*"

    # Support a mode where only the most egregious examples are shown.
        egregious_only = bool(report_data.get('appendix_egregious_only') or report_data.get('appendix_mode') == 'egregious')
        limit = int(report_data.get('appendix_limit', 10) or 10)
        if egregious_only:
            # Define egregious as items labeled 'inauthentic' or with very low final_score
            def is_egregious(it: Dict[str, Any]) -> bool:
                lbl = (it.get('label') or '').lower()
                final = float(it.get('final_score') or 0.0)
                return lbl == 'inauthentic' or final <= 40.0

            filtered = [it for it in appendix if is_egregious(it)]
            # Sort by ascending final score (worst first)
            filtered.sort(key=lambda x: float(x.get('final_score') or 0.0))
            appendix = filtered[:limit]

        lines = ["## Appendix: Per-item Diagnostics\n\nThis appendix lists every analyzed item with a concise per-item diagnostic including title, description, visited URL, final score, and rationale.\n"]

        # Choose which source to iterate: prefer full appendix entries, otherwise fall back to items.
        render_source = appendix if appendix else items_fallback

        for item in render_source:
            # Normalize access to fields whether item came from appendix or items list
            cid = item.get('content_id') or item.get('content_id') or item.get('id') or 'unknown'
            meta = item.get('meta') or {}
            # meta might be a JSON string in some cases
            if isinstance(meta, str):
                try:
                    import json as _json
                    meta = _json.loads(meta) if meta else {}
                except Exception:
                    meta = {}

            # If scorer attached an 'orig_meta' wrapper (preserved original fetch meta),
            # prefer values from there when top-level meta fields are missing.
            try:
                orig_meta = meta.get('orig_meta') if isinstance(meta, dict) else None
                if isinstance(orig_meta, str):
                    try:
                        import json as _json
                        orig_meta = _json.loads(orig_meta)
                    except Exception:
                        orig_meta = None
            except Exception:
                orig_meta = None

            if isinstance(orig_meta, dict):
                # backfill common fields from orig_meta if missing
                for k in ('title', 'name', 'description', 'snippet', 'body', 'source_url', 'url', 'terms', 'privacy'):
                    if k not in meta or not meta.get(k):
                        try:
                            if orig_meta.get(k):
                                meta[k] = orig_meta.get(k)
                        except Exception:
                            continue

            title = meta.get('title') or meta.get('name') or meta.get('headline') or meta.get('og:title') or (item.get('source') or '') + ' - ' + (cid or '')

            # Prefer body content for description when snippet appears noisy (multiple short fragments/menus)
            raw_desc = meta.get('description') or meta.get('snippet') or meta.get('summary') or ''
            body_candidate = meta.get('body') or item.get('body') or ''

            def _is_noisy_snippet(s: str) -> bool:
                if not s:
                    return False
                # Split on common separators; if many short fragments exist, it's noisy
                parts = re.split(r'[\n\r\t\-•,;…]+', s)
                parts = [p.strip() for p in parts if p.strip()]
                short_fragments = sum(1 for p in parts if len(p) < 40)
                if len(parts) >= 4 and short_fragments >= 4:
                    return True
                # also consider many languages / emoji-like tokens as noisy
                non_alpha = sum(1 for ch in s if not (ch.isalnum() or ch.isspace()))
                if non_alpha > max(10, len(s) * 0.05):
                    return True
                return False

            desc_source = raw_desc
            if raw_desc and _is_noisy_snippet(raw_desc) and body_candidate:
                desc_source = body_candidate

            # Allow LLM-generated descriptions when requested in report_data
            use_llm = bool(report_data.get('use_llm_for_descriptions') or report_data.get('use_llm_for_examples'))
            description = None
            if use_llm:
                try:
                    desc_llm = _llm_summarize(desc_source or clean_text_for_llm(meta), model=report_data.get('llm_model', 'gpt-3.5-turbo'), max_words=80)
                    if desc_llm:
                        description = desc_llm.strip() + f" (Generated by {report_data.get('llm_model', 'gpt-3.5-turbo')})"
                except Exception:
                    description = None
            if not description:
                # Try to produce a summary from body/snippet, and if still empty, synthesize a minimal description
                description = _summarize_text(desc_source or body_candidate or meta.get('snippet') or '', max_lines=2, max_chars=240)
                if not description:
                    # Synthesize a short description using available metadata
                    parts = []
                    domain = ''
                    try:
                        from urllib.parse import urlparse
                        vurl = meta.get('source_url') or meta.get('url') or meta.get('privacy') or meta.get('terms') or ''
                        if vurl:
                            domain = urlparse(vurl).netloc
                    except Exception:
                        domain = ''
                    if domain:
                        parts.append(f"Page on {domain}")
                    if meta.get('privacy'):
                        parts.append('Privacy policy found')
                    if meta.get('terms'):
                        parts.append('Terms of service found')
                    if meta.get('content_type'):
                        parts.append(f"Content type: {meta.get('content_type')}")
                    description = ("; ".join(parts)) if parts else ''
            visited_url = meta.get('source_url') or meta.get('url') or meta.get('source_link') or ''
            # Robust visited URL fallback: platform_id, terms/privacy, or try to pull from item-level fields
            if not visited_url:
                visited_url = meta.get('platform_id') or item.get('platform_id') or item.get('url') or ''
                if not visited_url:
                    visited_url = meta.get('privacy') or meta.get('terms') or ''
            # Last-resort: scan any meta/body text for the first http(s) URL and use it
            if not visited_url:
                try:
                    import json as _json
                    combined = ''
                    try:
                        combined = _json.dumps(meta) if meta else ''
                    except Exception:
                        combined = str(meta)
                    if not combined and body_candidate:
                        combined = body_candidate
                    # look for http(s) links, avoiding common trailing punctuation
                    m = re.search(r"https?://[^\s\)\]\'>]+", combined or '')
                    if m:
                        visited_url = m.group(0)
                except Exception:
                    pass
            score = item.get('final_score') if item.get('final_score') is not None else item.get('final', None) or 0.0
            label = (item.get('label') or item.get('class_label') or '').title()

            # Build a natural-language rationale using dimension signals, applied rules, and metadata cues
            rationale_sentences = []
            dims = item.get('dimension_scores') or {}
            if isinstance(dims, dict) and dims:
                # Identify weakest dimensions
                try:
                    dim_items = [(k, float(v)) for k, v in dims.items() if v is not None]
                    dim_items.sort(key=lambda x: x[1])
                    weakest = dim_items[:2]
                    best = dim_items[-1] if dim_items else None
                    if weakest:
                        w_names = ', '.join([f"{n.title()} ({v:.2f})" for n, v in weakest])
                        rationale_sentences.append(f"Low signals in {w_names} contributed to the lower score.")
                    if best and best[1] >= 0.8:
                        rationale_sentences.append(f"Strong {best[0].title()} signal ({best[1]:.2f}) partially offset weaknesses.")
                except Exception:
                    pass

            # Meta-based cues (missing Terms/Privacy or missing meta tags)
            try:
                if isinstance(meta, dict):
                    # Check for presence of common site metadata
                    has_terms = bool(meta.get('terms') or meta.get('terms_url'))
                    has_privacy = bool(meta.get('privacy') or meta.get('privacy_url'))
                    has_og = bool(meta.get('og:title') or meta.get('og:description') or meta.get('og'))
                    # If explicit meta flags are missing, scan the body text for common footer links/phrases
                    if not has_terms or not has_privacy:
                        body_text = ''
                        try:
                            body_text = (meta.get('body') or item.get('body') or '')
                        except Exception:
                            body_text = ''
                        if body_text:
                            lowered = body_text.lower()
                            # Common English phrases
                            if not has_terms and ('terms of service' in lowered or 'terms & conditions' in lowered or 'terms and conditions' in lowered or '/terms' in lowered or 'terms' in lowered):
                                has_terms = True
                            if not has_privacy and ('privacy policy' in lowered or 'privacy' in lowered or '/privacy' in lowered or 'politique de confidentialité' in lowered):
                                has_privacy = True
                    if not has_terms and not has_privacy:
                        rationale_sentences.append('The site lacks visible Terms/Privacy links which reduces trust signals.')
                    if not has_og:
                        rationale_sentences.append('Missing open-graph metadata reduced the detectable content richness.')
            except Exception:
                pass

            # Applied rules and reasons
            rules = item.get('applied_rules') or []
            if rules:
                try:
                    rule_msgs = []
                    for r in rules:
                        rid = r.get('id') or r.get('rule') or 'rule'
                        eff = r.get('effect', '')
                        reason = r.get('reason') or ''
                        rule_msgs.append(f"{rid} {eff}{(': ' + reason) if reason else ''}")
                    if rule_msgs:
                        rationale_sentences.append('Applied rules: ' + '; '.join(rule_msgs))
                except Exception:
                    pass

            # LLM annotations if present
            try:
                if isinstance(meta, dict) and meta.get('_llm_classification'):
                    llm = meta.get('_llm_classification')
                    lab = llm.get('label') or ''
                    conf = llm.get('confidence')
                    rationale_sentences.append(f"LLM classified this item as {lab} (conf={conf}).")
            except Exception:
                pass

            rationale = ' '.join(rationale_sentences) if rationale_sentences else ''

            # Render item block with explicit Title bullet
            # Provide more informative fallbacks for description/visited URL
            desc_display = description if description else ''
            if not desc_display:
                terms_link = meta.get('terms') or meta.get('terms_url')
                priv_link = meta.get('privacy') or meta.get('privacy_url')
                if terms_link or priv_link:
                    parts = []
                    if terms_link:
                        parts.append(f"Terms: {terms_link}")
                    if priv_link:
                        parts.append(f"Privacy: {priv_link}")
                    desc_display = "Page content was thin; found: " + "; ".join(parts)
                else:
                    desc_display = '*No description available*'

            if visited_url:
                visited_display = visited_url
            else:
                # show any footer links when the main visited URL is unavailable
                terms_link = meta.get('terms') or meta.get('terms_url')
                priv_link = meta.get('privacy') or meta.get('privacy_url')
                if terms_link or priv_link:
                    parts = []
                    if terms_link:
                        parts.append(f"Terms: {terms_link}")
                    if priv_link:
                        parts.append(f"Privacy: {priv_link}")
                    visited_display = "; ".join(parts)
                else:
                    visited_display = '*N/A*'

            lines.append(
                f"### {title}\n\n"
                f"- Title: {title}\n"
                f"- Description: {desc_display}\n"
                f"- Visited URL: {visited_display}\n"
                f"- Score: {float(score):.2f} | Label: **{label}**\n"
                f"- Rationale:\n  {rationale if rationale else 'No detailed rationale available.'}\n\n---\n"
            )

        return "\n".join(lines)

    # --- Visual helpers -------------------------------------------------
    def _ensure_output_dir(self, report_data: Dict[str, Any]) -> str:
        out_dir = report_data.get('output_dir', './output')
        os.makedirs(out_dir, exist_ok=True)
        return out_dir

    def _create_dimension_heatmap(self, report_data: Dict[str, Any]) -> str:
        """Create a simple heatmap of the five-dimension averages. Returns image path or empty string."""
        dims = report_data.get('dimension_breakdown', {})
        if not dims:
            return ""

        labels = ['Provenance', 'Verification', 'Transparency', 'Coherence', 'Resonance']
        values = [dims.get(k.lower(), {}).get('average', 0.0) for k in labels]
        if sum(values) == 0:
            return ""

        out_dir = self._ensure_output_dir(report_data)
        img_path = os.path.join(out_dir, f"heatmap_{report_data.get('run_id','run')}.png")

        # heatmap as a 1x5 colored bar
        fig, ax = plt.subplots(figsize=(6, 1.5))
        cmap = plt.get_cmap('RdYlGn')
        norm = plt.Normalize(0, 1)
        ax.imshow([values], aspect='auto', cmap=cmap, norm=norm)
        ax.set_yticks([])
        ax.set_xticks(range(len(labels)))
        ax.set_xticklabels(labels, rotation=45, ha='right')
        ax.set_title('5D Trust Dimensions (average scores)')
        plt.tight_layout()
        fig.savefig(img_path, dpi=150)
        plt.close(fig)
        return img_path

    def _create_trendline(self, report_data: Dict[str, Any]) -> str:
        """Attempt to build a simple AR trendline by scanning previous markdown reports in output dir."""
        out_dir = self._ensure_output_dir(report_data)
        # Scan output dir for existing markdown reports with run IDs and AR lines
        pattern = re.compile(r"Core Authenticity Ratio:\*\* (\d+\.?\d*)%")
        runs = []  # list of (timestamp, ar_pct)
        for fname in os.listdir(out_dir):
            if not fname.endswith('.md'):
                continue
            path = os.path.join(out_dir, fname)
            try:
                with open(path, 'r', encoding='utf-8') as fh:
                    content = fh.read()
                m = pattern.search(content)
                if m:
                    ar = float(m.group(1))
                    # try to extract timestamp from filename if included
                    ts_match = re.search(r'run_(\d{8}_\d{6}_[0-9a-f]+)', fname)
                    ts = ts_match.group(1) if ts_match else fname
                    runs.append((ts, ar))
            except Exception:
                continue

        # include current run at the end
        current_ar = report_data.get('authenticity_ratio', {}).get('authenticity_ratio_pct', None)
        if current_ar is None:
            return ""

        # sort by filename (best-effort chronological ordering)
        if runs:
            runs_sorted = sorted(runs, key=lambda x: x[0])
            xs = list(range(len(runs_sorted)))
            ys = [r[1] for r in runs_sorted]
            xs.append(len(xs))
            ys.append(current_ar)
        else:
            # no historical runs
            return ""

        img_path = os.path.join(out_dir, f"ar_trend_{report_data.get('run_id','run')}.png")
        fig, ax = plt.subplots(figsize=(6, 2.5))
        ax.plot(xs, ys, marker='o')
        ax.set_xlabel('Run (historic -> latest)')
        ax.set_ylabel('Core AR (%)')
        ax.set_title('Authenticity Ratio Trend')
        ax.grid(True, linestyle='--', alpha=0.4)
        plt.tight_layout()
        fig.savefig(img_path, dpi=150)
        plt.close(fig)
        return img_path

    def _create_channel_breakdown(self, report_data: Dict[str, Any]) -> str:
        """Create channel breakdown bar chart if classification includes source channel info."""
        class_analysis = report_data.get('classification_analysis', {})
        if not class_analysis:
            return ""
        # look for per-channel distribution
        per_channel = class_analysis.get('by_channel', {})
        if not per_channel:
            return ""

        labels = list(per_channel.keys())
        counts = [per_channel[k] for k in labels]
        if sum(counts) == 0:
            return ""

        out_dir = self._ensure_output_dir(report_data)
        img_path = os.path.join(out_dir, f"channel_breakdown_{report_data.get('run_id','run')}.png")

        fig, ax = plt.subplots(figsize=(6, 3))
        ax.bar(labels, counts, color='tab:blue')
        ax.set_ylabel('Count')
        ax.set_title('Per-Channel Classification Counts')
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        fig.savefig(img_path, dpi=150)
        plt.close(fig)
        return img_path

    def _create_content_type_breakdown(self, report_data: Dict[str, Any]) -> str:
        """Create pie and bar charts for content-type percentage breakdown."""
        ctype = report_data.get('content_type_breakdown_pct', {})
        if not ctype:
            return ""

        out_dir = self._ensure_output_dir(report_data)
        pie_path = os.path.join(out_dir, f"content_type_pie_{report_data.get('run_id','run')}.png")
        bar_path = os.path.join(out_dir, f"content_type_bar_{report_data.get('run_id','run')}.png")

        labels = list(ctype.keys())
        values = [ctype[k] for k in labels]
        if sum(values) == 0:
            return ""

        # Pie chart
        fig1, ax1 = plt.subplots(figsize=(5, 3))
        ax1.pie(values, labels=labels, autopct='%1.1f%%', startangle=140)
        ax1.axis('equal')
        ax1.set_title('Content Type Distribution')
        plt.tight_layout()
        fig1.savefig(pie_path, dpi=150)
        plt.close(fig1)

        # Bar chart
        fig2, ax2 = plt.subplots(figsize=(6, 3))
        ax2.bar(labels, values, color='tab:green')
        ax2.set_ylabel('Percentage')
        ax2.set_title('Content Type Percentage')
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        fig2.savefig(bar_path, dpi=150)
        plt.close(fig2)

        # Return the pie path (used in the executive visuals); the bar is saved alongside
        return pie_path
