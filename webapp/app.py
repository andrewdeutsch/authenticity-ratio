"""
Trust Stack Rating Web Application
A comprehensive interface for brand content Trust Stack Rating analysis
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

# Configure logging for the webapp
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

# Helper Functions
def infer_brand_domains(brand_id: str) -> Dict[str, List[str]]:
    """
    Automatically infer likely brand domains from brand_id.

    Args:
        brand_id: Brand identifier (e.g., 'nike', 'coca-cola')

    Returns:
        Dict with 'domains', 'subdomains', and 'social_handles' keys
    """
    if not brand_id:
        return {'domains': [], 'subdomains': [], 'social_handles': []}

    brand_id_clean = brand_id.lower().strip()

    # Handle common brand name variations (for domains, never use spaces)
    brand_variations = []

    # If there are spaces, create hyphenated and combined versions
    if ' ' in brand_id_clean:
        brand_variations.append(brand_id_clean.replace(' ', '-'))  # red-bull
        brand_variations.append(brand_id_clean.replace(' ', ''))   # redbull
    elif '-' in brand_id_clean:
        # If there are hyphens, also try without
        brand_variations.append(brand_id_clean)                    # coca-cola
        brand_variations.append(brand_id_clean.replace('-', ''))   # cocacola
    else:
        # Simple brand name without spaces or hyphens
        brand_variations.append(brand_id_clean)                    # nike

    # Generate common domain patterns
    domains = []
    for variant in brand_variations:
        domains.extend([
            f"{variant}.com",
            f"www.{variant}.com",
        ])

    # Generate common subdomains
    subdomains = []
    for variant in brand_variations:
        subdomains.extend([
            f"blog.{variant}.com",
            f"www.{variant}.com",
            f"shop.{variant}.com",
            f"store.{variant}.com",
        ])

    # Generate social handle variations (include original for handles like "@red bull")
    social_handles = []
    # Add handles based on domain variants
    for variant in brand_variations:
        social_handles.extend([
            f"@{variant}",
            variant,
        ])
    # Also add original brand_id if different (for handles with spaces)
    if brand_id_clean not in brand_variations:
        social_handles.extend([
            f"@{brand_id_clean}",
            brand_id_clean,
        ])

    # Remove duplicates while preserving order
    domains = list(dict.fromkeys(domains))
    subdomains = list(dict.fromkeys(subdomains))
    social_handles = list(dict.fromkeys(social_handles))

    return {
        'domains': domains,
        'subdomains': subdomains,
        'social_handles': social_handles
    }


def generate_rating_recommendation(avg_rating: float, dimension_breakdown: Dict[str, Any], items: List[Dict[str, Any]]) -> str:
    """
    Generate data-driven recommendation based on dimension analysis.

    Args:
        avg_rating: Average rating score (0-100)
        dimension_breakdown: Dictionary with dimension averages
        items: List of analyzed content items

    Returns:
        Comprehensive recommendation string
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

    # Find the dimension with the lowest score
    if dimension_scores:
        lowest_dim_key = min(dimension_scores, key=dimension_scores.get)
        lowest_dim_score = dimension_scores[lowest_dim_key]
        lowest_dim_info = dimension_info[lowest_dim_key]

        # Generate comprehensive summary based on rating band
        if avg_rating >= 80:
            # Excellent - maintain standards with minor optimization
            return f"Your brand content demonstrates high quality with an average rating of {avg_rating:.1f}/100. To reach even greater heights, consider optimizing {lowest_dim_info['name']} (currently at {lowest_dim_score:.1f}/100) by continuing to {lowest_dim_info['recommendation']}."

        elif avg_rating >= 60:
            # Good - focus on improvement area
            return f"Your content shows solid quality with an average rating of {avg_rating:.1f}/100. To improve from Good to Excellent, focus on enhancing {lowest_dim_info['name']} (currently at {lowest_dim_score:.1f}/100) by taking action to {lowest_dim_info['recommendation']}."

        elif avg_rating >= 40:
            # Fair - requires focused attention
            return f"Your content quality is moderate with an average rating of {avg_rating:.1f}/100, requiring attention. To mitigate weak {lowest_dim_info['description']}, you should {lowest_dim_info['recommendation']}. This will help move your rating from Fair to Good or Excellent."

        else:
            # Poor - immediate action needed
            return f"Your content quality is low with an average rating of {avg_rating:.1f}/100, requiring immediate action. Critical issue detected in {lowest_dim_info['name']} (scoring only {lowest_dim_score:.1f}/100). You must {lowest_dim_info['recommendation']} to improve trust signals and content quality."

    else:
        # Fallback if no dimension data available
        return f"Your content has an average rating of {avg_rating:.1f}/100. Comprehensive dimension analysis is needed to provide specific recommendations."

# Page configuration
st.set_page_config(
    page_title="Trust Stack Rating Tool",
    page_icon="⭐",
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
        color: #1565c0;
    }
    .success-box {
        background: #e8f5e9;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #4caf50;
        margin: 1rem 0;
        color: #2e7d32;
    }
    .warning-box {
        background: #fff3e0;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #ff9800;
        margin: 1rem 0;
        color: #e65100;
    }
