"""
Sentry error tracking initialization.

Phase 2 remediation: sentry-sdk[fastapi] has been a declared dependency,
and SENTRY_DSN has been set in backend/.env.production and
backend/.env.staging, since the start of this project — but nothing ever
called sentry_sdk.init(). The team had zero error-tracking visibility in
practice despite budgeting for it. This closes that gap.
"""
import logging

from core.config import settings

logger = logging.getLogger(__name__)


def init_sentry() -> None:
    """Call once, at process startup, before the FastAPI app is constructed.
    No-ops cleanly if SENTRY_DSN isn't set (e.g. local dev)."""
    if not settings.sentry_dsn:
        logger.info("SENTRY_DSN not set — Sentry error tracking disabled")
        return

    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.starlette import StarletteIntegration
        from sentry_sdk.integrations.logging import LoggingIntegration
    except ImportError:
        logger.warning("sentry-sdk not installed — skipping Sentry init despite SENTRY_DSN being set")
        return

    # Send breadcrumbs from INFO+, full events to Sentry from ERROR+.
    sentry_logging = LoggingIntegration(level=logging.INFO, event_level=logging.ERROR)

    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.environment,
        integrations=[FastApiIntegration(), StarletteIntegration(), sentry_logging],
        traces_sample_rate=settings.sentry_traces_sample_rate,
        # Meme prompts/captions can include arbitrary user text — don't ship
        # request bodies/PII to Sentry by default.
        send_default_pii=False,
    )
    logger.info(
        "Sentry initialized (environment=%s, traces_sample_rate=%s)",
        settings.environment,
        settings.sentry_traces_sample_rate,
    )
