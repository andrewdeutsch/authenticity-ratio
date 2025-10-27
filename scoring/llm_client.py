"""
OpenAI-backed ChatClient for LLM-powered text summarization.

This module provides a production ChatClient implementation that wraps OpenAI's API.
Used primarily for generating abstractive summaries in report generation.

Configuration:
    OPENAI_API_KEY: Set via environment variable or config/settings.py

Example usage:
    client = ChatClient()
    response = client.chat(
        model='gpt-3.5-turbo',
        messages=[{'role': 'user', 'content': 'Summarize this text...'}],
        max_tokens=150
    )
    summary = response.get('content')
"""

import os
import logging
from typing import Dict, Any, List, Optional

try:
    from openai import OpenAI
    from openai import OpenAIError
    _HAVE_OPENAI = True
except ImportError:
    OpenAI = None
    OpenAIError = Exception
    _HAVE_OPENAI = False

logger = logging.getLogger(__name__)


class ChatClient:
    """
    OpenAI-backed chat client for LLM text generation.

    This client is used for abstractive text summarization in report generation.
    It wraps the OpenAI API with a simple interface.

    Configuration:
        - OPENAI_API_KEY environment variable or APIConfig.openai_api_key
        - Defaults to gpt-3.5-turbo model if not specified

    Raises:
        ImportError: If openai package is not installed
        ValueError: If API key is not configured
    """

    def __init__(self, api_key: Optional[str] = None, default_model: str = 'gpt-3.5-turbo'):
        """
        Initialize ChatClient with OpenAI credentials.

        Args:
            api_key: OpenAI API key (optional, will use env var if not provided)
            default_model: Default model to use (default: gpt-3.5-turbo)

        Raises:
            ImportError: If openai package is not installed
            ValueError: If API key is not configured
        """
        if not _HAVE_OPENAI:
            raise ImportError(
                "OpenAI package not installed. Install with: pip install openai"
            )

        # Get API key from arg, config, or environment
        if api_key is None:
            try:
                from config.settings import APIConfig
                api_key = APIConfig.openai_api_key
            except Exception:
                pass

        if api_key is None:
            api_key = os.environ.get('OPENAI_API_KEY')

        if not api_key:
            raise ValueError(
                "OpenAI API key not configured. Set OPENAI_API_KEY environment variable "
                "or configure APIConfig.openai_api_key in config/settings.py"
            )

        self.client = OpenAI(api_key=api_key)
        self.default_model = default_model
        logger.info(f"ChatClient initialized with model: {default_model}")

    def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        max_tokens: int = 150,
        temperature: float = 0.3,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Send a chat completion request to OpenAI API.

        Args:
            messages: List of message dicts with 'role' and 'content' keys
            model: Model to use (default: gpt-3.5-turbo)
            max_tokens: Maximum tokens to generate (default: 150)
            temperature: Sampling temperature 0-1 (default: 0.3)
            **kwargs: Additional arguments to pass to OpenAI API

        Returns:
            Dict with 'content' or 'text' key containing the response text

        Raises:
            OpenAIError: If API request fails
        """
        if model is None:
            model = self.default_model

        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                **kwargs
            )

            # Extract the response content
            content = response.choices[0].message.content

            # Return dict format expected by callers
            return {
                'content': content,
                'text': content,  # Alias for backward compatibility
                'model': model,
                'usage': {
                    'prompt_tokens': response.usage.prompt_tokens if hasattr(response, 'usage') else 0,
                    'completion_tokens': response.usage.completion_tokens if hasattr(response, 'usage') else 0,
                    'total_tokens': response.usage.total_tokens if hasattr(response, 'usage') else 0
                }
            }

        except OpenAIError as e:
            logger.error(f"OpenAI API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in chat completion: {e}")
            raise

    def summarize(
        self,
        text: str,
        max_words: int = 120,
        model: Optional[str] = None
    ) -> Optional[str]:
        """
        Convenience method for text summarization.

        Args:
            text: Text to summarize
            max_words: Target word count for summary (default: 120)
            model: Model to use (default: gpt-3.5-turbo)

        Returns:
            Summary text or None if request fails
        """
        if not text or not text.strip():
            return None

        prompt = (
            f"Write a concise {max_words}-word human-readable summary (1-2 lines) "
            f"of the following content.\n\nContent:\n{text}\n\nSummary:"
        )

        try:
            response = self.chat(
                messages=[{"role": "user", "content": prompt}],
                model=model,
                max_tokens=min(300, max_words * 2)  # Rough token estimate
            )
            return response.get('content') or response.get('text')
        except Exception as e:
            logger.warning(f"Summarization failed: {e}")
            return None
