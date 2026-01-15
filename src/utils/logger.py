"""Logging utility for IGEL Profile Compare & Migration Tool.

Provides a centralized logging system that:
- Logs to both file and console
- Stores logs locally in human-readable format
- Does not expose sensitive data
- Supports different log levels
"""

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional
import re


class SensitiveDataFilter(logging.Filter):
    """Filter to redact potentially sensitive data from logs."""

    # Patterns that might contain sensitive data
    SENSITIVE_PATTERNS = [
        (r'password["']?\s*[:=]\s*["']?[^"'",\s]+', 'password=***REDACTED***'),
        (r'token["']?\s*[:=]\s*["']?[^"'",\s]+', 'token=***REDACTED***'),
        (r'secret["']?\s*[:=]\s*["']?[^"'",\s]+', 'secret=***REDACTED***'),
        (r'api_key["']?\s*[:=]\s*["']?[^"'",\s]+', 'api_key=***REDACTED***'),
    ]

    def filter(self, record: logging.LogRecord) -> bool:
        """Filter and redact sensitive data from log messages."""
        if hasattr(record, 'msg') and isinstance(record.msg, str):
            for pattern, replacement in self.SENSITIVE_PATTERNS:
                record.msg = re.sub(pattern, replacement, record.msg, flags=re.IGNORECASE)
        return True


class AppLogger:
    """Application logger with file and console output."""

    _instance: Optional['AppLogger'] = None
    _initialized: bool = False

    def __new__(cls) -> 'AppLogger':
        """Singleton pattern to ensure single logger instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize the logger if not already initialized."""
        if AppLogger._initialized:
            return

        self.logger = logging.getLogger('IGELProfileCompare')
        self.logger.setLevel(logging.DEBUG)

        # Create logs directory
        self.log_dir = self._get_log_directory()
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Create log file with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.log_file = self.log_dir / f'igel_profile_compare_{timestamp}.log'

        # File handler - detailed logging
        file_handler = logging.FileHandler(self.log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_format = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_format)
        file_handler.addFilter(SensitiveDataFilter())

        # Console handler - info and above
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_format = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(message)s',
            datefmt='%H:%M:%S'
        )
        console_handler.setFormatter(console_format)
        console_handler.addFilter(SensitiveDataFilter())

        # Add handlers
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

        AppLogger._initialized = True
        self.logger.info(f'Logger initialized. Log file: {self.log_file}')

    def _get_log_directory(self) -> Path:
        """Get the appropriate log directory based on OS."""
        # Use AppData on Windows, ~/.local/share on Linux
        if os.name == 'nt':
            base = Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData' / 'Local'))
        else:
            base = Path.home() / '.local' / 'share'

        return base / 'IGELProfileCompare' / 'logs'

    def debug(self, message: str) -> None:
        """Log debug message."""
        self.logger.debug(message)

    def info(self, message: str) -> None:
        """Log info message."""
        self.logger.info(message)

    def warning(self, message: str) -> None:
        """Log warning message."""
        self.logger.warning(message)

    def error(self, message: str) -> None:
        """Log error message."""
        self.logger.error(message)

    def critical(self, message: str) -> None:
        """Log critical message."""
        self.logger.critical(message)

    def exception(self, message: str) -> None:
        """Log exception with traceback."""
        self.logger.exception(message)

    def get_log_file_path(self) -> Path:
        """Return the current log file path."""
        return self.log_file

    def get_log_directory(self) -> Path:
        """Return the log directory path."""
        return self.log_dir


# Global logger instance
def get_logger() -> AppLogger:
    """Get the application logger instance."""
    return AppLogger()
