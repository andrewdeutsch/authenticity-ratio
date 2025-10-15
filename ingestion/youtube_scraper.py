"""
YouTube data scraper for AR tool
Uses YouTube Data API v3 (API key) to search videos and fetch comments.
Converts results to NormalizedContent objects compatible with ar_content_normalized_v2
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import logging
import time

from googleapiclient.discovery import build

from config.settings import APIConfig, SETTINGS
from data.models import NormalizedContent
from utils.helpers import format_timestamp

logger = logging.getLogger(__name__)


@dataclass
class YouTubeVideo:
    video_id: str
    title: str
    description: str
    channel_title: str
    publish_time: str
    view_count: Optional[int] = None
    like_count: Optional[int] = None
    comment_count: Optional[int] = None


class YouTubeScraper:
    """Simple YouTube Data API v3 wrapper for searching videos and fetching comments."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or APIConfig.youtube_api_key
        if not self.api_key:
            raise ValueError("YouTube API key not configured. Set YOUTUBE_API_KEY in environment.")

        self.service = build('youtube', 'v3', developerKey=self.api_key)
        self.rate_limit = SETTINGS.get('youtube_rate_limit', 60)  # requests per minute
        self.last_request_time = 0.0

    def _rate_limit_check(self):
        current_time = time.time()
        min_interval = 60.0 / float(self.rate_limit) if self.rate_limit > 0 else 0
        time_since_last = current_time - self.last_request_time
        if time_since_last < min_interval:
            time.sleep(min_interval - time_since_last)
        self.last_request_time = time.time()

    def search_videos(self, query: str, max_results: int = 25, published_after: Optional[str] = None) -> List[YouTubeVideo]:
        """Search for videos by query string.

        Args:
            query: Search query (brand keywords etc.)
            max_results: Max number of videos to return (<=50 per API limits)
            published_after: ISO timestamp to filter videos (e.g., '2023-01-01T00:00:00Z')
        """
        results: List[YouTubeVideo] = []
        self._rate_limit_check()

        try:
            request = self.service.search().list(
                q=query,
                part='snippet',
                type='video',
                maxResults=min(max_results, 50),
                publishedAfter=published_after
            )
            response = request.execute()

            video_ids = [item['id']['videoId'] for item in response.get('items', [])]

            if not video_ids:
                return []

            # Fetch video statistics/details in a second call
            self._rate_limit_check()
            vids_req = self.service.videos().list(
                part='snippet,statistics',
                id=','.join(video_ids),
                maxResults=len(video_ids)
            )
            vids_resp = vids_req.execute()

            for item in vids_resp.get('items', []):
                snippet = item.get('snippet', {})
                stats = item.get('statistics', {})
                results.append(YouTubeVideo(
                    video_id=item['id'],
                    title=snippet.get('title', ''),
                    description=snippet.get('description', ''),
                    channel_title=snippet.get('channelTitle', ''),
                    publish_time=snippet.get('publishedAt', ''),
                    view_count=int(stats.get('viewCount', 0)) if stats.get('viewCount') else None,
                    like_count=int(stats.get('likeCount', 0)) if stats.get('likeCount') else None,
                    comment_count=int(stats.get('commentCount', 0)) if stats.get('commentCount') else None,
                ))

            logger.info(f"YouTube search for '{query}' returned {len(results)} videos")
            return results

        except Exception as e:
            logger.error(f"YouTube search failed for query '{query}': {e}")
            return []

    def fetch_comments(self, video_id: str, max_comments: int = 100) -> List[Dict[str, Any]]:
        """Fetch top-level comments for a video. Returns list of dicts with comment data."""
        comments: List[Dict[str, Any]] = []
        page_token = None
        fetched = 0

        while fetched < max_comments:
            self._rate_limit_check()
            try:
                req = self.service.commentThreads().list(
                    part='snippet',
                    videoId=video_id,
                    maxResults=min(100, max_comments - fetched),
                    pageToken=page_token,
                    textFormat='plainText'
                )
                resp = req.execute()

                for item in resp.get('items', []):
                    snip = item['snippet']['topLevelComment']['snippet']
                    comments.append({
                        'comment_id': item['id'],
                        'author': snip.get('authorDisplayName', ''),
                        'text': snip.get('textDisplay', ''),
                        'like_count': int(snip.get('likeCount', 0)) if snip.get('likeCount') else 0,
                        'published_at': snip.get('publishedAt', ''),
                        'updated_at': snip.get('updatedAt', '')
                    })
                    fetched += 1
                    if fetched >= max_comments:
                        break

                page_token = resp.get('nextPageToken')
                if not page_token:
                    break

            except Exception as e:
                logger.warning(f"Failed to fetch comments for video {video_id}: {e}")
                break

        logger.info(f"Fetched {len(comments)} comments for video {video_id}")
        return comments

    def convert_videos_to_normalized(self, videos: List[YouTubeVideo], brand_id: str, run_id: str,
                                     include_comments: bool | None = None, comments_per_video: int = 20) -> List[NormalizedContent]:
        """Convert YouTube videos (and optional comments) into NormalizedContent objects"""
        normalized: List[NormalizedContent] = []

        for vid in videos:
            content_id = f"youtube_video_{vid.video_id}"
            event_ts = vid.publish_time or format_timestamp()
            meta = {
                'channel_title': vid.channel_title,
                'view_count': str(vid.view_count) if vid.view_count is not None else '',
                'like_count': str(vid.like_count) if vid.like_count is not None else '',
                'comment_count': str(vid.comment_count) if vid.comment_count is not None else ''
            }

            # Mark this item as a video-type content for downstream reporting
            normalized.append(NormalizedContent(
                content_id=content_id,
                src='youtube',
                platform_id=vid.video_id,
                author=vid.channel_title,
                title=vid.title,
                body=vid.description,
                rating=None,
                upvotes=None,
                helpful_count=None,
                event_ts=event_ts,
                run_id=run_id,
                meta={**meta, 'content_type': 'video'}
            ))

            # Respect global setting if not explicitly provided
            from config.settings import SETTINGS as _SETTINGS
            if include_comments is None:
                include_comments = bool(_SETTINGS.get('include_comments_in_analysis', False))

            if include_comments and vid.comment_count and int(vid.comment_count) > 0:
                comments = self.fetch_comments(vid.video_id, max_comments=comments_per_video)
                for c in comments:
                    comment_id = f"youtube_comment_{c['comment_id']}"
                    comment_ts = c.get('published_at') or format_timestamp()
                    meta_comment = {
                        'video_id': vid.video_id,
                        'video_title': vid.title,
                        'like_count': str(c.get('like_count', 0))
                    }

                    normalized.append(NormalizedContent(
                        content_id=comment_id,
                        src='youtube',
                        platform_id=c['comment_id'],
                        author=c.get('author', ''),
                        title='',
                        body=c.get('text', ''),
                        rating=None,
                        upvotes=c.get('like_count', 0),
                        helpful_count=None,
                        event_ts=comment_ts,
                        run_id=run_id,
                        meta={**meta_comment, 'content_type': 'comment'}
                    ))

        return normalized
