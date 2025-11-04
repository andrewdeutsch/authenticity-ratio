"""
Reddit data crawler for AR tool
Collects brand-related content from Reddit
"""

import praw
import time
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
from dataclasses import dataclass

from config.settings import SETTINGS, APIConfig
from data.models import NormalizedContent

logger = logging.getLogger(__name__)

@dataclass
class RedditPost:
    """Reddit post data structure"""
    id: str
    title: str
    selftext: str
    author: str
    score: int
    upvote_ratio: float
    num_comments: int
    created_utc: float
    subreddit: str
    url: str  # URL that the post links to (if link post)
    permalink: str  # Permalink to the Reddit post itself
    is_self: bool

class RedditCrawler:
    """Crawler for Reddit content"""
    
    def __init__(self):
        self.reddit = praw.Reddit(
            client_id=APIConfig.reddit_client_id,
            client_secret=APIConfig.reddit_client_secret,
            user_agent=APIConfig.reddit_user_agent
        )
        self.rate_limit = SETTINGS['reddit_rate_limit']
        self.last_request_time = 0
    
    def _rate_limit_check(self):
        """Enforce rate limiting"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        min_interval = 60 / self.rate_limit  # Convert to seconds
        
        if time_since_last < min_interval:
            sleep_time = min_interval - time_since_last
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def search_posts(self, keywords: List[str], subreddits: List[str] = None, 
                    limit: int = 100, time_filter: str = "week") -> List[RedditPost]:
        """
        Search for posts containing brand keywords
        
        Args:
            keywords: List of brand-related keywords
            subreddits: List of subreddit names to search (None for all)
            limit: Maximum number of posts to return
            time_filter: Time period ("day", "week", "month", "year", "all")
        """
        posts = []
        search_query = " OR ".join(keywords)
        
        try:
            self._rate_limit_check()
            
            # Search in specific subreddits or all
            if subreddits:
                for subreddit_name in subreddits:
                    subreddit = self.reddit.subreddit(subreddit_name)
                    search_results = subreddit.search(
                        search_query, 
                        time_filter=time_filter, 
                        limit=limit // len(subreddits)
                    )
                    
                    for submission in search_results:
                        posts.append(self._parse_submission(submission))
            else:
                # Search across all of Reddit
                search_results = self.reddit.subreddit("all").search(
                    search_query, 
                    time_filter=time_filter, 
                    limit=limit
                )
                
                for submission in search_results:
                    posts.append(self._parse_submission(submission))
            
            logger.info(f"Found {len(posts)} Reddit posts for keywords: {keywords}")
            
        except Exception as e:
            logger.error(f"Error searching Reddit: {e}")
            raise
        
        return posts
    
    def get_subreddit_posts(self, subreddit_name: str, sort: str = "hot", 
                          limit: int = 100, time_filter: str = "week") -> List[RedditPost]:
        """
        Get posts from a specific subreddit
        
        Args:
            subreddit_name: Name of the subreddit
            sort: Sort method ("hot", "new", "top", "rising")
            limit: Maximum number of posts
            time_filter: Time period for "top" sort
        """
        posts = []
        
        try:
            self._rate_limit_check()
            subreddit = self.reddit.subreddit(subreddit_name)
            
            if sort == "hot":
                submissions = subreddit.hot(limit=limit)
            elif sort == "new":
                submissions = subreddit.new(limit=limit)
            elif sort == "top":
                submissions = subreddit.top(time_filter=time_filter, limit=limit)
            elif sort == "rising":
                submissions = subreddit.rising(limit=limit)
            else:
                raise ValueError(f"Invalid sort method: {sort}")
            
            for submission in submissions:
                posts.append(self._parse_submission(submission))
            
            logger.info(f"Retrieved {len(posts)} posts from r/{subreddit_name}")
            
        except Exception as e:
            logger.error(f"Error getting posts from r/{subreddit_name}: {e}")
            raise
        
        return posts
    
    def _parse_submission(self, submission) -> RedditPost:
        """Parse Reddit submission into RedditPost object"""
        return RedditPost(
            id=submission.id,
            title=submission.title,
            selftext=submission.selftext or "",
            author=str(submission.author) if submission.author else "[deleted]",
            score=submission.score,
            upvote_ratio=submission.upvote_ratio,
            num_comments=submission.num_comments,
            created_utc=submission.created_utc,
            subreddit=str(submission.subreddit),
            url=submission.url,  # URL that post links to
            permalink=submission.permalink,  # Reddit post permalink
            is_self=submission.is_self
        )
    
    def filter_by_brand_keywords(self, posts: List[RedditPost], 
                               brand_keywords: List[str]) -> List[RedditPost]:
        """Filter posts that contain brand keywords"""
        filtered_posts = []
        keywords_lower = [kw.lower() for kw in brand_keywords]
        
        for post in posts:
            # Check title and content for keywords
            text_to_check = f"{post.title} {post.selftext}".lower()
            
            if any(keyword in text_to_check for keyword in keywords_lower):
                filtered_posts.append(post)
        
        logger.info(f"Filtered {len(posts)} posts down to {len(filtered_posts)} with brand keywords")
        return filtered_posts
    
    def convert_to_normalized_content(self, posts: List[RedditPost],
                                    brand_id: str, run_id: str) -> List[NormalizedContent]:
        """Convert Reddit posts to NormalizedContent objects"""
        normalized_content = []

        for post in posts:
            # Create content ID
            content_id = f"reddit_{post.id}"

            # Format timestamp
            event_ts = datetime.fromtimestamp(post.created_utc).isoformat()

            # Construct full Reddit post URL from permalink
            reddit_post_url = f"https://www.reddit.com{post.permalink}"

            # Prepare metadata
            meta = {
                "subreddit": post.subreddit,
                "source_url": reddit_post_url,  # Permalink to Reddit post
                "url": reddit_post_url,  # Also add as 'url' for compatibility
                "linked_url": post.url,  # URL that the post links to (if link post)
                "is_self": str(post.is_self),
                "upvote_ratio": str(post.upvote_ratio),
                "num_comments": str(post.num_comments),
                "title": post.title  # Explicitly include title in metadata
            }

            normalized_content.append(NormalizedContent(
                content_id=content_id,
                src="reddit",
                platform_id=post.id,
                author=post.author,
                title=post.title,
                body=post.selftext,
                rating=post.upvote_ratio,
                upvotes=post.score,
                helpful_count=None,  # Not applicable for Reddit
                event_ts=event_ts,
                run_id=run_id,
                meta={**meta, 'content_type': ('text' if post.selftext else ('link' if post.url else 'title'))}
            ))

        return normalized_content
