from __future__ import annotations

import logging
import random
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TypeVar

import requests.exceptions

T = TypeVar("T")

logger = logging.getLogger(__name__)


class RetryableHTTPError(requests.exceptions.HTTPError):
    """Raised for HTTP status codes that are safe to retry (429, 502, 503, 504)."""


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int
    base_delay: float
    max_delay: float
    backoff_factor: float
    jitter: float
    retryable_exceptions: tuple[type[Exception], ...]
    retryable_status_codes: frozenset[int] = field(default_factory=frozenset)


SEFIN_SUBMIT = RetryPolicy(
    max_attempts=3,
    base_delay=1.0,
    max_delay=10.0,
    backoff_factor=2.0,
    jitter=0.25,
    retryable_exceptions=(requests.exceptions.ConnectionError,),
)

ADN_READ = RetryPolicy(
    max_attempts=4,
    base_delay=1.0,
    max_delay=15.0,
    backoff_factor=2.0,
    jitter=0.25,
    retryable_exceptions=(
        requests.exceptions.ConnectionError,
        requests.exceptions.Timeout,
        RetryableHTTPError,
    ),
    retryable_status_codes=frozenset({429, 502, 503, 504}),
)


def _calc_delay(attempt: int, policy: RetryPolicy) -> float:
    """Calculate delay with exponential backoff and jitter.

    *attempt* is 0-indexed (0 = delay after first failure).
    """
    delay = policy.base_delay * (policy.backoff_factor**attempt)
    delay = min(delay, policy.max_delay)
    jitter_range = delay * policy.jitter
    delay += random.uniform(-jitter_range, jitter_range)
    return max(0.0, delay)


def retry_call(
    func: Callable[[], T],
    policy: RetryPolicy,
    *,
    sleep_func: Callable[[float], object] = time.sleep,
) -> T:
    """Execute *func()* with retry per *policy*, re-raising on exhaustion."""
    last_exc: Exception | None = None
    for attempt in range(policy.max_attempts):
        try:
            return func()
        except policy.retryable_exceptions as exc:
            last_exc = exc
            if attempt < policy.max_attempts - 1:
                delay = _calc_delay(attempt, policy)
                logger.warning(
                    "Retry %d/%d after %s (%.1fs delay)",
                    attempt + 1,
                    policy.max_attempts,
                    type(exc).__name__,
                    delay,
                )
                sleep_func(delay)
    raise last_exc  # type: ignore[misc]