</style>
""", unsafe_allow_html=True)


def show_home_page():
    """Display the home/overview page"""
    st.markdown('<div class="main-header">⭐ Trust Stack Rating</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Measure and monitor brand content quality across digital channels</div>', unsafe_allow_html=True)

    st.divider()

    # What is Trust Stack Rating section
    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown("### 📊 What is the Trust Stack Rating?")
        st.markdown("""
        The **Trust Stack Rating** is a comprehensive scoring system that evaluates brand-linked content
        across six trust dimensions. Each piece of content receives a **0-100 rating** based on
        signals detected in metadata, structure, and provenance.

        #### Rating Scale (0-100)
        - **80-100** (🟢 Excellent): High-quality, verified content
        - **60-79** (🟡 Good): Solid content with minor improvements needed
        - **40-59** (🟠 Fair): Moderate quality requiring attention
        - **0-39** (🔴 Poor): Low-quality content needing immediate review

        #### Comprehensive Rating
        ```
        Rating = Weighted average across 6 dimensions
        ```
        Each dimension contributes based on configurable weights, with detected attributes
        providing bonuses or penalties.
        """)

    with col2:
        st.markdown("### 🎯 Quick Start")
        st.markdown("""
        1. **Configure** your brand and sources
        2. **Run** the analysis pipeline
        3. **Review** Trust Stack Ratings
        4. **Export** reports for stakeholders
        """)

        if st.button("🚀 Start New Analysis", type="primary", use_container_width=True):
            st.session_state['page'] = 'analyze'
            st.rerun()

    st.divider()

    # 5D Trust Dimensions
    st.markdown("### 🔍 5D Trust Dimensions")
    st.markdown("Each piece of content is scored 0-100 on five dimensions:")

    dimensions_cols = st.columns(3)

    dimensions = [
        ("Provenance", "🔗", "Origin, traceability, metadata integrity"),
        ("Verification", "✓", "Factual accuracy vs. trusted databases"),
        ("Transparency", "👁", "Disclosures, clarity, attribution"),
        ("Coherence", "🔄", "Consistency across channels and time"),
        ("Resonance", "📢", "Cultural fit, organic engagement")
    ]

    for idx, (name, icon, desc) in enumerate(dimensions):
        with dimensions_cols[idx % 3]:
            st.markdown(f"**{icon} {name}**")
            st.caption(desc)

    st.divider()

    # Pipeline overview
    st.markdown("### ⚙️ Analysis Pipeline")

    pipeline_steps = [
        ("1. Ingest", "Collect raw content and data from multiple sources\n\n_→ Purpose: Gather inputs._"),
        ("2. Normalize", "Standardize data structure, remove noise, and extract core metadata (source, title, author, date).\n\n_→ Purpose: Prepare clean, consistent inputs._"),
        ("3. Enrich", "Add contextual intelligence — provenance tags, schema markup, fact-check references, and entity recognition.\n\n_→ Purpose: Add meaning and traceability._"),
        ("4. Analyze", "Evaluate enriched content for trust-related patterns and attributes across the five dimensions (Provenance, Resonance, Coherence, Transparency, Verification).\n\n_→ Purpose: Interpret trust signals in context._"),
        ("5. Score", "Apply the 5D rubric to quantify each content item on a 0–100 scale per dimension.\n\n_→ Purpose: Turn analysis into measurable data._"),
        ("6. Synthesize", "Aggregate and weight results into an overall Trust Index or benchmark, highlighting gaps and strengths.\n\n_→ Purpose: Combine scores into a holistic rating._"),
        ("7. Report", "Generate visual outputs (PDF, dashboard, Markdown) with trust maps, insights, and recommended actions.\n\n_→ Purpose: Communicate results and next steps._")
    ]

    cols = st.columns(7)
    for idx, (step, desc) in enumerate(pipeline_steps):
        with cols[idx]:
            st.markdown(f"**{step}**")
            st.caption(desc)


def show_analyze_page():
    """Display the analysis configuration and execution page"""
    st.markdown('<div class="main-header">🚀 Run Analysis</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Configure and execute Trust Stack Rating analysis</div>', unsafe_allow_html=True)

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

            # Search Provider Selection
            st.markdown("**Web Search Provider**")

            # Check which providers are available
            brave_available = bool(cfg.brave_api_key)
            serper_available = bool(cfg.serper_api_key)

            # Determine default provider
            default_provider = 'serper' if serper_available else 'brave'

            # Create provider options
            provider_options = []
            provider_labels = []

            if brave_available:
                provider_options.append('brave')
                provider_labels.append('🌐 Brave')

            if serper_available:
                provider_options.append('serper')
                provider_labels.append('🔍 Serper')

            if not provider_options:
                st.error("⚠️ No search provider API keys configured. Please set BRAVE_API_KEY or SERPER_API_KEY.")
                search_provider = None
            elif len(provider_options) == 1:
                # Only one provider available, show as info
                search_provider = provider_options[0]
                st.info(f"Using {provider_labels[0]} (only available provider)")
            else:
                # Multiple providers available, let user choose
                default_index = provider_options.index(default_provider) if default_provider in provider_options else 0
                search_provider = st.radio(
                    "Select search provider:",
                    options=provider_options,
                    format_func=lambda x: '🌐 Brave' if x == 'brave' else '🔍 Serper',
                    index=default_index,
                    horizontal=True,
                    help="Choose between Brave Search or Serper (Google) for web search"
                )

            # Web search settings
            use_web_search = st.checkbox("🌐 Enable Web Search", value=True, help="Search web content via selected provider")
            web_pages = st.number_input("Web pages to fetch", min_value=1, max_value=100, value=10, step=1) if use_web_search else 10

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

        # URL Collection Strategy - Simplified Interface
        with st.expander("⚙️ URL Collection Strategy", expanded=False):
            st.markdown("**Choose which URLs to collect:**")

            # Initialize session state for collection strategy if not exists
            if 'collection_strategy' not in st.session_state:
                st.session_state['collection_strategy'] = 'both'

            collection_strategy = st.radio(
                "Collection Type",
                options=["brand_controlled", "third_party", "both"],
                format_func=lambda x: {
                    "brand_controlled": "🏢 Brand-Controlled Only",
                    "third_party": "🌐 3rd Party Only",
                    "both": "⚖️ Both (Balanced Collection)"
                }[x],
                index=["brand_controlled", "third_party", "both"].index(st.session_state['collection_strategy']),
                help="Select which type of URLs to collect for analysis",
                key='collection_strategy_radio'
            )

            # Update session state
            st.session_state['collection_strategy'] = collection_strategy

            # Show different help text based on selection
            if collection_strategy == "brand_controlled":
                st.info("📝 **Collecting only from brand-owned domains** (website, blog, social media). Domains auto-detected from brand ID.")
            elif collection_strategy == "third_party":
                st.info("📝 **Collecting only from external sources** (news, reviews, forums, social media).")
            else:  # both
                st.info("📝 **Collecting from both brand-owned and 3rd party sources** for holistic assessment (recommended 60/40 ratio).")

            # Only show ratio slider when "Both" is selected
            if collection_strategy == "both":
                st.markdown("**Adjust Collection Ratio:**")
                col_ratio1, col_ratio2 = st.columns(2)
                with col_ratio1:
                    brand_owned_ratio = st.slider(
                        "Brand-Owned Ratio (%)",
                        min_value=0,
                        max_value=100,
                        value=60,
                        step=5,
                        help="Percentage of URLs from brand-owned domains"
                    )
                with col_ratio2:
                    third_party_ratio = 100 - brand_owned_ratio
                    st.metric("3rd Party Ratio (%)", f"{third_party_ratio}%")
                    st.caption("Auto-calculated")
            else:
                # Set ratio to 100/0 or 0/100 based on selection
                if collection_strategy == "brand_controlled":
                    brand_owned_ratio = 100
                else:  # third_party
                    brand_owned_ratio = 0

            st.divider()

            # Auto-infer brand domains from brand_id
            if collection_strategy in ["brand_controlled", "both"]:
                # Automatically infer brand domains
                inferred = infer_brand_domains(brand_id)

                st.info(f"🤖 **Auto-detected brand domains:** {', '.join(inferred['domains'][:3])}{'...' if len(inferred['domains']) > 3 else ''}")

                # Advanced override option
                with st.expander("⚙️ Advanced: Customize Brand Domains (Optional)", expanded=False):
                    st.caption("The system automatically detects brand domains. Only customize if you need specific overrides.")

                    brand_domains_input = st.text_input(
                        "Override Brand Domains",
                        value="",
                        placeholder="Leave empty to use auto-detected domains",
                        help="Comma-separated list. Leave empty to use auto-detected domains."
                    )

                    brand_subdomains_input = st.text_input(
                        "Additional Subdomains",
                        value="",
                        placeholder="e.g., blog.nike.com, help.nike.com",
                        help="Comma-separated list of specific brand subdomains to add"
                    )

                    brand_social_handles_input = st.text_input(
                        "Additional Social Handles",
                        value="",
                        placeholder="e.g., @nikerunning, nikebasketball",
                        help="Comma-separated list of additional brand social media handles"
                    )

                # Use auto-detected or manual override
                if brand_domains_input.strip():
                    brand_domains = [d.strip() for d in brand_domains_input.split(',') if d.strip()]
                else:
                    brand_domains = inferred['domains']

                # Combine auto-detected with additional manual entries
                if brand_subdomains_input.strip():
                    manual_subdomains = [d.strip() for d in brand_subdomains_input.split(',') if d.strip()]
                    brand_subdomains = list(dict.fromkeys(inferred['subdomains'] + manual_subdomains))
                else:
                    brand_subdomains = inferred['subdomains']

                if brand_social_handles_input.strip():
                    manual_handles = [h.strip() for h in brand_social_handles_input.split(',') if h.strip()]
                    brand_social_handles = list(dict.fromkeys(inferred['social_handles'] + manual_handles))
                else:
                    brand_social_handles = inferred['social_handles']

                # Show confirmation
                if collection_strategy == "both":
                    third_party_ratio = 100 - brand_owned_ratio
                    st.success(f"✓ Balanced collection enabled: {brand_owned_ratio}% brand-owned / {third_party_ratio}% 3rd party")
                else:
                    st.success(f"✓ Brand-controlled collection enabled with {len(brand_domains)} auto-detected domains")
            else:
                # No brand identification needed for 3rd party only
                brand_domains = []
                brand_subdomains = []
                brand_social_handles = []

        st.divider()

        col_search, col_submit, col_clear = st.columns([1, 1, 3])
        with col_search:
            search_urls = st.form_submit_button("🔍 Search URLs", use_container_width=True)
        with col_submit:
            submit = st.form_submit_button("▶️ Run Analysis", type="primary", use_container_width=True)
        with col_clear:
            if st.form_submit_button("Clear Results", use_container_width=True):
                st.session_state['last_run'] = None
                st.session_state['found_urls'] = None
                st.rerun()

    # Handle URL search
    if search_urls:
        # Validate inputs
        if not brand_id or not keywords:
            st.error("⚠️ Brand ID and Keywords are required")
            return

        # Build sources list
        sources = []
        if use_web_search:
            sources.append('web')
        if use_reddit:
            sources.append('reddit')
        if use_youtube:
            sources.append('youtube')

        if not sources:
            st.error("⚠️ Please select at least one data source")
            return

        # Search for URLs without running analysis
        search_for_urls(brand_id, keywords.split(), sources, web_pages, search_provider,
                       brand_domains, brand_subdomains, brand_social_handles,
                       collection_strategy, brand_owned_ratio)

    # Display found URLs for selection
    if 'found_urls' in st.session_state and st.session_state['found_urls']:
        st.markdown("### 📋 Found URLs")

        found_urls = st.session_state['found_urls']

        # Separate URLs into brand-owned and third-party
        brand_owned_urls = [u for u in found_urls if u.get('is_brand_owned', False)]
        third_party_urls = [u for u in found_urls if not u.get('is_brand_owned', False)]

        # Overall select/deselect buttons
        col_sel_all, col_desel_all, col_stats = st.columns([1, 1, 2])
        with col_sel_all:
            if st.button("✓ Select All"):
                for url_data in found_urls:
                    url_data['selected'] = True
                st.rerun()
        with col_desel_all:
            if st.button("✗ Deselect All"):
                for url_data in found_urls:
                    url_data['selected'] = False
                st.rerun()
        with col_stats:
            st.info(f"📊 Selected {sum(1 for u in found_urls if u.get('selected', True))} of {len(found_urls)} URLs")

        st.divider()

        # Brand-Owned URLs Section
        if brand_owned_urls:
            st.markdown("#### 🏢 Brand-Owned URLs")
            st.caption(f"{len(brand_owned_urls)} URLs from brand domains")

            for idx, url_data in enumerate(brand_owned_urls):
                col1, col2 = st.columns([1, 10])
                with col1:
                    url_data['selected'] = st.checkbox(
                        "Select",
                        value=url_data.get('selected', True),
                        key=f"brand_url_{idx}",
                        label_visibility="collapsed"
                    )
                with col2:
                    # Tier badge
                    tier = url_data.get('source_tier', 'unknown')
                    tier_emoji = {
                        'primary_website': '🏠',
                        'content_hub': '📚',
                        'direct_to_consumer': '🛒',
                        'brand_social': '📱'
                    }.get(tier, '📄')
                    tier_label = tier.replace('_', ' ').title()

                    st.markdown(f"**{url_data['title'][:70]}{'...' if len(url_data['title']) > 70 else ''}** {tier_emoji} `{tier_label}`")
                    st.caption(f"🔗 {url_data['url']}")

            st.divider()

        # Third-Party URLs Section
        if third_party_urls:
            st.markdown("#### 🌐 Third-Party URLs")
            st.caption(f"{len(third_party_urls)} URLs from external sources")

            for idx, url_data in enumerate(third_party_urls):
                col1, col2 = st.columns([1, 10])
                with col1:
                    url_data['selected'] = st.checkbox(
                        "Select",
                        value=url_data.get('selected', True),
                        key=f"third_party_url_{idx}",
                        label_visibility="collapsed"
                    )
                with col2:
                    # Tier badge
                    tier = url_data.get('source_tier', 'unknown')
                    tier_emoji = {
                        'news_media': '📰',
                        'user_generated': '👥',
                        'expert_professional': '🎓',
                        'marketplace': '🏪'
                    }.get(tier, '🌐')
                    tier_label = tier.replace('_', ' ').title()

                    st.markdown(f"**{url_data['title'][:70]}{'...' if len(url_data['title']) > 70 else ''}** {tier_emoji} `{tier_label}`")
                    st.caption(f"🔗 {url_data['url']}")

    if submit:
        # Validate inputs
        if not brand_id or not keywords:
            st.error("⚠️ Brand ID and Keywords are required")
            return

        # Build sources list
        sources = []
        if use_web_search:
            sources.append('web')
        if use_reddit:
            sources.append('reddit')
        if use_youtube:
            sources.append('youtube')

        if not sources:
            st.error("⚠️ Please select at least one data source")
            return

        # Check if URLs were searched and selected
        selected_urls = None
        if 'found_urls' in st.session_state and st.session_state['found_urls']:
            selected_urls = [u for u in st.session_state['found_urls'] if u.get('selected', True)]
            if not selected_urls:
                st.error("⚠️ Please select at least one URL to analyze")
                return

        # Run pipeline
        run_analysis(brand_id, keywords.split(), sources, max_items, web_pages, include_comments, selected_urls, search_provider,
                    brand_domains, brand_subdomains, brand_social_handles)


def detect_brand_owned_url(url: str, brand_id: str, brand_domains: List[str] = None, brand_subdomains: List[str] = None, brand_social_handles: List[str] = None) -> Dict[str, Any]:
    """
    Detect if a URL is a brand-owned property using the domain classifier.

    Returns:
        Dict with keys: is_brand_owned (bool), source_type (str), source_tier (str), reason (str)
    """
    try:
        from ingestion.domain_classifier import classify_url, URLCollectionConfig, URLSourceType

        # Create config for classification
        if brand_domains:
            config = URLCollectionConfig(
                brand_owned_ratio=0.6,
                third_party_ratio=0.4,
                brand_domains=brand_domains or [],
                brand_subdomains=brand_subdomains or [],
                brand_social_handles=brand_social_handles or []
            )
        else:
            # Fallback to simple heuristic if no domains provided
            from urllib.parse import urlparse
            domain = urlparse(url).netloc.lower().replace('www.', '')
            is_owned = brand_id.lower() in domain
            return {
                'is_brand_owned': is_owned,
                'source_type': 'brand_owned' if is_owned else 'third_party',
                'source_tier': 'primary_website' if is_owned else 'user_generated',
                'reason': f"Simple heuristic: {brand_id} {'found' if is_owned else 'not found'} in domain"
            }

        # Use domain classifier
        classification = classify_url(url, config)
        return {
            'is_brand_owned': classification.source_type == URLSourceType.BRAND_OWNED,
            'source_type': classification.source_type.value,
            'source_tier': classification.tier.value if classification.tier else 'unknown',
            'reason': classification.reason
        }
    except Exception as e:
        # Fallback on error
        return {
            'is_brand_owned': False,
            'source_type': 'unknown',
            'source_tier': 'unknown',
            'reason': f"Classification error: {str(e)}"
        }


def search_for_urls(brand_id: str, keywords: List[str], sources: List[str], web_pages: int, search_provider: str = 'serper',
                    brand_domains: List[str] = None, brand_subdomains: List[str] = None, brand_social_handles: List[str] = None,
                    collection_strategy: str = 'both', brand_owned_ratio: int = 60):
    """Search for URLs and store them in session state for user selection"""
    import os
    import logging

    # Set up logging
    logger = logging.getLogger(__name__)

    status_text = st.empty()
    progress_bar = st.progress(0)

    try:
        status_text.text("🔍 Initializing search...")
        progress_bar.progress(10)

        found_urls = []

        # Web search (using selected provider: Brave or Serper)
        if 'web' in sources:
            query = ' '.join(keywords)

            provider_display = '🌐 Brave' if search_provider == 'brave' else '🔍 Serper'
            status_text.text(f"{provider_display} Searching for '{query}' (requesting {web_pages} URLs)...")
            progress_bar.progress(30)

            try:
                # Configure timeout for larger requests (scale with number of pages)
                # Each pagination batch needs time, so scale appropriately
                original_timeout = os.environ.get('BRAVE_API_TIMEOUT')
                timeout_seconds = min(30, 10 + (web_pages // 10))
                os.environ['BRAVE_API_TIMEOUT'] = str(timeout_seconds)

                # Calculate expected number of API requests
                if search_provider == 'brave':
                    max_per_request = int(os.getenv('BRAVE_API_MAX_COUNT', '20'))
                else:  # serper
                    # Serper returns 10 results per page, regardless of the num parameter
                    max_per_request = 10

                expected_requests = (web_pages + max_per_request - 1) // max_per_request  # Ceiling division

                if expected_requests > 1:
                    logger.info(f"Searching {search_provider}: query={query}, size={web_pages}, will make ~{expected_requests} paginated requests")
                    status_text.text(f"{provider_display} Searching (will make ~{expected_requests} API requests for {web_pages} URLs)...")
                else:
                    logger.info(f"Searching {search_provider}: query={query}, size={web_pages}")

                # Create URLCollectionConfig for ratio enforcement
                url_collection_config = None
                if collection_strategy in ["brand_controlled", "both", "third_party"] and brand_domains:
                    from ingestion.domain_classifier import URLCollectionConfig

                    # Convert percentage to decimal ratio
                    brand_ratio = brand_owned_ratio / 100.0
                    third_party_ratio = 1.0 - brand_ratio

                    url_collection_config = URLCollectionConfig(
                        brand_owned_ratio=brand_ratio,
                        third_party_ratio=third_party_ratio,
                        brand_domains=brand_domains or [],
                        brand_subdomains=brand_subdomains or [],
                        brand_social_handles=brand_social_handles or []
                    )
                    logger.info(f"Created URLCollectionConfig with {collection_strategy} strategy: {brand_ratio:.1%} brand-owned, {third_party_ratio:.1%} 3rd party")

                progress_bar.progress(50)

                # Use collect functions for ratio enforcement
                search_results = []
                # Use 3x pool size - with content validation before pool checks, this should be sufficient
                pool_size = web_pages * 3

                if search_provider == 'brave':
                    from ingestion.brave_search import collect_brave_pages
                    pages = collect_brave_pages(
                        query=query,
                        target_count=web_pages,
                        pool_size=pool_size,
                        url_collection_config=url_collection_config
                    )
                    # Convert to search result format
                    for page in pages:
                        search_results.append({
                            'url': page.get('url', ''),
                            'title': page.get('title', 'No title'),
                            'snippet': page.get('body', '')[:200]
                        })
                else:  # serper
                    from ingestion.serper_search import collect_serper_pages
                    pages = collect_serper_pages(
                        query=query,
                        target_count=web_pages,
                        pool_size=pool_size,
                        url_collection_config=url_collection_config
                    )
                    # Convert to search result format
                    for page in pages:
                        search_results.append({
                            'url': page.get('url', ''),
                            'title': page.get('title', 'No title'),
                            'snippet': page.get('body', '')[:200]
                        })

                progress_bar.progress(70)
                status_text.text(f"✓ Collected {len(search_results)} URLs (target: {web_pages}) with {collection_strategy} ratio enforcement, processing...")

                # Restore original timeout
                if original_timeout is not None:
                    os.environ['BRAVE_API_TIMEOUT'] = original_timeout
                else:
                    os.environ.pop('BRAVE_API_TIMEOUT', None)

                if not search_results:
                    st.warning(f"⚠️ No search results found. Try different keywords or check your {search_provider.upper()} API configuration.")

                    # Provide helpful diagnostics
                    st.info("**Troubleshooting tips:**")
                    if search_provider == 'brave':
                        st.markdown("""
                        - **Check your Brave API key**: Ensure `BRAVE_API_KEY` environment variable is set
                        - **Check the logs**: Look at the terminal/console for detailed error messages
                        - **Try fewer pages**: Start with 10-20 pages to test the connection
                        - **Verify API quota**: Your Brave API plan may have reached its limit
                        - **Check search query**: Try simpler, more common keywords first
                        """)
                    else:  # serper
                        st.markdown("""
                        - **Check your Serper API key**: Ensure `SERPER_API_KEY` environment variable is set
                        - **Check the logs**: Look at the terminal/console for detailed error messages
                        - **Try fewer pages**: Start with 10-20 pages to test the connection
                        - **Verify API quota**: Your Serper API plan may have reached its limit
                        - **Check search query**: Try simpler, more common keywords first
                        """)

                    # Show current configuration for debugging
                    with st.expander("🔍 Show Configuration Details"):
                        if search_provider == 'brave':
                            st.code(f"""
