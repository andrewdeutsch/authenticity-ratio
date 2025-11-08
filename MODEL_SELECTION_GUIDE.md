# LLM Model Selection Guide

This guide explains how to select different OpenAI models for various parts of the Trust Stack analysis pipeline.

## Available Model Parameters

### `--recommendations-model`

Controls which LLM model generates the **Recommendations** section of your Trust Stack report.

**Default**: `gpt-4o-mini`

**Options**:
- `gpt-4o` - Most capable, higher quality, slower, more expensive
- `gpt-4o-mini` - Balanced quality/speed/cost (recommended for most use cases)
- `gpt-3.5-turbo` - Fastest, cheapest, lower quality

**Example Usage**:

```bash
# Use GPT-4o for highest quality recommendations
python scripts/run_pipeline.py \
  --brand-id myBrand \
  --keywords "brand name" \
  --sources reddit brave \
  --recommendations-model gpt-4o

# Use GPT-3.5-turbo for fastest/cheapest recommendations
python scripts/run_pipeline.py \
  --brand-id myBrand \
  --keywords "brand name" \
  --sources reddit brave \
  --recommendations-model gpt-3.5-turbo

# Default (gpt-4o-mini) - no flag needed
python scripts/run_pipeline.py \
  --brand-id myBrand \
  --keywords "brand name" \
  --sources reddit brave
```

### `--llm-model`

Controls which LLM model generates **executive summary examples** (abstractive content summaries).

**Default**: `gpt-3.5-turbo`

**Note**: Only used when `--use-llm-examples` flag is present.

**Example Usage**:

```bash
# Use LLM for executive examples with GPT-4o
python scripts/run_pipeline.py \
  --brand-id myBrand \
  --keywords "brand name" \
  --sources reddit brave \
  --use-llm-examples \
  --llm-model gpt-4o
```

## Combining Multiple Models

You can use different models for different purposes:

```bash
# High-quality recommendations with GPT-4o + fast summaries with GPT-3.5-turbo
python scripts/run_pipeline.py \
  --brand-id myBrand \
  --keywords "brand name" \
  --sources reddit brave \
  --recommendations-model gpt-4o \
  --use-llm-examples \
  --llm-model gpt-3.5-turbo
```

## Model Selection Guide

### When to use `gpt-4o`
- ✅ High-stakes reports requiring maximum quality
- ✅ Complex brand scenarios with nuanced recommendations needed
- ✅ When cost is not a primary concern
- ✅ Final reports for executive leadership

### When to use `gpt-4o-mini` (Default)
- ✅ Most production use cases
- ✅ Balanced quality and cost
- ✅ Good enough for actionable recommendations
- ✅ Regular reporting cadence

### When to use `gpt-3.5-turbo`
- ✅ Development and testing
- ✅ High-volume analysis where cost matters
- ✅ Quick preliminary reports
- ✅ When speed is critical

## Cost Comparison (Approximate)

Based on OpenAI pricing (as of 2024):

| Model | Input Cost | Output Cost | Recommendations Section Cost* |
|-------|-----------|-------------|------------------------------|
| gpt-4o | $2.50/1M tokens | $10.00/1M tokens | ~$0.05-0.15 |
| gpt-4o-mini | $0.15/1M tokens | $0.60/1M tokens | ~$0.003-0.01 |
| gpt-3.5-turbo | $0.50/1M tokens | $1.50/1M tokens | ~$0.01-0.03 |

*Per report, assuming ~2000 token prompt and ~2000 token response

## Quality Differences

### Recommendations Quality Examples

**GPT-4o**:
- Most detailed and contextual
- Better understanding of brand nuances
- More sophisticated strategic recommendations
- Excellent at connecting patterns across dimensions

**GPT-4o-mini** (Recommended):
- High-quality actionable recommendations
- Good contextual understanding
- Appropriate level of detail for most use cases
- Best balance of quality/cost

**GPT-3.5-turbo**:
- Solid basic recommendations
- May miss subtle patterns
- Less detailed strategic guidance
- Still references actual data correctly

## Fallback Behavior

If LLM generation fails (network issues, API errors, missing API key), the system automatically falls back to **enhanced structured recommendations** that still reference your actual data, URLs, and metrics.

## Platform-Aware Recommendations

The LLM recommendation system automatically adjusts its analysis based on the data sources being analyzed:

### Reddit Content
When analyzing Reddit posts and comments, the LLM understands:
- **Pseudonymous users** are normal - won't penalize lack of formal credentials
- **Transparency scores** of 0.50-0.65 may be "good" given platform norms
- **Conversational tone** is expected, not professional brand messaging
- Recommendations focus on **verifiable metadata** (subreddit credibility, post history) rather than impossible improvements

### YouTube Content
When analyzing YouTube videos and comments, the LLM understands:
- **User-generated content** is inherent to the platform
- **Independent creators** are not official brand channels
- **Comment pseudonymity** is platform-standard
- Recommendations focus on **actionable improvements** within platform capabilities

### Why This Matters
Without platform-aware context, the LLM might recommend:
- ❌ "Add formal author credentials to all Reddit posts" (impossible)
- ❌ "Ensure all YouTube commenters use real names" (not feasible)

With platform-aware context, the LLM recommends:
- ✅ "Verify subreddit credibility and moderator policies"
- ✅ "Check YouTube channel verification status and posting history"
- ✅ "Focus on metadata completeness within platform constraints"

## Requirements

- `OPENAI_API_KEY` environment variable must be set
- Model must be available in your OpenAI account
- Sufficient API quota/rate limits

## Troubleshooting

**Error: "OpenAI API key not configured"**
- Set `OPENAI_API_KEY` in your `.env` file or environment

**Error: "Model 'gpt-4o' not found"**
- Verify model name spelling
- Check that your OpenAI account has access to the model

**Slow generation**
- Try a faster model like `gpt-4o-mini` or `gpt-3.5-turbo`
- Check your network connection

**Generic recommendations despite specifying model**
- Check logs for LLM generation errors
- Verify API key is valid and has quota
- System falls back to structured recommendations on any error
