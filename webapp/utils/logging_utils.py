"""
Logging utilities for Streamlit webapp
"""
import logging
import streamlit as st
import time
import html as html_module


class StreamlitLogHandler(logging.Handler):
    """
    Custom logging handler that captures log messages and sends them to a ProgressAnimator.
    """

    def __init__(self, progress_animator):
        """
        Initialize the handler.

        Args:
            progress_animator: ProgressAnimator instance to send logs to
        """
        super().__init__()
        self.progress_animator = progress_animator

    def emit(self, record):
        """
        Emit a log record.

        Args:
            record: LogRecord to emit
        """
        try:
            # Format the log message
            msg = self.format(record)
            # Send to progress animator
            self.progress_animator.add_log(msg)
        except Exception:
            self.handleError(record)


class ProgressAnimator:
    """
    Animated progress indicator that displays messages with pulsing effects.
    Each message appears at 100% visibility, then pulses (80% -> 100%) until replaced.
    """

    def __init__(self, container=None):
        """
        Initialize the progress animator.

        Args:
            container: Streamlit container to use. If None, creates a new empty container.
        """
        self.container = container if container is not None else st.empty()
        self.current_message = None
        self.current_emoji = None
        self.logs = []
        self.max_logs = 50  # Keep last 50 log entries

    def add_log(self, message: str):
        """
        Add a log message to the display.

        Args:
            message: The log message to add
        """
        self.logs.append(message)
        # Keep only the last max_logs entries
        if len(self.logs) > self.max_logs:
            self.logs = self.logs[-self.max_logs:]
        # Re-render with the new log
        self._render()
        # Small sleep to allow Streamlit to update UI
        time.sleep(0.01)

    def show(self, message: str, emoji: str = "🔍", url: str = None):
        """
        Display an animated progress message that pulses until next update.

        Args:
            message: The progress message to display (will be truncated if too long)
            emoji: Emoji to show with the message
            url: Optional URL to display below the message (shown at 40% opacity)
        """
        # Truncate message if too long (keep it concise for animation effect)
        max_length = 120
        if len(message) > max_length:
            message = message[:max_length-3] + "..."

        self.current_message = message
        self.current_emoji = emoji
        self.current_url = url

        self._render()

    def _render(self):
        """Internal method to render the current state."""
        # Build URL display if provided
        url_html = ""
        if hasattr(self, 'current_url') and self.current_url:
            # Truncate URL for display
            display_url = self.current_url if len(self.current_url) <= 80 else self.current_url[:77] + "..."
            display_url = html_module.escape(display_url)
            url_html = f'<div class="progress-urls">{display_url}</div>'

        # Build logs display
        logs_html = ""
        if self.logs:
            # Escape HTML in log messages for security and show only the last log
            last_log = html_module.escape(self.logs[-1])
            logs_html = f'<div class="progress-logs"><div class="progress-log-entry">{last_log}</div></div>'

        # Escape message and emoji
        safe_message = html_module.escape(self.current_message) if self.current_message else ""
        safe_emoji = html_module.escape(self.current_emoji) if self.current_emoji else ""

        # Display with pulsing animation (stays visible until next call)
        html = f"""
        <div class="progress-container">
            <div class="progress-item progress-item-pulsing">
                <span class="progress-emoji">{safe_emoji}</span>
                <span>{safe_message}</span>
            </div>
            {url_html}
            {logs_html}
        </div>
        """

        self.container.markdown(html, unsafe_allow_html=True)

    def clear(self):
        """Clear the progress display."""
        self.container.empty()
        self.current_message = None
        self.current_emoji = None
        self.logs = []
