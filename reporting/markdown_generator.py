"""
Markdown report generator for AR tool
Creates markdown reports for easy sharing and documentation
"""

from typing import Dict, Any, List
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

        return f"""## Summary

**Core Authenticity Ratio:** {ar_pct:.1f}%  
**Extended Authenticity Ratio:** {extended_ar:.1f}%  
**Total content analyzed:** {total_items:,}  
**Distribution:** Authentic: {authentic_items:,} | Suspect: {suspect_items:,} | Inauthentic: {inauthentic_items:,}

{interp}

**Executive (one-liner):** {executive_one_liner}

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

- Reddit: Community discussions and brand mentions
- Amazon: Product reviews and brand-related content
- Additional sources: [To be expanded in future versions]

### Report Generation

- **Generated**: {generated_at}
- **Brand**: {brand_id}
- **Version**: Authenticity Ratio Tool v1.0

---

*This report is confidential and proprietary. For questions or additional analysis, contact the Authenticity Ratio team.*"""

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
