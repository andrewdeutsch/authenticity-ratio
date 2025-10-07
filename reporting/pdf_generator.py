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
    
    def generate_report(self, report_data: Dict[str, Any], output_path: str) -> str:
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
        story.extend(self._create_executive_summary(report_data))
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
        
        metadata = [
            ['Report ID:', run_id],
            ['Generated:', generated_at],
            ['Analysis Period:', 'Current Run'],
            ['Data Sources:', 'Reddit, Amazon'],
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
        
        story.append(Paragraph("Key Metrics Preview", self.styles['SectionHeader']))
        story.append(Paragraph(f"Authenticity Ratio: {ar_pct:.1f}%", self.styles['KPI']))
        story.append(Paragraph(f"Total Content Analyzed: {total_items:,}", self.styles['Heading3']))
        
        return story
    
    def _create_executive_summary(self, report_data: Dict[str, Any]) -> List:
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
        
        summary_text = f"""
        This Authenticity Ratio™ analysis evaluated {total_items:,} pieces of brand-related content 
        across multiple channels. The analysis reveals that {ar_pct:.1f}% of content meets 
        authenticity standards, with {authentic_items:,} items classified as authentic, 
        {suspect_items:,} as suspect, and {inauthentic_items:,} as inauthentic.
        
        The Extended Authenticity Ratio, which gives partial credit to suspect content, 
        stands at {extended_ar:.1f}%. This metric provides a more nuanced view of brand 
        content authenticity by recognizing content that may be genuine but lacks 
        sufficient verification.
        
        This analysis serves as a key brand health indicator, helping identify areas 
        where brand messaging may need reinforcement and where inauthentic content 
        requires attention.
        """
        
        story.append(Paragraph(summary_text, self.styles['Normal']))
        
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
        
        # AR chart
        chart_path = self._create_ar_chart(ar_data)
        if chart_path:
            story.append(Image(chart_path, width=6*inch, height=4*inch))
        
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
