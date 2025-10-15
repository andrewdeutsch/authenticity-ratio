"""Quick debug helper: run `search_brave()` and dump results + HTML snippet to disk.

Usage:
    python scripts/debug_brave.py --query nike --size 4 --out /tmp/brave_debug.html

This helps you see the raw HTML Brave returns and the parsed link targets.
"""
import argparse
import logging
import os
import sys

# Ensure project root is on PYTHONPATH when running this script directly
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ingestion import brave_search

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--query', required=True)
    p.add_argument('--size', type=int, default=4)
    p.add_argument('--out', default='/tmp/brave_snippet.html')
    args = p.parse_args()

    results = brave_search.search_brave(args.query, size=args.size)
    print(f"Parsed {len(results)} results:\n")
    for i, r in enumerate(results):
        print(i, r.get('title'), r.get('url'))

    # Also fetch the full HTML for inspection (best-effort)
    import requests
    try:
        resp = requests.get('https://search.brave.com/search', params={'q': args.query, 'source': 'web', 'count': args.size}, timeout=15)
        snippet = resp.text[:4000]
        with open(args.out, 'w', encoding='utf-8') as f:
            f.write(snippet)
        print(f"Wrote HTML snippet to: {args.out}")
    except Exception as e:
        logger.error('Failed to fetch Brave HTML: %s', e)


if __name__ == '__main__':
    main()
