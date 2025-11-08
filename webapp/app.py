"""
Authenticity Ratio™ Web Application
A comprehensive interface for brand content authenticity analysis
"""
from __future__ import annotations

import sys
import os

# Ensure project root is on PYTHONPATH
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import json
import time
from datetime import datetime
from typing import Dict, List, Any
import glob as file_glob

from config.settings import APIConfig

# Page configuration
st.set_page_config(
    page_title="Authenticity Ratio™ Tool",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        color: #1f77b4;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: #f0f2f6;
        padding: 1.5rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
    }
    .info-box {
        background: #e7f3ff;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #2196F3;
        margin: 1rem 0;
    }
    .success-box {
        background: #e8f5e9;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #4caf50;
        margin: 1rem 0;
    }
    .warning-box {
        background: #fff3e0;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #ff9800;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)


def show_home_page():
    """Display the home/overview page"""
    st.markdown('<div class="main-header">🔍 Authenticity Ratio™</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Measure and monitor brand content authenticity across digital channels</div>', unsafe_allow_html=True)

    st.divider()

    # What is AR section
    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown("### 📊 What is Authenticity Ratio?")
        st.markdown("""
        **Authenticity Ratio (AR)** is a KPI that measures authentic vs. inauthentic brand-linked content
        across channels. It reframes authenticity as a brand health metric for CMOs and boards.

        #### Core Formula
        ```
        AR = (Verified Authentic Content ÷ Total Brand-Linked Content) × 100
        ```

        #### Extended Formula (with suspect content)
        ```
        AR = (A + 0.5S) ÷ (A + S + I) × 100
        ```
        - **A** = Authentic
        - **S** = Suspect
        - **I** = Inauthentic
        """)

    with col2:
        st.markdown("### 🎯 Quick Start")
        st.markdown("""
        1. **Configure** your brand and sources
        2. **Run** the analysis pipeline
        3. **Review** AR scores and insights
        4. **Export** reports for stakeholders
        """)

        if st.button("🚀 Start New Analysis", type="primary", use_container_width=True):
            st.session_state['page'] = 'analyze'
            st.rerun()

    st.divider()

    # 6D Trust Dimensions
    st.markdown("### 🔍 6D Trust Dimensions")
    st.markdown("Content is scored across six dimensions to determine authenticity:")

    dimensions_cols = st.columns(3)

    dimensions = [
        ("Provenance", "🔗", "Origin, traceability, metadata integrity"),
        ("Verification", "✓", "Factual accuracy vs. trusted databases"),
        ("Transparency", "👁", "Disclosures, clarity, attribution"),
        ("Coherence", "🔄", "Consistency across channels and time"),
        ("Resonance", "📢", "Cultural fit, organic engagement"),
        ("AI Readiness", "🤖", "Machine discoverability, LLM-readable signals")
    ]

    for idx, (name, icon, desc) in enumerate(dimensions):
        with dimensions_cols[idx % 3]:
            st.markdown(f"**{icon} {name}**")
            st.caption(desc)

    st.divider()

    # Pipeline overview
    st.markdown("### ⚙️ Analysis Pipeline")

    pipeline_steps = [
        ("1. Ingest", "Collect content from Reddit, YouTube, Web, Amazon"),
        ("2. Normalize", "Standardize data format and extract metadata"),
        ("3. Enrich", "Add metadata, fact-check signals, provenance data"),
        ("4. Score", "Apply 6D rubric to each content item"),
        ("5. Classify", "Label as Authentic, Suspect, or Inauthentic"),
        ("6. Calculate", "Compute AR and generate insights"),
        ("7. Report", "Export PDF/Markdown with visualizations")
    ]

    cols = st.columns(7)
    for idx, (step, desc) in enumerate(pipeline_steps):
        with cols[idx]:
            st.markdown(f"**{step}**")
            st.caption(desc)


def show_analyze_page():
    """Display the analysis configuration and execution page"""
    st.markdown('<div class="main-header">🚀 Run Analysis</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Configure and execute brand authenticity analysis</div>', unsafe_allow_html=True)

    st.divider()

    # Configuration form
    with st.form("analysis_config"):
        col1, col2 = st.columns(2)

        with col1:
            brand_id = st.text_input(
                "Brand ID*",
                value="nike",
                help="Unique identifier for the brand (e.g., 'nike', 'coca-cola')"
            )

            keywords = st.text_input(
                "Search Keywords*",
                value="nike",
                help="Space-separated keywords to search for (e.g., 'nike swoosh')"
            )

            max_items = st.number_input(
                "Max Items to Analyze",
                min_value=5,
                max_value=100,
                value=20,
                step=5,
                help="Maximum number of content items to analyze"
            )

        with col2:
            st.markdown("**Data Sources**")

            cfg = APIConfig()

            # Brave (always available)
            use_brave = st.checkbox("🌐 Web Search (Brave)", value=True, help="Search web content via Brave Search")
            brave_pages = st.number_input("Web pages to fetch", min_value=1, max_value=20, value=10, step=1) if use_brave else 10

            # Reddit
            reddit_available = bool(cfg.reddit_client_id and cfg.reddit_client_secret)
            use_reddit = st.checkbox(
                "🔴 Reddit",
                value=False,
                disabled=not reddit_available,
                help="Requires REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET" if not reddit_available else "Search Reddit posts and comments"
            )

            # YouTube
            youtube_available = bool(cfg.youtube_api_key)
            use_youtube = st.checkbox(
                "📹 YouTube",
                value=False,
                disabled=not youtube_available,
                help="Requires YOUTUBE_API_KEY" if not youtube_available else "Search YouTube videos and comments"
            )
            include_comments = st.checkbox("Include YouTube comments", value=False) if use_youtube else False

        st.divider()

        col_submit, col_clear = st.columns([1, 4])
        with col_submit:
            submit = st.form_submit_button("▶️ Run Analysis", type="primary", use_container_width=True)
        with col_clear:
            if st.form_submit_button("Clear Results", use_container_width=True):
                st.session_state['last_run'] = None
                st.rerun()

    if submit:
        # Validate inputs
        if not brand_id or not keywords:
            st.error("⚠️ Brand ID and Keywords are required")
            return

        # Build sources list
        sources = []
        if use_brave:
            sources.append('brave')
        if use_reddit:
            sources.append('reddit')
        if use_youtube:
            sources.append('youtube')

        if not sources:
            st.error("⚠️ Please select at least one data source")
            return

        # Run pipeline
        run_analysis(brand_id, keywords.split(), sources, max_items, brave_pages, include_comments)


def run_analysis(brand_id: str, keywords: List[str], sources: List[str], max_items: int, brave_pages: int, include_comments: bool):
    """Execute the analysis pipeline"""

    # Create output directory
    output_dir = os.path.join(PROJECT_ROOT, 'output', 'webapp_runs')
    os.makedirs(output_dir, exist_ok=True)

    run_id = datetime.now().strftime('%Y%m%d_%H%M%S')
    run_dir = os.path.join(output_dir, f"{brand_id}_{run_id}")
    os.makedirs(run_dir, exist_ok=True)

    # Progress tracking
    progress_bar = st.progress(0)
    status_text = st.empty()

    try:
        # Step 1: Import modules
        status_text.text("Initializing pipeline components...")
        progress_bar.progress(10)

        from ingestion.brave_search import collect_brave_pages
        from ingestion.normalizer import ContentNormalizer
        from scoring.pipeline import ScoringPipeline
        from reporting.pdf_generator import PDFReportGenerator
        from reporting.markdown_generator import MarkdownReportGenerator
        from data.models import NormalizedContent

        try:
            from ingestion.reddit_crawler import RedditCrawler
        except:
            RedditCrawler = None

        try:
            from ingestion.youtube_scraper import YouTubeScraper
        except:
            YouTubeScraper = None

        # Step 2: Data Ingestion
        status_text.text(f"Ingesting content from {', '.join(sources)}...")
        progress_bar.progress(20)

        all_content = []

        # Brave ingestion
        if 'brave' in sources:
            query = ' '.join(keywords)
            collected = collect_brave_pages(query, target_count=brave_pages)

            for i, c in enumerate(collected):
                url = c.get('url')
                content_id = f"brave_{i}_{abs(hash(url or ''))}"
                meta = {
                    'source_url': url or '',
                    'content_type': 'web',
                    'title': c.get('title', ''),
                    'description': c.get('body', '')[:200]
                }
                if c.get('terms'):
                    meta['terms'] = c.get('terms')
                if c.get('privacy'):
                    meta['privacy'] = c.get('privacy')

                nc = NormalizedContent(
                    content_id=content_id,
                    src='brave',
                    platform_id=url or '',
                    author='web',
                    title=c.get('title', '') or '',
                    body=c.get('body', '') or '',
                    run_id=run_id,
                    event_ts=datetime.now().isoformat(),
                    meta=meta,
                    url=url or '',
                    modality='text',
                    channel='web',
                    platform_type='web'
                )
                all_content.append(nc)

            st.info(f"✓ Collected {len(collected)} web pages")

        # Reddit ingestion
        if 'reddit' in sources and RedditCrawler:
            try:
                reddit = RedditCrawler()
                posts = reddit.search_posts(keywords=keywords, limit=max_items // len(sources))
                reddit_content = reddit.convert_to_normalized_content(posts, brand_id, run_id)
                all_content.extend(reddit_content)
                st.info(f"✓ Collected {len(reddit_content)} Reddit posts")
            except Exception as e:
                st.warning(f"⚠️ Reddit ingestion failed: {e}")

        # YouTube ingestion
        if 'youtube' in sources and YouTubeScraper:
            try:
                yt = YouTubeScraper()
                query = ' '.join(keywords)
                videos = yt.search_videos(query=query, max_results=max_items // len(sources))
                youtube_content = yt.convert_videos_to_normalized(videos, brand_id, run_id, include_comments=include_comments)
                all_content.extend(youtube_content)
                st.info(f"✓ Collected {len(youtube_content)} YouTube videos")
            except Exception as e:
                st.warning(f"⚠️ YouTube ingestion failed: {e}")

        if not all_content:
            st.error("❌ No content collected from any source")
            return

        # Step 3: Normalization
        status_text.text("Normalizing content...")
        progress_bar.progress(40)

        normalizer = ContentNormalizer()
        normalized_content = normalizer.normalize_content(all_content)

        # Step 4: Scoring
        status_text.text("Scoring content on 6D Trust dimensions...")
        progress_bar.progress(60)

        scoring_pipeline = ScoringPipeline()
        brand_config = {
            'brand_id': brand_id,
            'brand_name': brand_id,
            'keywords': keywords,
            'sources': sources
        }

        pipeline_run = scoring_pipeline.run_scoring_pipeline(normalized_content, brand_config)

        # Step 5: Generate Reports
        status_text.text("Generating reports...")
        progress_bar.progress(80)

        scores_list = pipeline_run.classified_scores or []
        scoring_report = scoring_pipeline.generate_scoring_report(scores_list, brand_config)

        # Generate PDF
        pdf_generator = PDFReportGenerator()
        pdf_path = os.path.join(run_dir, f'ar_report_{brand_id}_{run_id}.pdf')
        pdf_generator.generate_report(scoring_report, pdf_path, include_items_table=True)

        # Generate Markdown
        markdown_generator = MarkdownReportGenerator()
        md_path = os.path.join(run_dir, f'ar_report_{brand_id}_{run_id}.md')
        markdown_generator.generate_report(scoring_report, md_path)

        # Save run data for visualization
        run_data = {
            'run_id': run_id,
            'brand_id': brand_id,
            'keywords': keywords,
            'sources': sources,
            'timestamp': datetime.now().isoformat(),
            'pdf_path': pdf_path,
            'md_path': md_path,
            'scoring_report': scoring_report,
            'total_items': len(normalized_content)
        }

        data_path = os.path.join(run_dir, '_run_data.json')
        with open(data_path, 'w') as f:
            json.dump(run_data, f, indent=2, default=str)

        # Complete
        progress_bar.progress(100)
        status_text.text("✓ Analysis complete!")

        st.success(f"✅ Analysis completed successfully! Analyzed {len(normalized_content)} content items.")

        # Store in session state
        st.session_state['last_run'] = run_data

        # Switch to results view
        time.sleep(1)
        st.session_state['page'] = 'results'
        st.rerun()

    except Exception as e:
        st.error(f"❌ Analysis failed: {e}")
        import traceback
        st.code(traceback.format_exc())


def show_results_page():
    """Display analysis results with visualizations"""

    # Load last run or selected run
    run_data = st.session_state.get('last_run')

    if not run_data:
        st.warning("⚠️ No analysis results available. Please run an analysis first.")
        if st.button("← Back to Analysis"):
            st.session_state['page'] = 'analyze'
            st.rerun()
        return

    report = run_data.get('scoring_report', {})
    ar_data = report.get('authenticity_ratio', {})

    # Header
    st.markdown('<div class="main-header">📊 Analysis Results</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="sub-header">Brand: {run_data.get("brand_id")} | Run: {run_data.get("run_id")}</div>', unsafe_allow_html=True)

    st.divider()

    # Key Metrics
    st.markdown("### 🎯 Key Metrics")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        ar_pct = ar_data.get('authenticity_ratio_pct', 0)
        st.metric(
            label="Authenticity Ratio",
            value=f"{ar_pct:.1f}%",
            delta=None
        )

    with col2:
        st.metric(
            label="Total Content",
            value=f"{ar_data.get('total_items', 0):,}"
        )

    with col3:
        st.metric(
            label="Authentic",
            value=f"{ar_data.get('authentic_items', 0):,}",
            delta=None
        )

    with col4:
        st.metric(
            label="Inauthentic",
            value=f"{ar_data.get('inauthentic_items', 0):,}",
            delta=None
        )

    # AR Interpretation
    if ar_pct >= 80:
        st.markdown('<div class="success-box">🟢 <b>Excellent</b> - Your brand has excellent content authenticity. Continue maintaining high standards.</div>', unsafe_allow_html=True)
    elif ar_pct >= 60:
        st.markdown('<div class="info-box">🟡 <b>Good</b> - Good authenticity with room for improvement. Focus on verification processes.</div>', unsafe_allow_html=True)
    elif ar_pct >= 40:
        st.markdown('<div class="warning-box">🟠 <b>Moderate</b> - Moderate authenticity requiring attention. Implement stricter content guidelines.</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="warning-box">🔴 <b>Poor</b> - Poor authenticity requiring immediate action. Review and remove inauthentic content.</div>', unsafe_allow_html=True)

    st.divider()

    # Visualizations
    col1, col2 = st.columns(2)

    with col1:
        # Classification Distribution Pie Chart
        st.markdown("#### Content Classification Distribution")

        fig_pie = px.pie(
            values=[
                ar_data.get('authentic_items', 0),
                ar_data.get('suspect_items', 0),
                ar_data.get('inauthentic_items', 0)
            ],
            names=['Authentic', 'Suspect', 'Inauthentic'],
            color_discrete_map={
                'Authentic': '#2ecc71',
                'Suspect': '#f39c12',
                'Inauthentic': '#e74c3c'
            },
            hole=0.3
        )
        fig_pie.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig_pie, use_container_width=True)

    with col2:
        # AR Comparison Bar Chart
        st.markdown("#### Authenticity Ratio Comparison")

        core_ar = ar_data.get('authenticity_ratio_pct', 0)
        extended_ar = ar_data.get('extended_ar_pct', 0)

        fig_bar = go.Figure(data=[
            go.Bar(
                x=['Core AR', 'Extended AR'],
                y=[core_ar, extended_ar],
                marker_color=['#3498db', '#9b59b6'],
                text=[f"{core_ar:.1f}%", f"{extended_ar:.1f}%"],
                textposition='auto'
            )
        ])
        fig_bar.update_layout(
            yaxis_title="Percentage (%)",
            showlegend=False,
            height=350
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    st.divider()

    # 6D Trust Dimensions Analysis
    st.markdown("### 🔍 6D Trust Dimensions Analysis")

    dimension_breakdown = report.get('dimension_breakdown', {})

    col1, col2 = st.columns([2, 1])

    with col1:
        # Radar Chart
        dimensions = ['Provenance', 'Verification', 'Transparency', 'Coherence', 'Resonance', 'AI Readiness']
        dimension_keys = ['provenance', 'verification', 'transparency', 'coherence', 'resonance', 'ai_readiness']

        scores = [dimension_breakdown.get(key, {}).get('average', 0) for key in dimension_keys]

        fig_radar = go.Figure()
        fig_radar.add_trace(go.Scatterpolar(
            r=scores,
            theta=dimensions,
            fill='toself',
            name='Current Scores',
            line_color='#3498db'
        ))

        fig_radar.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, 1]
                )
            ),
            showlegend=False,
            height=400
        )

        st.plotly_chart(fig_radar, use_container_width=True)

    with col2:
        st.markdown("#### Dimension Scores")

        for dim_name, dim_key in zip(dimensions, dimension_keys):
            dim_data = dimension_breakdown.get(dim_key, {})
            avg_score = dim_data.get('average', 0)

            # Status indicator
            if avg_score >= 0.8:
                status = "🟢"
            elif avg_score >= 0.6:
                status = "🟡"
            elif avg_score >= 0.4:
                status = "🟠"
            else:
                status = "🔴"

            st.markdown(f"**{status} {dim_name}**")
            st.progress(avg_score)
            st.caption(f"Average: {avg_score:.3f} | Min: {dim_data.get('min', 0):.3f} | Max: {dim_data.get('max', 0):.3f}")

    st.divider()

    # Content Items Detail
    st.markdown("### 📝 Content Items Detail")

    items = report.get('items', [])
    appendix = report.get('appendix', [])

    if items:
        # Create DataFrame for display
        items_data = []
        for item in items:
            meta = item.get('meta', {})
            items_data.append({
                'Source': item.get('source', '').upper(),
                'Title': meta.get('title', meta.get('name', ''))[:50] + '...' if meta.get('title') or meta.get('name') else 'N/A',
                'Score': f"{item.get('final_score', 0):.1f}",
                'Classification': item.get('label', 'Unknown').title(),
                'URL': meta.get('source_url', meta.get('url', 'N/A'))
            })

        df = pd.DataFrame(items_data)

        # Color-code by classification
        def color_classification(val):
            if val == 'Authentic':
                return 'background-color: #d4edda'
            elif val == 'Suspect':
                return 'background-color: #fff3cd'
            elif val == 'Inauthentic':
                return 'background-color: #f8d7da'
            return ''

        styled_df = df.style.applymap(color_classification, subset=['Classification'])
        st.dataframe(styled_df, use_container_width=True, height=400)

        # Detailed view expander
        with st.expander("🔎 View Detailed Breakdown"):
            for idx, item_detail in enumerate(appendix[:20]):  # Limit to first 20 for performance
                meta = item_detail.get('meta', {})
                st.markdown(f"**Item {idx + 1}: {meta.get('title', 'Untitled')}**")

                col_a, col_b = st.columns([1, 2])

                with col_a:
                    st.write(f"**Source:** {item_detail.get('source', 'N/A')}")
                    st.write(f"**Final Score:** {item_detail.get('final_score', 0):.2f}")
                    st.write(f"**Classification:** {item_detail.get('label', 'Unknown').title()}")

                with col_b:
                    st.write("**Dimension Scores:**")
                    dims = item_detail.get('dimension_scores', {})
                    dim_cols = st.columns(3)
                    for idx2, (dim_name, score) in enumerate(dims.items()):
                        if score is not None:
                            with dim_cols[idx2 % 3]:
                                st.metric(dim_name.title(), f"{score:.3f}")

                st.divider()

    st.divider()

    # Export section
    st.markdown("### 📥 Export Reports")

    col1, col2, col3 = st.columns(3)

    with col1:
        pdf_path = run_data.get('pdf_path')
        if pdf_path and os.path.exists(pdf_path):
            with open(pdf_path, 'rb') as f:
                st.download_button(
                    label="📄 Download PDF Report",
                    data=f,
                    file_name=os.path.basename(pdf_path),
                    mime="application/pdf",
                    use_container_width=True
                )

    with col2:
        md_path = run_data.get('md_path')
        if md_path and os.path.exists(md_path):
            with open(md_path, 'r') as f:
                st.download_button(
                    label="📝 Download Markdown Report",
                    data=f.read(),
                    file_name=os.path.basename(md_path),
                    mime="text/markdown",
                    use_container_width=True
                )

    with col3:
        # Export raw data as JSON
        st.download_button(
            label="💾 Download Raw Data (JSON)",
            data=json.dumps(report, indent=2, default=str),
            file_name=f"ar_data_{run_data.get('brand_id')}_{run_data.get('run_id')}.json",
            mime="application/json",
            use_container_width=True
        )


