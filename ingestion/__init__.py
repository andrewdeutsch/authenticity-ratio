"""
Data ingestion module for AR tool
Supports multiple sources: Reddit, Amazon, etc.
"""

"""
Data ingestion module for AR tool
Supports multiple sources: Reddit, Amazon, etc.

This package intentionally avoids importing optional source-specific modules at
package import time. Those modules may require optional third-party packages
that are not always installed (for example, `praw` for Reddit). Callers should
import source classes lazily or handle missing optional dependencies.
"""

from .normalizer import ContentNormalizer

__all__ = ['ContentNormalizer']
