# Web Scraping Improvements

This document describes the improvements made to the web scraping system for legitimate, authorized scraping scenarios.

## Overview

The scraping system has been enhanced with:
1. **Domain-specific configurations** - Different strategies for different types of sites
2. **Realistic browser headers** - Full header sets that mimic real browsers
3. **Session management** - Connection pooling and automatic cookie handling
4. **Randomized delays** - Variable timing to avoid detection
5. **Smart retry logic** - Adaptive backoff based on response codes
6. **Automatic Playwright usage** - JavaScript rendering for enterprise sites

## Domain-Specific Configuration

### Pre-configured Domains

The following enterprise domains are automatically configured to use Playwright and longer delays:

- `mastercard.com`
- `visa.com`
- `americanexpress.com`
- `discover.com`
- `chase.com`
- `bankofamerica.com`

### Adding New Domain Configurations

To add a new domain configuration, edit `ingestion/fetch_config.py`:

```python
DOMAIN_CONFIGS = {
    "example.com": {
        "use_playwright": True,        # Use browser automation
        "min_delay": 2.0,              # Minimum delay between requests
        "max_delay": 4.0,              # Maximum delay between requests
        "timeout": 15,                 # Request timeout in seconds
        "max_retries": 3,              # Number of retry attempts
    },
}
```

## Environment Variables

### New Variables

- `AR_RANDOMIZE_DELAYS` - Enable randomized delays (default: `1`)
- `AR_USER_AGENT` - User agent to use (now automatically uses realistic UAs if not set)
- `AR_USE_PLAYWRIGHT` - Global override to enable Playwright for all domains (default: `0`)

### Existing Variables (still supported)

- `AR_FETCH_RETRIES` - Number of retry attempts (default: `3`)
- `AR_FETCH_BACKOFF` - Base backoff delay in seconds (default: `0.6`)
- `BRAVE_REQUEST_INTERVAL` - Rate limit interval (default: `1.2`)

## How It Works

### 1. Realistic Browser Headers

Every request now includes a full set of browser headers:

```
User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) ...
Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8
Accept-Language: en-US,en;q=0.9
Accept-Encoding: gzip, deflate, br
Connection: keep-alive
Upgrade-Insecure-Requests: 1
Sec-Fetch-Dest: document
Sec-Fetch-Mode: navigate
Sec-Fetch-Site: none
Sec-Fetch-User: ?1
Cache-Control: max-age=0
DNT: 1
```

User agents are randomly selected from a pool of realistic browser UAs to avoid fingerprinting.

### 2. Session Management

The system now maintains persistent sessions per domain:

- **Connection pooling** - Reuses TCP connections for better performance
- **Automatic cookie handling** - Maintains cookies across requests to the same domain
- **Thread-safe** - Safe to use in multi-threaded environments

### 3. Randomized Delays

Instead of fixed delays, the system now uses randomized delays:

- **Default**: 1.0-2.5 seconds
- **Enterprise domains**: 2.0-4.0 seconds
- **Configurable per domain** via `DOMAIN_CONFIGS`

This makes request patterns less predictable and more natural.

### 4. Smart Retry Logic

The retry system now adapts based on response codes:

- **403 Forbidden** - Backs off 3x longer (likely bot detection)
- **429 Rate Limited** - Backs off 5x longer (respects rate limits)
- **5xx Server Errors** - Backs off 2x longer (server issues)
- **Other failures** - Normal exponential backoff

### 5. Automatic Playwright Usage

For enterprise domains (like `mastercard.com`), the system automatically uses Playwright (headless Chrome) when:

- The initial request fails (non-200 status)
- The content is thin (< 200 characters)
- The domain is configured with `use_playwright: True`

This enables:
- **JavaScript rendering** - Full page execution
- **Browser fingerprinting** - More realistic browser profile
- **Cookie/session handling** - Full browser session simulation

## Usage Examples

### Basic Usage

No changes needed! The improvements are automatic:

```python
from ingestion.brave_search import fetch_page

# Automatically uses realistic headers, sessions, and delays
result = fetch_page("https://mastercard.com")
```

### Custom Domain Configuration

For a new domain that needs special handling:

```python
# Edit ingestion/fetch_config.py
DOMAIN_CONFIGS = {
    "mycompany.com": {
        "use_playwright": True,
        "min_delay": 3.0,
        "max_delay": 5.0,
        "timeout": 20,
        "max_retries": 5,
    },
}
```

### Force Playwright for All Domains

```bash
export AR_USE_PLAYWRIGHT=1
```

### Disable Randomization

```bash
export AR_RANDOMIZE_DELAYS=0
```

## Best Practices

1. **Respect robots.txt** - The system already does this automatically
2. **Use appropriate delays** - Default delays are conservative; adjust if needed
3. **Configure per-domain** - Add frequently-blocked domains to `DOMAIN_CONFIGS`
4. **Monitor success rates** - Check logs for 403/429 responses
5. **Contact sites directly** - For high-volume scraping, consider official APIs

## Troubleshooting

### Still Getting Blocked?

1. **Check if Playwright is installed**: `pip install playwright && playwright install chromium`
2. **Enable Playwright for the domain**: Add it to `DOMAIN_CONFIGS` with `use_playwright: True`
3. **Increase delays**: Set higher `min_delay` and `max_delay` for the domain
4. **Check logs**: Look for patterns in blocked requests

### Slow Performance?

1. **Disable Playwright** if not needed: Set `use_playwright: False` for the domain
2. **Reduce delays**: Lower `min_delay` and `max_delay` (but respect rate limits!)
3. **Check timeout values**: Reduce `timeout` if sites are slow but reliable

### Session Issues?

Sessions are maintained per domain automatically. If you need to clear sessions (e.g., to reset cookies), restart the application.

## Technical Details

### Files Modified

- `ingestion/fetch_config.py` - **NEW** - Domain configuration system
- `ingestion/brave_search.py` - Updated fetch logic with new features
- `webapp/app.py` - Updated webapp fetch functions

### Key Functions

- `get_domain_config(url)` - Returns configuration for a URL's domain
- `get_realistic_headers(url)` - Returns full browser header set
- `get_random_delay(url)` - Returns randomized delay for domain
- `should_use_playwright(url)` - Checks if Playwright should be used
- `get_retry_config(url, status_code)` - Returns adaptive retry settings

## Future Improvements

Potential enhancements for the future:

1. **Proxy rotation** - Distribute requests across multiple IPs
2. **TLS fingerprinting evasion** - Use `curl_cffi` for better mimicry
3. **Adaptive rate limiting** - Learn optimal rates per domain
4. **Request monitoring** - Track success rates and adjust strategies
5. **Playwright stealth mode** - Additional anti-detection measures