def show_history_page():
    """Display analysis history"""
    st.markdown('<div class="main-header">📚 Analysis History</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">View past analysis runs</div>', unsafe_allow_html=True)

    st.divider()

    # Find all past runs
    output_dir = os.path.join(PROJECT_ROOT, 'output', 'webapp_runs')

    if not os.path.exists(output_dir):
        st.info("No analysis history found. Run your first analysis to get started!")
        return

    # Scan for run data files
    run_files = file_glob.glob(os.path.join(output_dir, '*', '_run_data.json'))

    if not run_files:
        st.info("No analysis history found. Run your first analysis to get started!")
        return

    # Load and display runs
    runs = []
    for run_file in run_files:
        try:
            with open(run_file, 'r') as f:
                run_data = json.load(f)
                runs.append(run_data)
        except:
            continue

    # Sort by timestamp (newest first)
    runs.sort(key=lambda x: x.get('timestamp', ''), reverse=True)

    st.write(f"Found {len(runs)} past analysis runs")

    # Display runs
    for run in runs:
        report = run.get('scoring_report', {})
        ar_data = report.get('authenticity_ratio', {})

        with st.expander(f"🔍 {run.get('brand_id')} - {run.get('timestamp')} (AR: {ar_data.get('authenticity_ratio_pct', 0):.1f}%)"):
            col1, col2, col3 = st.columns(3)

            with col1:
                st.write(f"**Run ID:** {run.get('run_id')}")
                st.write(f"**Brand:** {run.get('brand_id')}")
                st.write(f"**Keywords:** {', '.join(run.get('keywords', []))}")

            with col2:
                st.write(f"**Sources:** {', '.join(run.get('sources', []))}")
                st.write(f"**Total Items:** {run.get('total_items', 0)}")
                st.write(f"**AR:** {ar_data.get('authenticity_ratio_pct', 0):.1f}%")

            with col3:
                if st.button(f"View Results", key=f"view_{run.get('run_id')}"):
                    st.session_state['last_run'] = run
                    st.session_state['page'] = 'results'
                    st.rerun()


