"""
PDF report generator for AR tool
Creates professional PDF reports with charts and analysis
"""

from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.platypus import Image
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from typing import Dict, Any, List
import logging
from datetime import datetime
import io
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import os

from config.settings import SETTINGS

logger = logging.getLogger(__name__)

class PDFReportGenerator:
    """Generates PDF reports for AR analysis"""
    
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
    
    def _setup_custom_styles(self):
        """Setup custom paragraph styles"""
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            alignment=TA_CENTER,
            textColor=colors.darkblue
        ))
        
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading2'],
            fontSize=16,
            spaceAfter=12,
            textColor=colors.darkblue
        ))
        
        self.styles.add(ParagraphStyle(
            name='KPI',
            parent=self.styles['Heading2'],
            fontSize=18,
            spaceAfter=6,
            alignment=TA_CENTER,
            textColor=colors.darkgreen
        ))
    
    def generate_report(self, report_data: Dict[str, Any], output_path: str, include_items_table: bool = False) -> str:
        """
        Generate PDF report from report data
        
        Args:
            report_data: Dictionary containing report data
            output_path: Path to save the PDF file
            
        Returns:
            Path to generated PDF file
        """
        logger.info(f"Generating PDF report: {output_path}")
        
        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=18
        )
        
        story = []
        
        # Title page
        story.extend(self._create_title_page(report_data))
        story.append(PageBreak())

        # Executive Summary
        story.extend(self._create_executive_summary(report_data, include_items_table=include_items_table))
        story.append(PageBreak())
        
        # Authenticity Ratio Analysis
        story.extend(self._create_ar_analysis(report_data))
        story.append(PageBreak())
        
        # Dimension Breakdown
        story.extend(self._create_dimension_breakdown(report_data))
        story.append(PageBreak())
        
        # Classification Analysis
        story.extend(self._create_classification_analysis(report_data))
        
        # Build PDF
        doc.build(story)
        
        logger.info(f"PDF report generated successfully: {output_path}")
        return output_path
    
    def _create_title_page(self, report_data: Dict[str, Any]) -> List:
        """Create title page"""
        story = []
        
        # Main title
        story.append(Paragraph("Authenticity Ratio™ Report", self.styles['CustomTitle']))
        story.append(Spacer(1, 20))
        
        # Brand information
        brand_id = report_data.get('brand_id', 'Unknown Brand')
        story.append(Paragraph(f"Brand: {brand_id}", self.styles['Heading2']))
        story.append(Spacer(1, 10))
        
        # Report metadata
        run_id = report_data.get('run_id', 'Unknown')
        generated_at = report_data.get('generated_at', datetime.now().isoformat())
        
        sources = report_data.get('sources', [])
        sources_display = ', '.join(sources) if sources else 'Unknown'

        metadata = [
            ['Report ID:', run_id],
            ['Generated:', generated_at],
            ['Analysis Period:', 'Current Run'],
            ['Data Sources:', sources_display],
            ['Rubric Version:', report_data.get('rubric_version', 'v1.0')]
        ]
        
        metadata_table = Table(metadata, colWidths=[2*inch, 3*inch])
        metadata_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        
        story.append(metadata_table)
        story.append(Spacer(1, 30))
        # Key metrics preview
        ar_data = report_data.get('authenticity_ratio', {})
        total_items = ar_data.get('total_items', 0)
        ar_pct = ar_data.get('authenticity_ratio_pct', 0.0)
        extended_ar = ar_data.get('extended_ar_pct', 0.0)

        story.append(Paragraph("Summary", self.styles['SectionHeader']))
        story.append(Paragraph(f"Core Authenticity Ratio: {ar_pct:.1f}%", self.styles['KPI']))
        story.append(Paragraph(f"Extended Authenticity Ratio: {extended_ar:.1f}%", self.styles['Heading3']))
        story.append(Paragraph(f"Total Content Analyzed: {total_items:,}", self.styles['Normal']))
        # Short executive one-liner for non-technical stakeholders
        executive_one_liner = f"Executive Summary: {ar_pct:.1f}% Core AR — {total_items} items analyzed."
        story.append(Spacer(1, 6))
        story.append(Paragraph(executive_one_liner, self.styles['Normal']))

        return story
    
    def _create_executive_summary(self, report_data: Dict[str, Any], include_items_table: bool = False) -> List:
        """Create executive summary section"""
        story = []
        story.append(Paragraph("Executive Summary", self.styles['SectionHeader']))
        ar_data = report_data.get('authenticity_ratio', {})
        total_items = ar_data.get('total_items', 0)
        authentic_items = ar_data.get('authentic_items', 0)
        suspect_items = ar_data.get('suspect_items', 0)
        inauthentic_items = ar_data.get('inauthentic_items', 0)
        ar_pct = ar_data.get('authenticity_ratio_pct', 0.0)
        extended_ar = ar_data.get('extended_ar_pct', 0.0)

        interp = (
            f"Out of {total_items} items analyzed, {ar_pct:.1f}% met authenticity standards, "
            f"indicating that most brand-related content lacks verifiable provenance or transparency. "
            f"The low Verification and Transparency scores suggest the brand’s messaging is being reused or misrepresented by third parties."
        )

        story.append(Paragraph(interp, self.styles['Normal']))

        # Include score-based AR if present
        score_based = report_data.get('score_based_ar_pct')
        if score_based is not None:
            story.append(Spacer(1, 6))
            story.append(Paragraph(f"Score-based Authenticity Ratio (mean 5D score): {score_based:.1f}%", self.styles['Normal']))

        # Add explicit definitions for Core vs Extended AR to reduce confusion
        story.append(Spacer(1, 8))
        defs_lines = [
            "Definitions:",
            "- Core AR (classification): Percentage of items explicitly classified as 'Authentic' (Authentic / Total * 100).",
            "- Score-based AR (mean 5D score): The arithmetic mean of per-item 5D composite scores (0-100).",
            "- Extended AR: A rubric-blended metric combining classification labels and score-based signals; see AR Analysis for formula details."
        ]
        for ln in defs_lines:
            story.append(Paragraph(ln, self.styles['Normal']))

        # Examples section (up to 5 items) for quick review
        items = report_data.get('items', []) or report_data.get('items', [])
        if items:
            story.append(Spacer(1, 8))
            story.append(Paragraph("Examples from this run:", self.styles['Heading3']))
            example_rows = []
            max_examples = 5

            preferred_sources = report_data.get('sources') or sorted({it.get('source') for it in items if it.get('source')})
            selected = []
            for src in preferred_sources:
                if len(selected) >= max_examples:
                    break
                for it in items:
                    if it.get('source') == src and it not in selected:
                        selected.append(it)
                        break
            if len(selected) < max_examples:
                for it in items:
                    if len(selected) >= max_examples:
                        break
                    if it not in selected:
                        selected.append(it)

            # Render each example as a small block with Title, Label, Score, Description, URL
            for ex in selected[:max_examples]:
                meta = ex.get('meta') or {}
                title = meta.get('title') or meta.get('source_url') or ex.get('content_id')
                score = ex.get('final_score', 0.0)
                label = ex.get('label', '')
                desc = meta.get('description') or meta.get('snippet') or meta.get('summary') or ''
                url = meta.get('source_url') or meta.get('url') or ''

                # Title row
                story.append(Paragraph(f"<b>{title}</b> — {label.title()} ({score:.1f})", self.styles['Normal']))
                if desc:
                    if len(desc) > 300:
                        desc = desc[:297].rstrip() + '...'
                    story.append(Paragraph(desc, self.styles['Normal']))
                if url:
                    story.append(Paragraph(f"URL: {url}", self.styles['Normal']))
                story.append(Spacer(1, 6))

        # Optionally include the full per-item table when requested (programmatic runs)
        if include_items_table:
            all_items = report_data.get('items', [])
            if all_items:
                story.append(PageBreak())
                story.append(Paragraph('Per-item Scoring Table', self.styles['SectionHeader']))
                table_rows = [['Content ID', 'Source', 'Label', 'Score', 'URL']]
                for it in all_items:
                    url = ''
                    try:
                        url = it.get('meta', {}).get('source_url') or ''
                    except Exception:
                        url = ''
                    table_rows.append([it.get('content_id'), it.get('source'), it.get('label'), f"{it.get('final_score', 0.0):.1f}", url])
                per_table = Table(table_rows, colWidths=[1.5*inch, 1*inch, 1*inch, 0.8*inch, 2.0*inch])
                per_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 8),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ]))
                story.append(per_table)
        
        return story
    
    def _create_ar_analysis(self, report_data: Dict[str, Any]) -> List:
        """Create Authenticity Ratio analysis section"""
        story = []
        story.append(Paragraph("Authenticity Ratio Analysis", self.styles['SectionHeader']))

        ar_data = report_data.get('authenticity_ratio', {})

        # AR metrics table
        ar_metrics = [
            ['Metric', 'Count', 'Percentage'],
            ['Total Content', f"{ar_data.get('total_items', 0):,}", '100.0%'],
            ['Authentic', f"{ar_data.get('authentic_items', 0):,}", f"{ar_data.get('authentic_items', 0) / max(ar_data.get('total_items', 1), 1) * 100:.1f}%"],
            ['Suspect', f"{ar_data.get('suspect_items', 0):,}", f"{ar_data.get('suspect_items', 0) / max(ar_data.get('total_items', 1), 1) * 100:.1f}%"],
            ['Inauthentic', f"{ar_data.get('inauthentic_items', 0):,}", f"{ar_data.get('inauthentic_items', 0) / max(ar_data.get('total_items', 1), 1) * 100:.1f}%"],
            ['', '', ''],
            ['Core AR', f"{ar_data.get('authenticity_ratio_pct', 0.0):.1f}%", ''],
            ['Extended AR', f"{ar_data.get('extended_ar_pct', 0.0):.1f}%", '']
        ]

        ar_table = Table(ar_metrics, colWidths=[2.5*inch, 1.5*inch, 1.5*inch])
        ar_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('BACKGROUND', (0, 1), (-1, -3), colors.beige),
            ('BACKGROUND', (0, -2), (-1, -1), colors.lightblue),
            ('FONTNAME', (0, -2), (-1, -1), 'Helvetica-Bold'),
        ]))

        story.append(ar_table)
        story.append(Spacer(1, 20))

        # Add a small explanatory paragraph showing the simple Core AR formula and why Extended AR can differ
        try:
            total = ar_data.get('total_items', 0)
            auth = ar_data.get('authentic_items', 0)
            ext = ar_data.get('extended_ar_pct', 0.0)
            core_pct = ar_data.get('authenticity_ratio_pct', 0.0)
            expl = (
                f"Core AR (simple): Authentic / Total * 100 = {auth} / {total} * 100 = {core_pct:.1f}%\n"
                f"Extended AR: {ext:.1f}% — this is a rubric-adjusted blend that can pull items toward authenticity or inauthenticity based on 5D scores and attribute rules."
            )
            story.append(Paragraph(expl, self.styles['Normal']))
        except Exception:
            pass

        # Dimension sections
        dimension_data = report_data.get('dimension_breakdown', {})
        defs = {
            'provenance': 'How traceable and source-verified the content is.',
            'verification': 'Alignment with verifiable brand or regulatory data.',
            'transparency': 'Clarity of ownership, disclosure, and intent.',
            'coherence': 'Consistency of messaging and tone with known brand assets.',
            'resonance': 'Audience engagement that aligns with brand values.'
        }

        for dim in ['provenance', 'verification', 'transparency', 'coherence', 'resonance']:
            stats = dimension_data.get(dim, {})
            avg = stats.get('average', 0.0)
            lo = stats.get('min', 0.0)
            hi = stats.get('max', 0.0)
            interp = ''
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

            story.append(Paragraph(dim.title(), self.styles['SectionHeader']))
            story.append(Paragraph(f"Definition: {defs.get(dim)}", self.styles['Normal']))
            story.append(Paragraph(f"Key Stats: Average: {avg:.3f} | Range: {lo:.2f}–{hi:.2f}", self.styles['Normal']))
            story.append(Paragraph(interp, self.styles['Normal']))
            story.append(Spacer(1, 12))
        
        return story
    
    def _create_dimension_breakdown(self, report_data: Dict[str, Any]) -> List:
        """Create dimension breakdown section"""
        story = []
        
        story.append(Paragraph("5D Trust Dimensions Analysis", self.styles['SectionHeader']))
        
        dimension_data = report_data.get('dimension_breakdown', {})
        
        if dimension_data:
            # Dimension scores table
            dim_headers = ['Dimension', 'Average', 'Min', 'Max', 'Std Dev']
            dim_rows = [dim_headers]
            
            for dimension, stats in dimension_data.items():
                dim_rows.append([
                    dimension.title(),
                    f"{stats.get('average', 0):.3f}",
                    f"{stats.get('min', 0):.3f}",
                    f"{stats.get('max', 0):.3f}",
                    f"{stats.get('std_dev', 0):.3f}"
                ])
            
            dim_table = Table(dim_rows, colWidths=[1.5*inch, 1*inch, 1*inch, 1*inch, 1*inch])
            dim_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ]))
            
            story.append(dim_table)
            story.append(Spacer(1, 20))
            
            # Dimension chart
            chart_path = self._create_dimension_chart(dimension_data)
            if chart_path:
                story.append(Image(chart_path, width=6*inch, height=4*inch))

        # Attempt to embed visuals created by markdown generator (heatmap, trendline, channel breakdown)
        # They are saved in the output directory if present
        out_dir = report_data.get('output_dir', './output')
        run_id = report_data.get('run_id', 'run')
        heatmap = os.path.join(out_dir, f"heatmap_{run_id}.png")
        trend = os.path.join(out_dir, f"ar_trend_{run_id}.png")
        channel = os.path.join(out_dir, f"channel_breakdown_{run_id}.png")
        # Content-type visuals (created by MarkdownReportGenerator)
        ctype_pie = os.path.join(out_dir, f"content_type_pie_{run_id}.png")
        ctype_bar = os.path.join(out_dir, f"content_type_bar_{run_id}.png")

        for img_path in (heatmap, trend, channel, ctype_pie, ctype_bar):
            if not img_path:
                continue
            if os.path.exists(img_path):
                try:
                    story.append(Spacer(1, 12))
                    # For pie charts, prefer a square-ish box; for bars/trend use a wider box
                    basename = os.path.basename(img_path).lower()
                    if 'pie' in basename:
                        story.append(Image(img_path, width=5*inch, height=4*inch))
                    elif 'dim' in basename or 'dimension' in basename:
                        story.append(Image(img_path, width=6*inch, height=4*inch))
                    else:
                        # default sizing for other charts
                        story.append(Image(img_path, width=6*inch, height=3*inch))
                except Exception as e:
                    logger.debug(f"Could not embed image {img_path}: {e}")
        
        return story
    
    def _create_classification_analysis(self, report_data: Dict[str, Any]) -> List:
        """Create classification analysis section"""
        story = []
        
        story.append(Paragraph("Content Classification Analysis", self.styles['SectionHeader']))
        
        classification_data = report_data.get('classification_analysis', {})
        
        if classification_data:
            # Classification summary
            dist = classification_data.get('classification_distribution', {})
            total = sum(dist.values())
            
            if total > 0:
                summary_text = f"""
                Content classification analysis reveals the following distribution:
                • Authentic content: {dist.get('authentic', 0):,} items ({dist.get('authentic', 0)/total*100:.1f}%)
                • Suspect content: {dist.get('suspect', 0):,} items ({dist.get('suspect', 0)/total*100:.1f}%)
                • Inauthentic content: {dist.get('inauthentic', 0):,} items ({dist.get('inauthentic', 0)/total*100:.1f}%)
                
                This classification helps identify content that requires immediate attention 
                (inauthentic), content that may need verification (suspect), and content 
                that strengthens brand authenticity (authentic).
                """
                
                story.append(Paragraph(summary_text, self.styles['Normal']))
        
        return story
    
    def _create_ar_chart(self, ar_data: Dict[str, Any]) -> str:
        """Create Authenticity Ratio chart"""
        try:
            # Create pie chart
            fig, ax = plt.subplots(figsize=(8, 6))
            
            labels = ['Authentic', 'Suspect', 'Inauthentic']
            sizes = [
                ar_data.get('authentic_items', 0),
                ar_data.get('suspect_items', 0),
                ar_data.get('inauthentic_items', 0)
            ]
            colors_list = ['#2ecc71', '#f39c12', '#e74c3c']
            
            # Remove zero values
            non_zero_data = [(label, size, color) for label, size, color in zip(labels, sizes, colors_list) if size > 0]
            if non_zero_data:
                labels, sizes, colors_list = zip(*non_zero_data)
            
            wedges, texts, autotexts = ax.pie(sizes, labels=labels, colors=colors_list, autopct='%1.1f%%', startangle=90)
            
            # Customize text
            for autotext in autotexts:
                autotext.set_color('white')
                autotext.set_fontweight('bold')
            
            ax.set_title('Content Classification Distribution', fontsize=14, fontweight='bold')
            
            # Save to temporary file
            chart_path = f"/tmp/ar_chart_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            plt.savefig(chart_path, dpi=150, bbox_inches='tight')
            plt.close()
            
            return chart_path
            
        except Exception as e:
            logger.error(f"Error creating AR chart: {e}")
            return None
    
    def _create_dimension_chart(self, dimension_data: Dict[str, Any]) -> str:
        """Create dimension scores chart"""
        try:
            # Create bar chart
            fig, ax = plt.subplots(figsize=(10, 6))
            
            dimensions = list(dimension_data.keys())
            averages = [dimension_data[dim]['average'] for dim in dimensions]
            
            bars = ax.bar(dimensions, averages, color=['#3498db', '#e74c3c', '#2ecc71', '#f39c12', '#9b59b6'])
            
            # Customize chart
            ax.set_ylim(0, 1)
            ax.set_ylabel('Average Score')
            ax.set_title('5D Trust Dimensions - Average Scores', fontsize=14, fontweight='bold')
            ax.grid(True, alpha=0.3)
            
            # Add value labels on bars
            for bar, avg in zip(bars, averages):
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height + 0.01,
                       f'{avg:.3f}', ha='center', va='bottom', fontweight='bold')
            
            plt.xticks(rotation=45)
            plt.tight_layout()
            
            # Save to temporary file
            chart_path = f"/tmp/dimensions_chart_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            plt.savefig(chart_path, dpi=150, bbox_inches='tight')
            plt.close()
            
            return chart_path
        except Exception as e:
            logger.error(f"Error creating dimension chart: {e}")
            return None