Provider: Brave Search
Query: {query}
Pages requested: {web_pages}
Timeout: {timeout_seconds}s
API Key set: {'Yes' if os.getenv('BRAVE_API_KEY') else 'No'}
API Endpoint: {os.getenv('BRAVE_API_ENDPOINT', 'https://api.search.brave.com/res/v1/web/search')}
""")
                        else:
                            st.code(f"""
Provider: Serper (Google Search)
Query: {query}
Pages requested: {web_pages}
Timeout: {timeout_seconds}s
API Key set: {'Yes' if os.getenv('SERPER_API_KEY') else 'No'}
""")

                    progress_bar.empty()
                    status_text.empty()
                    return

                for result in search_results:
                    url = result.get('url', '')
                    if url:
                        classification = detect_brand_owned_url(url, brand_id, brand_domains, brand_subdomains, brand_social_handles)
                        found_urls.append({
                            'url': url,
                            'title': result.get('title', 'No title'),
                            'description': result.get('snippet', result.get('description', '')),
                            'is_brand_owned': classification['is_brand_owned'],
                            'source_type': classification['source_type'],
                            'source_tier': classification['source_tier'],
                            'classification_reason': classification['reason'],
                            'selected': True,  # Default to selected
                            'source': search_provider
                        })

                # Prioritize brand-owned URLs by sorting them first
                # This ensures brand domains appear at the top of the list
                found_urls.sort(key=lambda x: (not x['is_brand_owned'], x['url']))
                logger.info(f"Sorted {len(found_urls)} URLs with brand-owned URLs prioritized")

                progress_bar.progress(90)
                st.session_state['found_urls'] = found_urls

                brand_owned_count = sum(1 for u in found_urls if u['is_brand_owned'])
                third_party_count = sum(1 for u in found_urls if not u['is_brand_owned'])

                progress_bar.progress(100)
                status_text.empty()
                progress_bar.empty()

                st.success(f"✓ Found {len(found_urls)} URLs ({brand_owned_count} brand-owned, {third_party_count} third-party)")
                st.rerun()

            except TimeoutError as e:
                logger.error(f"Timeout error during {search_provider} search: {e}")
                st.error(f"⏱️ Search timed out after {timeout_seconds} seconds. Try requesting fewer URLs or check your network connection.")

            except ConnectionError as e:
                logger.error(f"Connection error during {search_provider} search: {e}")
                st.error(f"🌐 Connection error: Could not reach {search_provider.upper()} API. Please check your internet connection.")

            except Exception as e:
                logger.error(f"Error during {search_provider} search: {type(e).__name__}: {e}")
                st.error(f"❌ Search failed: {type(e).__name__}: {str(e)}")

                # Show more helpful error messages for common issues
                if 'api' in str(e).lower() or 'key' in str(e).lower():
                    api_key_name = 'BRAVE_API_KEY' if search_provider == 'brave' else 'SERPER_API_KEY'
                    st.info(f"💡 Tip: Check that your {api_key_name} is set correctly in your environment.")
                elif 'timeout' in str(e).lower():
                    st.info("💡 Tip: Try reducing the number of web pages to fetch, or check your network connection.")

    except Exception as e:
        logger.error(f"Unexpected error in search_for_urls: {type(e).__name__}: {e}")
        st.error(f"❌ Unexpected error: {type(e).__name__}: {str(e)}")

    finally:
        # Clean up progress indicators
        try:
            progress_bar.empty()
            status_text.empty()
        except:
            pass


def run_analysis(brand_id: str, keywords: List[str], sources: List[str], max_items: int, web_pages: int, include_comments: bool,
                 selected_urls: List[Dict] = None, search_provider: str = 'serper',
                 brand_domains: List[str] = None, brand_subdomains: List[str] = None, brand_social_handles: List[str] = None):
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

        from ingestion.brave_search import collect_brave_pages, fetch_page
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

        # Web search ingestion (using selected provider)
        if 'web' in sources:
            # If URLs were pre-selected, use only those
            if selected_urls:
                # Filter URLs from the current search provider
                selected_web_urls = [u for u in selected_urls if u['source'] in ['brave', 'serper', 'web']]
                collected = []

                for url_data in selected_web_urls:
                    try:
                        page_data = fetch_page(url_data['url'])
                        if page_data and page_data.get('body'):
                            # Add brand-owned flag to metadata
                            page_data['is_brand_owned'] = url_data.get('is_brand_owned', False)
                            collected.append(page_data)
                    except Exception as e:
                        st.warning(f"⚠️ Could not fetch {url_data['url']}: {str(e)}")

                st.info(f"✓ Fetched {len(collected)} of {len(selected_web_urls)} selected web pages")
            else:
                # Original behavior: search and fetch automatically
                query = ' '.join(keywords)

                # Use the unified search interface with the selected provider
                from ingestion.search_unified import search
                search_results = search(query, size=web_pages, provider=search_provider)

                collected = []
                for result in search_results:
                    url = result.get('url', '')
                    if url:
                        try:
                            page_data = fetch_page(url)
                            if page_data and page_data.get('body'):
                                # Add metadata from search result
                                page_data['search_title'] = result.get('title', '')
                                page_data['search_snippet'] = result.get('snippet', '')
                                classification = detect_brand_owned_url(url, brand_id, brand_domains, brand_subdomains, brand_social_handles)
                                page_data['is_brand_owned'] = classification['is_brand_owned']
                                page_data['source_type'] = classification['source_type']
                                page_data['source_tier'] = classification['source_tier']
                                collected.append(page_data)
                        except Exception as e:
                            st.warning(f"⚠️ Could not fetch {url}: {str(e)}")

                st.info(f"✓ Collected {len(collected)} web pages using {search_provider}")

            # Convert to NormalizedContent
            for i, c in enumerate(collected):
                url = c.get('url')
                content_id = f"{search_provider}_{i}_{abs(hash(url or ''))}"
                is_brand_owned = c.get('is_brand_owned', False)

                meta = {
                    'source_url': url or '',
                    'content_type': 'web',
                    'title': c.get('title', ''),
                    'description': c.get('body', '')[:200],
                    'is_brand_owned': is_brand_owned,  # Add brand-owned flag to metadata
                    'search_provider': search_provider  # Track which provider was used
                }
                if c.get('terms'):
                    meta['terms'] = c.get('terms')
                if c.get('privacy'):
                    meta['privacy'] = c.get('privacy')

                nc = NormalizedContent(
                    content_id=content_id,
                    src=search_provider,
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
                    platform_type='web',
                    source_type=c.get('source_type', 'unknown'),
                    source_tier=c.get('source_tier', 'unknown')
                )
                all_content.append(nc)

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

        # Report URL distribution if brand domains were provided
        if brand_domains:
            brand_owned_count = sum(1 for c in normalized_content if getattr(c, 'source_type', None) == 'brand_owned')
            third_party_count = sum(1 for c in normalized_content if getattr(c, 'source_type', None) == 'third_party')
            unknown_count = len(normalized_content) - brand_owned_count - third_party_count

            st.info(f"""
            📊 **URL Distribution Summary**
            - Brand-owned: {brand_owned_count} ({brand_owned_count/len(normalized_content)*100:.1f}%)
            - 3rd party: {third_party_count} ({third_party_count/len(normalized_content)*100:.1f}%)
            {f"- Unknown: {unknown_count} ({unknown_count/len(normalized_content)*100:.1f}%)" if unknown_count > 0 else ""}
            - Total: {len(normalized_content)}
            """)

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
    items = report.get('items', [])

    # Calculate average comprehensive rating
    if items:
        avg_rating = sum(item.get('final_score', 0) for item in items) / len(items)
    else:
        avg_rating = 0

    # Calculate rating distribution
    excellent = sum(1 for item in items if item.get('final_score', 0) >= 80)
    good = sum(1 for item in items if 60 <= item.get('final_score', 0) < 80)
    fair = sum(1 for item in items if 40 <= item.get('final_score', 0) < 60)
    poor = sum(1 for item in items if item.get('final_score', 0) < 40)

    # Header
    st.markdown('<div class="main-header">⭐ Trust Stack Results</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="sub-header">Brand: {run_data.get("brand_id")} | Run: {run_data.get("run_id")}</div>', unsafe_allow_html=True)

    st.divider()

    # Key Metrics
    st.markdown("### 🎯 Key Metrics")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="Average Rating",
            value=f"{avg_rating:.1f}/100",
            delta=None
        )

    with col2:
        st.metric(
            label="Total Content",
            value=f"{len(items):,}"
        )

    with col3:
        st.metric(
            label="Excellent (80+)",
            value=f"{excellent:,}",
            delta=f"{(excellent/len(items)*100):.0f}%" if items else "0%"
        )

    with col4:
        st.metric(
            label="Poor (<40)",
            value=f"{poor:,}",
            delta=f"{(poor/len(items)*100):.0f}%" if items else "0%"
        )

    # Rating Interpretation with Data-Driven Recommendations
    dimension_breakdown = report.get('dimension_breakdown', {})
    recommendation = generate_rating_recommendation(avg_rating, dimension_breakdown, items)

    if avg_rating >= 80:
        st.markdown(f'<div class="success-box">🟢 <b>Excellent</b> - {recommendation}</div>', unsafe_allow_html=True)
    elif avg_rating >= 60:
        st.markdown(f'<div class="info-box">🟡 <b>Good</b> - {recommendation}</div>', unsafe_allow_html=True)
    elif avg_rating >= 40:
        st.markdown(f'<div class="warning-box">🟠 <b>Fair</b> - {recommendation}</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="warning-box">🔴 <b>Poor</b> - {recommendation}</div>', unsafe_allow_html=True)

    st.divider()

    # Visualizations
    col1, col2 = st.columns(2)

    with col1:
        # Rating Distribution Pie Chart
        st.markdown("#### Rating Distribution")

        fig_pie = px.pie(
            values=[excellent, good, fair, poor],
            names=['Excellent (80+)', 'Good (60-79)', 'Fair (40-59)', 'Poor (<40)'],
            color_discrete_map={
                'Excellent (80+)': '#2ecc71',
                'Good (60-79)': '#3498db',
                'Fair (40-59)': '#f39c12',
                'Poor (<40)': '#e74c3c'
            },
            hole=0.3
        )
        fig_pie.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig_pie, use_container_width=True, config={'displayModeBar': False})

    with col2:
        # Rating Score Distribution Histogram
        st.markdown("#### Score Distribution")

        scores = [item.get('final_score', 0) for item in items]

        fig_hist = go.Figure(data=[
            go.Histogram(
                x=scores,
                nbinsx=20,
                marker_color='#3498db',
                opacity=0.7
            )
        ])
        fig_hist.update_layout(
            xaxis_title="Rating Score (0-100)",
            yaxis_title="Number of Items",
            showlegend=False,
            height=350
        )
        # Add threshold lines
        fig_hist.add_vline(x=80, line_dash="dash", line_color="green", annotation_text="Excellent")
        fig_hist.add_vline(x=60, line_dash="dash", line_color="blue", annotation_text="Good")
        fig_hist.add_vline(x=40, line_dash="dash", line_color="orange", annotation_text="Fair")
        st.plotly_chart(fig_hist, use_container_width=True, config={'displayModeBar': False})

    st.divider()

    # 5D Trust Dimensions Analysis
    st.markdown("### 🔍 5D Trust Dimensions Breakdown")

    dimension_breakdown = report.get('dimension_breakdown', {})

    col1, col2 = st.columns([2, 1])

    with col1:
        # Radar Chart
        dimensions = ['Provenance', 'Verification', 'Transparency', 'Coherence', 'Resonance']
        dimension_keys = ['provenance', 'verification', 'transparency', 'coherence', 'resonance']

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

        st.plotly_chart(fig_radar, use_container_width=True, config={'displayModeBar': False})

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
            st.caption(f"Score: {avg_score*100:.1f}/100 | Range: {dim_data.get('min', 0)*100:.1f} - {dim_data.get('max', 0)*100:.1f}")

    st.divider()

    # Content Items Detail
    st.markdown("### 📝 Content Items Detail")

    appendix = report.get('appendix', [])

    if items:
        # Create DataFrame for display
        items_data = []
        for item in items:
            meta = item.get('meta', {})
            score = item.get('final_score', 0)

            # Determine rating band
            if score >= 80:
                rating_band = '🟢 Excellent'
            elif score >= 60:
                rating_band = '🟡 Good'
            elif score >= 40:
                rating_band = '🟠 Fair'
            else:
                rating_band = '🔴 Poor'

            items_data.append({
                'Source': item.get('source', '').upper(),
                'Title': meta.get('title', meta.get('name', ''))[:50] + '...' if meta.get('title') or meta.get('name') else 'N/A',
                'Score': f"{score:.1f}",
                'Rating': rating_band,
                'URL': meta.get('source_url', meta.get('url', 'N/A'))
            })

        df = pd.DataFrame(items_data)

        # Color-code by rating band
        def color_rating(val):
            if '🟢' in val:
                return 'background-color: #d4edda; color: #155724'
            elif '🟡' in val:
                return 'background-color: #d1ecf1; color: #0c5460'
            elif '🟠' in val:
                return 'background-color: #fff3cd; color: #856404'
            elif '🔴' in val:
                return 'background-color: #f8d7da; color: #721c24'
            return ''

        styled_df = df.style.applymap(color_rating, subset=['Rating'])
        st.dataframe(styled_df, use_container_width=True, height=400)

        # Detailed view expander
        with st.expander("🔎 View Detailed Breakdown"):
            for idx, item_detail in enumerate(appendix[:20]):  # Limit to first 20 for performance
                meta = item_detail.get('meta', {})
                st.markdown(f"**Item {idx + 1}: {meta.get('title', 'Untitled')}**")

                col_a, col_b = st.columns([1, 2])

                with col_a:
                    item_score = item_detail.get('final_score', 0)
                    if item_score >= 80:
                        rating_band = '🟢 Excellent'
                    elif item_score >= 60:
                        rating_band = '🟡 Good'
                    elif item_score >= 40:
                        rating_band = '🟠 Fair'
                    else:
                        rating_band = '🔴 Poor'

                    st.write(f"**Source:** {item_detail.get('source', 'N/A')}")
                    st.write(f"**Rating Score:** {item_score:.1f}/100")
                    st.write(f"**Rating Band:** {rating_band}")

                with col_b:
                    st.write("**Dimension Scores:**")
                    dims = item_detail.get('dimension_scores', {})
                    dim_cols = st.columns(3)
                    for idx2, (dim_name, score) in enumerate(dims.items()):
                        if score is not None:
                            with dim_cols[idx2 % 3]:
                                st.metric(dim_name.title(), f"{score*100:.1f}/100")

                st.divider()

    st.divider()

    # Legacy AR Metrics (optional)
    with st.expander("📊 Legacy Metrics (Authenticity Ratio)"):
        st.caption("These metrics are provided for backward compatibility. The primary focus is Trust Stack Ratings.")

        ar_data = report.get('authenticity_ratio', {})

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric(
                label="Core AR",
                value=f"{ar_data.get('authenticity_ratio_pct', 0):.1f}%"
            )

        with col2:
            st.metric(
                label="Extended AR",
                value=f"{ar_data.get('extended_ar_pct', 0):.1f}%"
            )

        with col3:
            st.metric(
                label="Authentic Items",
                value=f"{ar_data.get('authentic_items', 0):,}"
            )

        with col4:
            st.metric(
                label="Inauthentic Items",
                value=f"{ar_data.get('inauthentic_items', 0):,}"
            )

        st.caption("**Note:** AR classifies content as Authentic/Suspect/Inauthentic using fixed thresholds. Trust Stack Ratings provide more nuanced 0-100 scores across 6 dimensions.")

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
            file_name=f"trust_stack_data_{run_data.get('brand_id')}_{run_data.get('run_id')}.json",
            mime="application/json",
            use_container_width=True
        )


def show_history_page():
    """Display analysis history"""
    st.markdown('<div class="main-header">📚 Rating History</div>', unsafe_allow_html=True)
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
        items = report.get('items', [])

        # Calculate average rating for this run
        if items:
            avg_rating = sum(item.get('final_score', 0) for item in items) / len(items)
        else:
            avg_rating = 0

        with st.expander(f"⭐ {run.get('brand_id')} - {run.get('timestamp')} (Avg Rating: {avg_rating:.1f}/100)"):
            col1, col2, col3 = st.columns(3)

            with col1:
                st.write(f"**Run ID:** {run.get('run_id')}")
                st.write(f"**Brand:** {run.get('brand_id')}")
                st.write(f"**Keywords:** {', '.join(run.get('keywords', []))}")

            with col2:
                st.write(f"**Sources:** {', '.join(run.get('sources', []))}")
                st.write(f"**Total Items:** {run.get('total_items', 0)}")
                st.write(f"**Avg Rating:** {avg_rating:.1f}/100")

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

        st.markdown("**Search Providers:**")
        st.write("🌐 Brave:", "✅" if cfg.brave_api_key else "❌")
        st.write("🔍 Serper:", "✅" if cfg.serper_api_key else "❌")

        st.markdown("**Other APIs:**")
        st.write("🔴 Reddit:", "✅" if (cfg.reddit_client_id and cfg.reddit_client_secret) else "❌")
        st.write("📹 YouTube:", "✅" if cfg.youtube_api_key else "❌")

        st.divider()
        st.caption("Trust Stack Rating v2.0")
        st.caption("6D Trust Framework")

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
