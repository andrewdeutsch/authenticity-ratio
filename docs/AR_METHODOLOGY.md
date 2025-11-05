# Authenticity Ratio™ Methodology

**Version:** 1.0
**Last Updated:** October 2025

---

## Overview

The **Authenticity Ratio (AR)** is a proprietary KPI that quantifies the proportion of authentic versus inauthentic brand-linked content across digital channels. It provides CMOs and boards with a single, actionable metric for brand health—similar to how Net Promoter Score (NPS) measures customer satisfaction.

### Purpose

- **Measure** authentic brand presence across channels
- **Identify** inauthentic or misleading content
- **Track** brand health trends over time
- **Enable** data-driven content strategy decisions

---

## The 5D Trust Dimensions Framework

Content is scored across five trust dimensions. Each dimension receives a score from 0.0 (lowest) to 1.0 (highest).

### 1. Provenance

**Definition:** Origin clarity, traceability, and metadata completeness.

**What it measures:**
- Can we trace where this content came from?
- Is the author/source identifiable?
- Is metadata complete and verifiable?

**Scoring criteria:**
- **0.8-1.0**: Clear origin, verifiable author, complete metadata
- **0.6-0.8**: Good origin info, some metadata present
- **0.4-0.6**: Basic origin info, limited metadata
- **0.2-0.4**: Unclear origin, minimal metadata
- **0.0-0.2**: No clear origin, no verifiable metadata

**Examples:**
- ✅ **High (0.9)**: Official Nike.com product page with full metadata
- ⚠️ **Medium (0.5)**: Reddit post by unverified user
- ❌ **Low (0.2)**: Anonymous forum post with no attribution

---

### 2. Verification

**Definition:** Factual accuracy and consistency with trusted sources.

**What it measures:**
- Are claims factually accurate?
- Can facts be verified against trusted databases?
- Are there inconsistencies or false claims?

**Scoring criteria:**
- **0.8-1.0**: Highly verifiable facts, consistent with known information
- **0.6-0.8**: Mostly accurate, minor inconsistencies
- **0.4-0.6**: Some accurate info, some questionable claims
- **0.2-0.4**: Several inaccuracies or unverifiable claims
- **0.0-0.2**: Major inaccuracies or completely unverifiable

**Examples:**
- ✅ **High (0.9)**: Product details match official specs
- ⚠️ **Medium (0.5)**: User review with subjective opinions
- ❌ **Low (0.2)**: False claims about product features

---

### 3. Transparency

**Definition:** Clear disclosures, honest communication, no hidden agendas.

**What it measures:**
- Are affiliations and sponsorships disclosed?
- Is the intent of the content clear?
- Are there hidden agendas or deceptive practices?

**Scoring criteria:**
- **0.8-1.0**: Clear disclosures, honest communication, transparent intent
- **0.6-0.8**: Mostly transparent, minor omissions
- **0.4-0.6**: Some transparency, some unclear aspects
- **0.2-0.4**: Limited transparency, hidden elements
- **0.0-0.2**: No transparency, deceptive or manipulative

**Examples:**
- ✅ **High (0.9)**: Influencer post with #ad disclosure
- ⚠️ **Medium (0.5)**: Review without affiliate link disclosure
- ❌ **Low (0.2)**: Fake review or undisclosed sponsorship

---

### 4. Coherence

**Definition:** Consistency with brand messaging and professional quality.

**What it measures:**
- Does tone/style align with official brand voice?
- Is messaging consistent across channels?
- Is quality professional and polished?

**Scoring criteria:**
- **0.8-1.0**: Highly coherent, consistent with brand, professional quality
- **0.6-0.8**: Mostly coherent, good consistency
- **0.4-0.6**: Some coherence, minor inconsistencies
- **0.2-0.4**: Limited coherence, noticeable inconsistencies
- **0.0-0.2**: Incoherent, inconsistent, unprofessional

**Examples:**
- ✅ **High (0.9)**: Official Nike campaign content
- ⚠️ **Medium (0.5)**: Fan-created content with brand mentions
- ❌ **Low (0.2)**: Counterfeit product listing with poor quality

---

### 5. Resonance

**Definition:** Cultural fit, authentic engagement, organic appeal.

**What it measures:**
- Does content resonate with target audience?
- Is engagement genuine (not bots/fake)?
- Does it align with brand values?

**Scoring criteria:**
- **0.8-1.0**: High cultural fit, strong organic engagement
- **0.6-0.8**: Good resonance, positive engagement
- **0.4-0.6**: Moderate resonance, mixed engagement
- **0.2-0.4**: Low resonance, limited engagement
- **0.0-0.2**: No resonance, negative or artificial engagement

