"""
Simple Reddit API connectivity test for the AR project.
This script uses config.settings.APIConfig (which loads .env) to build a PRAW Reddit client
and attempts to fetch one "hot" post from r/all. It prints a short success message or an error.

Run with: ./.venv/bin/python scripts/test_reddit.py
"""
import sys
import os
import traceback

# Ensure project root is on sys.path so config imports work when running this script
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import APIConfig

def main() -> int:
    try:
        import praw
    except Exception:
        print("ERROR: PRAW not installed in the active environment.")
        return 2

    cfg = APIConfig()

    if not cfg.reddit_client_id or not cfg.reddit_client_secret:
        print("MISSING: Reddit client_id or client_secret not provided in environment.")
        return 3

    try:
        reddit = praw.Reddit(
            client_id=cfg.reddit_client_id,
            client_secret=cfg.reddit_client_secret,
            user_agent=cfg.reddit_user_agent
        )

        # Try a simple read-only call
        subreddit = reddit.subreddit('all')
        post = next(subreddit.hot(limit=1))
        print(f"OK: fetched post id={post.id!s} title={post.title!s}")
        return 0

    except Exception:
        print("ERROR: Exception while connecting to Reddit API:")
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
