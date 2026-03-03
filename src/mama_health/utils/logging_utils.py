"""Logging utilities for the mama health pipeline.

Provides a thin wrapper around Dagster's get_dagster_logger so that modules
can call get_logger() uniformly — and the same call works correctly whether
executed inside a Dagster run (returns the Dagster-managed logger that writes
to the event log) or in a plain test / script context (returns the standard
library logger).
"""

import logging
from typing import Any

# Lazy import: dagster may not be available in all environments
try:
    from dagster import get_dagster_logger as _get_dagster_logger

    _DAGSTER_AVAILABLE = True
except ImportError:  # pragma: no cover
    _DAGSTER_AVAILABLE = False


def get_logger(name: str = "mama_health") -> Any:
    """Return a logger appropriate for the current execution context.

    Inside a Dagster run this returns Dagster's managed logger, which
    writes structured log entries to the run event stream.  Outside of
    a run (e.g. unit tests, scripts) it returns a standard Python logger.

    Args:
        name: Logger name used when falling back to stdlib logging.

    Returns:
        A logger with .debug(), .info(), .warning(), .error() methods.
    """
    if _DAGSTER_AVAILABLE:
        try:
            return _get_dagster_logger()
        except Exception:
            # Not inside a Dagster execution context — fall through to stdlib
            pass

    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter("%(asctime)s  %(levelname)-8s  %(name)s  %(message)s")
        )
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


def log_asset_stats(logger: Any, asset_name: str, stats: dict[str, Any]) -> None:
    """Log a standardised key-value summary for an asset materialisation.

    Produces consistent log lines like::

        [posts_with_comments] total_posts=87  total_comments=3104

    Args:
        logger: Logger returned by get_logger().
        asset_name: Name of the asset being materialised.
        stats: Mapping of metric names to values to include in the log line.
    """
    pairs = "  ".join(f"{k}={v}" for k, v in stats.items())
    logger.info(f"[{asset_name}] {pairs}")
