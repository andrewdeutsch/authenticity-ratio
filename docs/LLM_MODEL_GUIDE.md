# LLM Model Selection Guide

This guide helps you choose the right LLM model for your Trust Stack analysis needs. The system now supports multiple providers with models at different capability and cost levels.

## Quick Reference

| Provider | Model Name | Tier | Best For | Relative Cost |
|----------|-----------|------|----------|---------------|
| **OpenAI** | `gpt-3.5-turbo` | Budget | Simple summaries, high volume | $ |
| **OpenAI** | `gpt-4o-mini` | Mid | Balanced performance | $$ |
| **OpenAI** | `gpt-4o` | Premium | Complex analysis | $$$$ |
| **Claude** | `claude-3-haiku-20240307` | Budget | Fast processing | $$ |
| **Claude** | `claude-3-5-sonnet-20241022` | Premium | Detailed analysis, nuanced writing | $$$$ |
| **Google** | `gemini-1.5-flash` | Budget | Fast, efficient processing | $ |
| **Google** | `gemini-1.5-pro` | Premium | Advanced reasoning | $$$ |
| **DeepSeek** | `deepseek-chat` | Budget | Cost-effective processing | $ |
| **DeepSeek** | `deepseek-reasoner` | Premium | Complex reasoning tasks | $$ |

## Provider Setup

### Environment Variables Required

```bash
# OpenAI (required for default configuration)
OPENAI_API_KEY=sk-...

# Anthropic Claude (optional)
ANTHROPIC_API_KEY=sk-ant-...

# Google Gemini (optional)
GOOGLE_API_KEY=AIza...

# DeepSeek (optional)
DEEPSEEK_API_KEY=sk-...
```

## Detailed Model Profiles

### OpenAI Models

#### `gpt-3.5-turbo` (Current Default)
- **Cost**: Lowest OpenAI cost (~$0.50-$1.50 per 1M tokens)
- **Speed**: Very fast
- **Quality**: Good for straightforward summaries
- **Best for**: High-volume processing, simple executive summaries
- **Limitations**: Less nuanced understanding, may miss subtle context
- **Current use**: Default for executive summaries

#### `gpt-4o-mini`
- **Cost**: Moderate (~$0.15-$0.60 per 1M tokens)
- **Speed**: Fast
- **Quality**: Significantly better than GPT-3.5
- **Best for**: Recommendations, balanced cost/quality
- **Current use**: Default for recommendations generation

#### `gpt-4o`
- **Cost**: Premium (~$2.50-$10 per 1M tokens)
- **Speed**: Moderate
- **Quality**: Highest quality OpenAI model
- **Best for**: Complex analysis requiring deep understanding
- **Use when**: Quality is more important than cost

### Anthropic Claude Models

#### `claude-3-haiku-20240307`
- **Cost**: Low (~$0.25-$1.25 per 1M tokens)
- **Speed**: Very fast (fastest Claude model)
- **Quality**: Good, efficient processing
- **Best for**: Quick summaries, high-throughput scenarios
- **Strengths**: Good instruction following, concise outputs

#### `claude-3-5-sonnet-20241022` ⭐ Recommended for Quality
- **Cost**: Premium (~$3-$15 per 1M tokens)
- **Speed**: Moderate
- **Quality**: Excellent reasoning and writing quality
- **Best for**: Detailed recommendations, nuanced analysis
- **Strengths**:
  - Superior writing quality
  - Better at following complex instructions
  - Excellent at structured output
  - Strong reasoning capabilities
- **Use when**: You want the most actionable and well-written recommendations

### Google Gemini Models

#### `gemini-1.5-flash`
- **Cost**: Very low (~$0.075-$0.30 per 1M tokens)
- **Speed**: Very fast
- **Quality**: Good for basic tasks
- **Best for**: Cost-sensitive, high-volume processing
- **Strengths**: Excellent speed-to-cost ratio

#### `gemini-1.5-pro`
- **Cost**: Moderate (~$1.25-$5 per 1M tokens)
- **Speed**: Moderate
- **Quality**: Advanced reasoning capabilities
- **Best for**: Complex analysis requiring multi-step reasoning
- **Strengths**: Long context window, good at structured reasoning

### DeepSeek Models

#### `deepseek-chat`
- **Cost**: Very low (~$0.14-$0.28 per 1M tokens)
- **Speed**: Fast
- **Quality**: Competitive with GPT-3.5
- **Best for**: Cost-effective alternative to OpenAI
- **Note**: Great for experimentation and high-volume testing

#### `deepseek-reasoner`
- **Cost**: Low (~$0.55-$2.19 per 1M tokens)
- **Speed**: Moderate to slow (shows reasoning process)
- **Quality**: Strong reasoning capabilities
- **Best for**: Tasks requiring step-by-step reasoning
- **Strengths**: Shows chain-of-thought reasoning

## Usage Examples

### Command Line

