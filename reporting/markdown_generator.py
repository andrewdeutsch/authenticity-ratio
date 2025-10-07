"""
Markdown report generator for AR tool
Creates markdown reports for easy sharing and documentation
"""

from typing import Dict, Any, List
import logging
from datetime import datetime

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
        return f"# Authenticity Ratio™ Report\n\n## Brand: {brand_id}"
    
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
| Data Sources | Reddit, Amazon |
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
        
        return f"""## Executive Summary

This Authenticity Ratio™ analysis evaluated **{total_items:,}** pieces of brand-related content across multiple channels. The analysis reveals that **{ar_pct:.1f}%** of content meets authenticity standards.

### Key Findings

- **Authentic Content**: {authentic_items:,} items ({authentic_items/total_items*100:.1f}% of total)
- **Suspect Content**: {suspect_items:,} items ({suspect_items/total_items*100:.1f}% of total)  
- **Inauthentic Content**: {inauthentic_items:,} items ({inauthentic_items/total_items*100:.1f}% of total)

### Authenticity Metrics

| Metric | Value |
|--------|-------|
| **Core Authenticity Ratio** | **{ar_pct:.1f}%** |
| **Extended Authenticity Ratio** | **{extended_ar:.1f}%** |

> The Extended Authenticity Ratio gives partial credit to suspect content, providing a more nuanced view of brand content authenticity.

### Strategic Implications

This analysis serves as a key brand health indicator, helping identify areas where:
- Brand messaging may need reinforcement
- Inauthentic content requires immediate attention
- Content verification processes can be improved"""
    
    def _create_ar_analysis(self, report_data: Dict[str, Any]) -> str:
        """Create Authenticity Ratio analysis section"""
        ar_data = report_data.get('authenticity_ratio', {})
        
        # Create classification breakdown table
        total_items = ar_data.get('total_items', 0)
        authentic_items = ar_data.get('authentic_items', 0)
        suspect_items = ar_data.get('suspect_items', 0)
        inauthentic_items = ar_data.get('inauthentic_items', 0)
        
        return f"""## Authenticity Ratio Analysis

### Content Classification Breakdown

| Classification | Count | Percentage |
|----------------|-------|------------|
| **Total Content** | {total_items:,} | 100.0% |
| **Authentic** | {authentic_items:,} | {authentic_items/total_items*100:.1f}% |
| **Suspect** | {suspect_items:,} | {suspect_items/total_items*100:.1f}% |
| **Inauthentic** | {inauthentic_items:,} | {inauthentic_items/total_items*100:.1f}% |

### Authenticity Ratio Calculations

| Metric | Formula | Result |
|--------|---------|--------|
| **Core AR** | (Authentic ÷ Total) × 100 | **{ar_data.get('authenticity_ratio_pct', 0.0):.1f}%** |
| **Extended AR** | (Authentic + 0.5×Suspect) ÷ Total × 100 | **{ar_data.get('extended_ar_pct', 0.0):.1f}%** |

### Interpretation Guidelines

- **Core AR ≥ 80%**: Excellent authenticity
- **Core AR 60-79%**: Good authenticity with room for improvement
- **Core AR 40-59%**: Moderate authenticity requiring attention
- **Core AR < 40%**: Poor authenticity requiring immediate action

### Current Status: {"🟢 Excellent" if ar_data.get('authenticity_ratio_pct', 0) >= 80 else "🟡 Good" if ar_data.get('authenticity_ratio_pct', 0) >= 60 else "🟠 Moderate" if ar_data.get('authenticity_ratio_pct', 0) >= 40 else "🔴 Poor"}"""
    
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
