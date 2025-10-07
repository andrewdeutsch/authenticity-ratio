"""
Data ingestion module for AR tool
Supports multiple sources: Reddit, Amazon, etc.
"""

from .reddit_crawler import RedditCrawler
from .amazon_scraper import AmazonScraper
from .normalizer import ContentNormalizer

__all__ = ['RedditCrawler', 'AmazonScraper', 'ContentNormalizer']