**Calculation approach:**
- 70% LLM qualitative assessment
- 30% engagement metrics (upvotes, ratings, helpful counts)

**Examples:**
- ✅ **High (0.9)**: Popular authentic user content with high engagement
- ⚠️ **Medium (0.5)**: Standard product mention with moderate engagement
- ❌ **Low (0.2)**: Bot-generated spam with fake engagement

---

## Authenticity Ratio Calculations

### Core AR (Classification-Based)

The primary metric based on content classification.

**Formula:**
```
Core AR = (Authentic Items / Total Items) × 100
```

**Classification thresholds:**
- **Authentic**: Final score ≥ 0.70
- **Suspect**: Final score 0.50-0.69
- **Inauthentic**: Final score < 0.50

**Example:**
- Total items: 47
- Authentic: 32
- Suspect: 10
- Inauthentic: 5
- **Core AR = (32 / 47) × 100 = 68.1%**

---

### Score-Based AR

Alternative metric using mean 5D scores.

**Formula:**
```
Score-Based AR = (Mean of all 5D scores) × 100
```

**5D Score calculation:**
```
5D Score = (Provenance + Verification + Transparency + Coherence + Resonance) / 5
```

**Example:**
- Mean Provenance: 0.65
- Mean Verification: 0.58
- Mean Transparency: 0.62
- Mean Coherence: 0.70
- Mean Resonance: 0.68
- **Mean 5D = 0.646**
- **Score-Based AR = 64.6%**

---

### Extended AR

Weighted blend incorporating rubric adjustments and confidence scores (optional).

**Formula:**
```
Extended AR = (Core AR × 0.7) + (Score-Based AR × 0.3)
```

**Example:**
- Core AR: 68.1%
- Score-Based AR: 64.6%
- **Extended AR = (68.1 × 0.7) + (64.6 × 0.3) = 47.67 + 19.38 = 67.05%**

---

## Data Collection Process

### 1. Source Ingestion

**Supported sources:**
- **Brave Search**: Web content, product pages
- **Reddit**: Posts and discussions
- **YouTube**: Videos and comments
- **Amazon**: Product reviews (planned)
- **Yelp**: Business reviews (planned)

**Collection approach:**
- API-based retrieval using official SDKs
- Rate limiting and quota management
- Configurable per-source item limits

### 2. Normalization

All content is converted to a standardized `NormalizedContent` format:

```python
{
    "content_id": "unique_identifier",
    "src": "brave|reddit|youtube",
    "title": "Content title",
    "body": "Main text content",
    "author": "Author/channel name",
    "event_ts": "ISO timestamp",
    "platform_id": "Source URL/ID",
    "meta": {
        "source_url": "...",
        "rating": 4.5,
        "upvotes": 123,
        # ... additional metadata
    }
}
```

### 3. Enrichment

Content is enriched with:
- Metadata extraction (titles, descriptions, URLs)
- Engagement metrics (ratings, upvotes, view counts)
- Timestamp normalization
- Source attribution

---

## Scoring Process

### 1. Triage (Optional)

Efficiently filter content before expensive LLM scoring:

**Purpose:**
- Reduce API costs
- Focus on substantive content
- Filter obvious spam/low-quality items

**Approach:**
- Score-based preliminary filtering
- Promote items above threshold (default: 0.6)
- Demote items below threshold for exclusion

### 2. 5D Scoring

Each content item is scored on all 5 dimensions using:

**LLM-based scoring:**
- Model: GPT-3.5-turbo (default) or GPT-4
- Structured prompts for each dimension
- Returns score 0.0-1.0
- Fallback: neutral score (0.5) on error

**Engagement-based adjustments (Resonance only):**
- Normalize upvotes, ratings, helpful counts
- Blend with LLM score (70% LLM, 30% engagement)

### 3. Classification

Final classification based on mean 5D score:

```python
if mean_5d_score >= 0.70:
    classification = "Authentic"
elif mean_5d_score >= 0.50:
    classification = "Suspect"
else:
    classification = "Inauthentic"
```

### 4. Quality Assurance

- Verify all items have valid scores
- Check for API errors or timeouts
- Log anomalies for review
- Apply confidence thresholds

---

## Report Generation

### LLM-Enhanced Descriptions

When enabled (`--use-llm-examples`):

**Abstractive summarization:**
- Generate human-readable summaries
- Max 50-120 words per item
- Temperature: 0.3 (consistent output)

**Provenance labeling:**
- All LLM-generated text includes: `(Generated by gpt-3.5-turbo)`
- Format: `"Summary text. (Generated by {model})"`
- Prevents confusion with original content

**Fallback behavior:**
- If LLM fails, use extractive summarization
- First 2 lines or 240 chars from body
- Graceful degradation

