"""
Structured logging configuration.

Phase 2 remediation: structlog has been a declared dependency since the
start of this project but was never imported or configured anywhere — every
log line in the codebase is a plain stdlib logger.info()/print() with no
request correlation. This module wires it up.

Usage elsewhere in the codebase (gradual migration, not a forced rewrite):
    from core.logging import get_logger
    logger = get_logger(__name__)
    logger.info("meme_generated", meme_id=meme.id, template_id=template.id)

structured kwargs (not f-strings) are the point — they make logs queryable
in whatever log aggregator you point stdout at.
"""
from __future__ import annotations

import logging
import sys

import structlog

from core.config import settings


def configure_logging() -> None:
    """Call once, at process startup, before the FastAPI app is constructed."""
    level = getattr(logging, settings.log_level.upper(), logging.INFO)

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=level,
    )
    # Quiet the noisiest third-party loggers down to WARNING regardless of
    # our own LOG_LEVEL, so DEBUG/INFO doesn't drown in driver chatter.
    for noisy in ("sqlalchemy.engine", "httpx", "httpcore", "asyncio"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    # JSON in production (log-aggregator friendly), readable console output
    # in development.
    renderer = (
        structlog.processors.JSONRenderer()
        if settings.is_production
        else structlog.dev.ConsoleRenderer()
    )

    structlog.configure(
        processors=shared_processors + [renderer],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str = "memegpt"):
    return structlog.get_logger(name)