```bash
# Use Claude Sonnet for high-quality recommendations
python -m scripts.run_pipeline \
  --brand-id nike \
  --keywords "nike shoes" \
  --sources brave \
  --use-llm-examples \
  --llm-model claude-3-5-sonnet-20241022 \
  --recommendations-model claude-3-5-sonnet-20241022

# Use budget-friendly Gemini Flash for summaries
python -m scripts.run_pipeline \
  --brand-id nike \
  --keywords "nike shoes" \
  --sources brave \
  --use-llm-examples \
  --llm-model gemini-1.5-flash \
  --recommendations-model gemini-1.5-pro

# Mix models: fast summaries + quality recommendations
python -m scripts.run_pipeline \
  --brand-id nike \
  --keywords "nike shoes" \
  --sources brave \
  --use-llm-examples \
  --llm-model gpt-3.5-turbo \
  --recommendations-model claude-3-5-sonnet-20241022

# Cost-effective DeepSeek option
python -m scripts.run_pipeline \
  --brand-id nike \
  --keywords "nike shoes" \
  --sources brave \
  --use-llm-examples \
  --llm-model deepseek-chat \
  --recommendations-model deepseek-reasoner
```

## Recommended Configurations

### Development & Testing
```bash
--llm-model gemini-1.5-flash
--recommendations-model deepseek-chat
```
**Why**: Minimize costs while developing

### Production (Balanced)
```bash
--llm-model gpt-4o-mini
--recommendations-model gpt-4o-mini
```
**Why**: Good quality-to-cost ratio for most use cases

### Production (Premium Quality) ⭐
```bash
--llm-model claude-3-5-sonnet-20241022
--recommendations-model claude-3-5-sonnet-20241022
```
**Why**: Best output quality for client-facing reports

### High Volume Processing
```bash
--llm-model gemini-1.5-flash
--recommendations-model gemini-1.5-pro
```
**Why**: Fastest processing with good quality

### Cost-Conscious
```bash
--llm-model deepseek-chat
--recommendations-model deepseek-reasoner
```
**Why**: Lowest overall cost

## Model Selection Decision Tree

```
Do you need the absolute best quality?
├─ YES → claude-3-5-sonnet-20241022
└─ NO ↓

Is cost a primary concern?
├─ YES → gemini-1.5-flash or deepseek-chat
└─ NO ↓

Processing high volume?
├─ YES → gemini-1.5-flash or claude-3-haiku-20240307
└─ NO ↓

Default choice → gpt-4o-mini (balanced)
```

## Installation Requirements

### Install Provider SDKs

```bash
# OpenAI (required)
pip install openai

# Anthropic Claude (optional)
pip install anthropic

# Google Gemini (optional)
pip install google-generativeai

# DeepSeek uses OpenAI-compatible API (no additional install needed)
```

### Update .env File

```bash
# Copy the template
cp .env.example .env

# Add your API keys
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=AIza...
DEEPSEEK_API_KEY=sk-...
```

## Testing Different Models

To compare outputs across different models, run the same analysis with different model configurations:

```bash
# Test 1: GPT-3.5 (current default)
python -m scripts.run_pipeline \
  --brand-id test-brand \
  --keywords "test" \
  --sources brave \
  --brave-pages 5 \
  --use-llm-examples \
  --llm-model gpt-3.5-turbo \
  --recommendations-model gpt-4o-mini \
  --output-dir ./output/test_gpt35

# Test 2: Claude Sonnet (premium)
python -m scripts.run_pipeline \
  --brand-id test-brand \
  --keywords "test" \
  --sources brave \
  --brave-pages 5 \
  --use-llm-examples \
  --llm-model claude-3-5-sonnet-20241022 \
  --recommendations-model claude-3-5-sonnet-20241022 \
  --output-dir ./output/test_claude

# Test 3: Gemini (cost-effective)
python -m scripts.run_pipeline \
  --brand-id test-brand \
  --keywords "test" \
  --sources brave \
  --brave-pages 5 \
  --use-llm-examples \
  --llm-model gemini-1.5-flash \
  --recommendations-model gemini-1.5-pro \
  --output-dir ./output/test_gemini
```

Then compare the generated reports to see which model provides the best output for your needs.

## Troubleshooting

### Model Not Working

1. **Check API Key**: Ensure the correct environment variable is set
   ```bash
   echo $ANTHROPIC_API_KEY
   ```

2. **Install SDK**: Make sure the provider SDK is installed
   ```bash
   pip install anthropic google-generativeai
   ```

3. **Check Logs**: Review the output for provider-specific errors
   ```bash
   tail -f output/logs/ar_pipeline_*.log
   ```

### Rate Limits

Each provider has different rate limits:
- **OpenAI**: Tier-based (check your account tier)
- **Claude**: Typically 50 requests/minute
- **Google**: Generous free tier, then pay-as-you-go
- **DeepSeek**: Check documentation for current limits

If you hit rate limits, consider:
- Using a lower-tier model with higher rate limits
- Reducing `--max-items` or `--brave-pages`
- Implementing retry logic (built into the client)

## Future Enhancements

Planned improvements:
- Automatic model fallback if primary fails
- Cost tracking per analysis run
- Model performance benchmarking
- A/B testing framework for comparing outputs
- Web UI for model selection

## Support

For issues or questions:
1. Check the logs in `output/logs/`
2. Verify API keys are properly set
3. Review provider-specific documentation
4. File an issue with model name and error message