def main():
    """Main application entry point"""

    # Initialize session state
    if 'page' not in st.session_state:
        st.session_state['page'] = 'home'

    # Sidebar navigation
    with st.sidebar:
        st.markdown("### Navigation")

        if st.button("🏠 Home", use_container_width=True):
            st.session_state['page'] = 'home'
            st.rerun()

        if st.button("🚀 Run Analysis", use_container_width=True):
            st.session_state['page'] = 'analyze'
            st.rerun()

        if st.button("📊 View Results", use_container_width=True):
            st.session_state['page'] = 'results'
            st.rerun()

        if st.button("📚 History", use_container_width=True):
            st.session_state['page'] = 'history'
            st.rerun()

        st.divider()

        # API Status
        st.markdown("### API Status")
        cfg = APIConfig()

        st.write("🌐 Brave Search:", "✅" if True else "❌")
        st.write("🔴 Reddit:", "✅" if (cfg.reddit_client_id and cfg.reddit_client_secret) else "❌")
        st.write("📹 YouTube:", "✅" if cfg.youtube_api_key else "❌")

        st.divider()
        st.caption("Authenticity Ratio™ v2.0")
        st.caption("Trust Stack Framework")

    # Route to appropriate page
    page = st.session_state.get('page', 'home')

    if page == 'home':
        show_home_page()
    elif page == 'analyze':
        show_analyze_page()
    elif page == 'results':
        show_results_page()
    elif page == 'history':
        show_history_page()


if __name__ == '__main__':
    main()
