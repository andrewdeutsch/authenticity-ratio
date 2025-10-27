"""
scoring.llm_client placeholder

This file previously contained a mock ChatClient used for offline smoke tests.
It has been intentionally replaced with this placeholder to avoid accidentally
using a mock in production runs. To re-enable offline testing, either:

- restore a test-only ChatClient implementation here (not recommended in prod),
- or provide a real `scoring.llm_client.ChatClient` implementation that wraps
    your chosen LLM provider and credentials.

Importing this module will raise ImportError to ensure callers detect absence
of a real client and gracefully fall back to extractive summarization.
"""

raise ImportError("scoring.llm_client removed: implement a real ChatClient or restore a test mock")
