"""structlog configuration — stdout for humans, optional JSON for files.

Kept tiny in M1: the CLI's top-level callback calls `configure_logging` once
with `verbose` from the user and every module uses `structlog.get_logger()`.
"""

from __future__ import annotations

import logging
import sys

import structlog


def configure_logging(*, verbose: bool = False) -> None:
    """Configure structlog + stdlib logging.

    INFO by default, DEBUG under --verbose. Renders a console-friendly format
    to stderr so stdout stays clean for pipeable output.
    """
    level = logging.DEBUG if verbose else logging.INFO

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stderr,
        level=level,
    )

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=False),
            structlog.dev.ConsoleRenderer(colors=sys.stderr.isatty()),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        logger_factory=structlog.PrintLoggerFactory(file=sys.stderr),
        cache_logger_on_first_use=True,
    )
