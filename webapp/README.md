# Authenticity Ratio™ Web Application

A comprehensive web interface for analyzing and visualizing brand content authenticity across digital channels.

## Features

### 🏠 Home Page
- **Overview** of Authenticity Ratio concept and formulas
- **6D Trust Dimensions** explanation
- **Pipeline visualization** showing the analysis workflow
- Quick start guide

### 🚀 Analysis Page
- **Configure brand analysis** with custom parameters:
  - Brand ID and search keywords
  - Maximum items to analyze
  - Data source selection (Brave, Reddit, YouTube)
- **Real-time progress tracking** during pipeline execution
- **Automatic report generation** (PDF and Markdown)

### 📊 Results Page
- **Key Metrics Dashboard**:
  - Authenticity Ratio percentage
  - Total content analyzed
  - Authentic vs. Inauthentic counts
- **Rich Visualizations**:
  - Pie chart showing content classification distribution
  - Bar chart comparing Core AR vs. Extended AR
  - Radar chart displaying 6D Trust Dimensions scores
  - Progress bars for individual dimension performance
- **Detailed Content Analysis**:
  - Sortable table of all analyzed content items
  - Color-coded classification (Authentic, Suspect, Inauthentic)
  - Expandable detailed breakdown with per-dimension scores
- **Export Capabilities**:
  - Download PDF report
  - Download Markdown report
  - Export raw data as JSON

### 📚 History Page
- View all past analysis runs
- Quick access to historical results
- Compare performance across different runs

## Getting Started

### Prerequisites

1. **Python 3.8+** with required packages:
   ```bash
   pip install streamlit plotly pandas
   ```

2. **API Credentials** (optional, depending on data sources):
   - `BRAVE_API_KEY` - For Brave Search (optional, falls back to HTML scraping)
   - `REDDIT_CLIENT_ID` and `REDDIT_CLIENT_SECRET` - For Reddit ingestion
   - `YOUTUBE_API_KEY` - For YouTube ingestion

### Running the Application

1. **Navigate to the project root**:
   ```bash
   cd /path/to/authenticity-ratio
   ```

2. **Launch the Streamlit app**:
   ```bash
   streamlit run webapp/app.py
   ```

3. **Access the application**:
   - Open your browser to `http://localhost:8501`
   - The app will automatically open in your default browser

## Usage Guide

### Running Your First Analysis

1. **Navigate to "Run Analysis"** page using the sidebar
2. **Configure your analysis**:
   - Enter a Brand ID (e.g., "nike")
   - Specify search keywords (space-separated)
   - Set maximum items to analyze (5-100)
   - Select data sources (at least one required)
3. **Click "Run Analysis"**
4. **Monitor progress** via the progress bar
5. **View results** automatically when analysis completes

### Understanding Results

#### Authenticity Ratio (AR)
- **80-100%**: 🟢 Excellent - High content authenticity
- **60-79%**: 🟡 Good - Solid performance with room for improvement
- **40-59%**: 🟠 Moderate - Requires attention and action
- **0-39%**: 🔴 Poor - Immediate action needed

#### 6D Trust Dimensions
Each content item is scored on six dimensions (0-1 scale):
- **Provenance** (🔗): Origin, traceability, metadata integrity
- **Verification** (✓): Factual accuracy vs. trusted databases
- **Transparency** (👁): Disclosures, clarity, attribution
- **Coherence** (🔄): Consistency across channels and time
- **Resonance** (📢): Cultural fit, organic engagement
- **AI Readiness** (🤖): Machine discoverability, LLM-readable signals

#### Content Classification
- **Authentic**: High-quality, verified content (Score ≥ 75)
- **Suspect**: Uncertain content requiring review (40 ≤ Score < 75)
- **Inauthentic**: Low-quality or misleading content (Score < 40)

### Exporting Reports

From the Results page, you can export analysis in three formats:

1. **PDF Report**: Professional report with charts and tables
2. **Markdown Report**: Text-based report for documentation
3. **JSON Data**: Raw data for custom analysis or integration

## Data Sources

### 🌐 Brave Search (Web)
- **Always available** (no API key required for basic functionality)
- Searches public web content
- Extracts metadata including title, body, and footer links

### 🔴 Reddit
- **Requires API credentials**
- Searches posts and comments
- Analyzes engagement metrics (upvotes, comments)

### 📹 YouTube
- **Requires API key**
- Searches video content
- Optional: Include video comments in analysis

## Output Directory

Analysis results are saved to:
```
output/webapp_runs/{brand_id}_{run_id}/
├── _run_data.json           # Run metadata and results
├── ar_report_{brand}_{id}.pdf   # PDF report
└── ar_report_{brand}_{id}.md    # Markdown report
```

## Troubleshooting

### "No content collected from any source"
- **Cause**: Search returned no results or all fetches failed
- **Solution**: Try different keywords or check API credentials

### "Missing API credentials for selected sources"
- **Cause**: Data source selected but API keys not configured
- **Solution**: Set environment variables or unselect that source

### Analysis takes a long time
- **Cause**: Large number of items or slow API responses
- **Solution**: Reduce max items or focus on fewer data sources

### Visualizations not displaying
- **Cause**: Missing plotly or pandas libraries
- **Solution**: Run `pip install plotly pandas`

## Architecture

The web app integrates with the following pipeline components:

1. **Ingestion** (`ingestion/`): Collects content from various sources
2. **Normalization** (`ingestion/normalizer.py`): Standardizes content format
3. **Scoring** (`scoring/pipeline.py`): Applies 6D rubric and classifies content
4. **Reporting** (`reporting/`): Generates PDF and Markdown reports

## Performance Tips

- Start with **10-20 items** for faster initial runs
- Use **Brave only** for quickest results (no API rate limits)
- Enable **Reddit/YouTube** when you need comprehensive coverage
- View **History** to compare results across multiple runs

## API Status Indicator

The sidebar shows real-time status of available data sources:
- ✅ Available (API credentials configured)
- ❌ Unavailable (missing credentials)

## Advanced Features

### Custom Analysis Parameters
Modify the following in the UI:
- **Max Items**: Control analysis scope (5-100 items)
- **Brave Pages**: Number of web pages to fetch (1-20)
- **Include Comments**: Whether to analyze YouTube comments

### Detailed Breakdown
Expand the "View Detailed Breakdown" section to see:
- Per-item dimension scores
- Applied scoring rules and bonuses
- Source metadata (URL, title, description)
- Final scores and classifications

## Support

For issues, questions, or feature requests, refer to the main project README or documentation in `docs/`.

---

**Authenticity Ratio™ v2.0** | Trust Stack Framework