### Visualizations

**Charts generated:**
1. **5D Heatmap**: Color-coded dimension scores
2. **AR Trendline**: Historical AR over time
3. **Source Breakdown**: Pie chart of content sources
4. **Content Type Distribution**: Bar chart of content types

### Output Formats

**Markdown report:**
- Executive-friendly layout
- Embedded visualizations
- Full appendix with all items
- Reference link to methodology

**PDF report:**
- Professional formatting
- Charts and tables
- Curated examples (not full appendix)
- Suitable for presentations

---

## Rubric Versioning

### Version 1.0 (Current)

**Key characteristics:**
- 5D Trust Dimensions framework
- Classification thresholds: 0.70 (authentic), 0.50 (suspect)
- Equal weighting across dimensions (0.20 each)
- LLM-based scoring with engagement metrics for Resonance

**Future versions:**
- Adjustable dimension weights per industry
- Custom thresholds per brand
- Enhanced verification against external databases
- Multi-language support

---

## Interpretation Guidelines

### AR Score Ranges

| AR Range | Interpretation | Action Priority |
|----------|----------------|-----------------|
| **80-100%** | Excellent brand authenticity | Monitor and maintain |
| **60-79%** | Good authenticity, room for improvement | Targeted improvements |
| **40-59%** | Moderate concerns, mixed signals | Strategic intervention |
| **20-39%** | Significant authenticity issues | Immediate action required |
| **0-19%** | Critical brand health problems | Crisis response |

### Common Patterns

**High AR (>70%):**
- Strong official presence
- Clear brand voice
- Verified sources dominate
- High transparency and coherence

**Low AR (<50%):**
- Weak official presence
- Third-party content dominates
- Missing disclosures
- Inconsistent messaging

---

## Data Quality & Limitations

### Current Limitations

1. **Sample size**: AR is calculated on collected sample, not exhaustive search
2. **Temporal**: Snapshot in time, not continuous monitoring
3. **LLM bias**: Scoring includes inherent LLM interpretation
4. **Coverage**: Limited to supported sources (Brave, Reddit, YouTube)
5. **Language**: Primarily English content

### Best Practices

- **Run regularly**: Weekly or monthly for trend tracking
- **Consistent parameters**: Use same sources and keywords for comparisons
- **Manual review**: Spot-check classifications for accuracy
- **Context matters**: Consider industry norms and brand maturity

---

## Technical Stack

### Core Technologies

- **Python 3.8+**: Primary language
- **OpenAI API**: LLM scoring (GPT-3.5-turbo, GPT-4)
- **PRAW**: Reddit API wrapper
- **Google API Client**: YouTube Data API
- **Brave Search API**: Web content
- **ReportLab**: PDF generation
- **Matplotlib**: Visualization

### Infrastructure

- **AWS S3**: Data storage (optional)
- **AWS Athena**: Query engine (optional)
- **Local execution**: Standalone mode supported

---

## Glossary

**5D Trust Dimensions**: Framework of five dimensions (Provenance, Verification, Transparency, Coherence, Resonance) used to evaluate content authenticity.

**Authenticity Ratio (AR)**: The percentage of authentic content relative to total analyzed content.

**Classification**: Categorization of content as Authentic, Suspect, or Inauthentic based on 5D scores.

**Content Normalization**: Process of converting diverse source formats into standardized structure.

**Core AR**: Classification-based AR using authentic/suspect/inauthentic counts.

**Extended AR**: Weighted blend of Core AR and Score-Based AR.

**LLM**: Large Language Model (e.g., GPT-3.5-turbo) used for scoring and summarization.

**Provenance Labeling**: Attribution text added to LLM-generated content (e.g., "Generated by gpt-3.5-turbo").

**Score-Based AR**: AR calculated from mean 5D scores across all items.

**Triage**: Preliminary filtering to identify high-value content for detailed scoring.

---

## Version History

### v1.0 (October 2025)
- Initial release
- 5D Trust Dimensions framework
- Multi-source ingestion (Brave, Reddit, YouTube)
- LLM-based scoring with OpenAI
- Markdown and PDF report generation
- LLM provenance labeling

### Planned Enhancements
- Real-time monitoring dashboard
- Custom dimension weights
- Multi-language support
- Enhanced verification integrations (C2PA, FDA, SEC)
- Historical trend analysis
- Competitive benchmarking

---

## Contact & Support

For questions about methodology, custom implementations, or enterprise features:

**Authenticity Ratio Team**
Email: support@authenticityratio.com
Documentation: https://docs.authenticityratio.com

---

*This methodology document is confidential and proprietary. Unauthorized distribution is prohibited.*

**© 2025 Authenticity Ratio. All rights reserved.**
