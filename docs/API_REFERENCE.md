# API Reference

## Overview

The Authenticity Ratio (AR) tool provides APIs for content ingestion, scoring, and reporting. This document outlines the available endpoints and usage patterns.

## Database Schema

### Tables

#### ar_content_normalized_v2
Stores ingested and normalized content from various sources.

| Column | Type | Description |
|--------|------|-------------|
| content_id | string | Unique identifier for content |
| src | string | Source platform (reddit, amazon) |
| platform_id | string | Original platform ID |
| author | string | Content author |
| title | string | Content title |
| body | string | Content body text |
| rating | double | Content rating/score |
| upvotes | int | Number of upvotes |
| helpful_count | double | Helpful votes (Amazon) |
| event_ts | string | Event timestamp |
| run_id | string | Pipeline run identifier |
| meta | map<string,string> | Additional metadata |

#### ar_content_scores_v2
Stores 5D Trust Dimension scores and classifications.

| Column | Type | Description |
|--------|------|-------------|
| content_id | string | Unique identifier for content |
| brand | string | Brand name |
| src | string | Source platform |
| event_ts | string | Event timestamp |
| score_provenance | double | Provenance dimension score |
| score_resonance | double | Resonance dimension score |
| score_coherence | double | Coherence dimension score |
| score_transparency | double | Transparency dimension score |
| score_verification | double | Verification dimension score |
| class_label | string | Classification (authentic/suspect/inauthentic) |
| is_authentic | boolean | Authentic classification |
| rubric_version | string | Scoring rubric version |
| run_id | string | Pipeline run identifier |
| meta | string | Additional metadata (JSON) |

## Key Queries

### Calculate Authenticity Ratio
```sql
SELECT
    n.brand_id, n.source, n.run_id,
    COUNT(*) AS total_items,
    SUM(CASE WHEN s.is_authentic THEN 1 ELSE 0 END) AS authentic_items,
    SUM(CASE WHEN s.class_label = 'suspect' THEN 1 ELSE 0 END) AS suspect_items,
    SUM(CASE WHEN s.class_label = 'inauthentic' THEN 1 ELSE 0 END) AS inauthentic_items,
    100.0 * SUM(CASE WHEN s.is_authentic THEN 1 ELSE 0 END) / COUNT(*) AS authenticity_ratio_pct
FROM ar_mvp.v_content_normalized n
JOIN ar_mvp.ar_content_scores_v2 s
    ON n.content_id = s.content_id
   AND n.brand_id = s.brand_id
   AND n.source = s.source
   AND n.run_id = s.run_id
WHERE n.brand_id = 'brandX' 
  AND n.run_id = 'runY'
  AND n.source IN ('reddit','amazon')
GROUP BY n.brand_id, n.source, n.run_id
ORDER BY n.run_id DESC;
```

### Get Dimension Scores
```sql
SELECT
    content_id,
    score_provenance,
    score_resonance,
    score_coherence,
    score_transparency,
    score_verification,
    class_label,
    is_authentic
FROM ar_mvp.ar_content_scores_v2
WHERE brand_id = 'brandX'
  AND run_id = 'runY'
ORDER BY score_provenance + score_resonance + score_coherence + score_transparency + score_verification DESC;
```

## Python API

### Data Models

#### NormalizedContent
```python
from data.models import NormalizedContent

content = NormalizedContent(
    content_id="reddit_123",
    src="reddit",
    platform_id="abc123",
    author="username",
    title="Post Title",
    body="Post content...",
    rating=0.85,
    upvotes=42,
    event_ts="2024-01-01T12:00:00",
    run_id="run_123"
)
```

#### ContentScores
```python
from data.models import ContentScores

scores = ContentScores(
    content_id="reddit_123",
    brand="Example Brand",
    src="reddit",
    event_ts="2024-01-01T12:00:00",
    score_provenance=0.8,
    score_resonance=0.7,
    score_coherence=0.9,
    score_transparency=0.6,
    score_verification=0.75,
    class_label="authentic",
    is_authentic=True,
    rubric_version="v1.0",
    run_id="run_123"
)
```

### Athena Client

#### Upload Content
```python
from data.athena_client import AthenaClient

client = AthenaClient()
client.upload_normalized_content(content_list, brand_id, source, run_id)
```

#### Calculate AR
```python
ar_result = client.calculate_authenticity_ratio(brand_id, run_id, sources=['reddit', 'amazon'])
print(f"Authenticity Ratio: {ar_result.authenticity_ratio_pct:.1f}%")
```

### Ingestion

#### Reddit Crawler
```python
from ingestion.reddit_crawler import RedditCrawler

crawler = RedditCrawler()
posts = crawler.search_posts(keywords=["brand", "product"], limit=100)
content = crawler.convert_to_normalized_content(posts, brand_id, run_id)
```

#### Amazon Scraper
```python
from ingestion.amazon_scraper import AmazonScraper

scraper = AmazonScraper()
reviews = scraper.mock_reviews_for_demo(keywords=["brand"], num_reviews=50)
content = scraper.convert_to_normalized_content(reviews, brand_id, run_id)
```

### Scoring

#### Content Scorer
```python
from scoring.scorer import ContentScorer

scorer = ContentScorer()
dimension_scores = scorer.score_content(content, brand_context)
scores_list = scorer.batch_score_content(content_list, brand_context)
```

#### Content Classifier
```python
from scoring.classifier import ContentClassifier

classifier = ContentClassifier()
classified_scores = classifier.classify_content(scores)
confidence = classifier.get_classification_confidence(scores)
```

### Reporting

#### PDF Generator
```python
from reporting.pdf_generator import PDFReportGenerator

generator = PDFReportGenerator()
pdf_path = generator.generate_report(report_data, "output/report.pdf")
```

#### Markdown Generator
```python
from reporting.markdown_generator import MarkdownReportGenerator

generator = MarkdownReportGenerator()
md_path = generator.generate_report(report_data, "output/report.md")
```

## Configuration

### Environment Variables
```bash
# AWS
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret

# APIs
REDDIT_CLIENT_ID=your_reddit_id
REDDIT_CLIENT_SECRET=your_reddit_secret
OPENAI_API_KEY=your_openai_key
```

### Settings
```python
from config.settings import SETTINGS

# Modify scoring weights
SETTINGS['scoring_weights'].provenance = 0.25
SETTINGS['scoring_weights'].verification = 0.25
SETTINGS['scoring_weights'].transparency = 0.20
SETTINGS['scoring_weights'].coherence = 0.15
SETTINGS['scoring_weights'].resonance = 0.15
```

## Error Handling

### Common Exceptions
- `AthenaQueryError`: Database query failures
- `APIError`: External API failures
- `ValidationError`: Configuration or data validation errors
- `ScoringError`: Content scoring failures

### Retry Logic
```python
from utils.helpers import retry_on_failure

@retry_on_failure(max_retries=3, delay=1.0)
def api_call():
    # API call that might fail
    pass
```

## Rate Limiting

### API Limits
- Reddit: 60 requests per minute
- Amazon: 1 request per second
- OpenAI: 60 requests per minute

### Best Practices
- Use batch processing for large datasets
- Implement exponential backoff for retries
- Cache results when possible
- Monitor API usage quotas

## Security

### Data Protection
- All sensitive data encrypted at rest
- API keys stored in environment variables
- Content deduplication to prevent data leakage
- Audit logging for all operations

### Access Control
- IAM roles for AWS services
- API key rotation
- Network security groups
- VPC isolation for sensitive operations
