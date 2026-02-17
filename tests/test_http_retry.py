from __future__ import annotations

import pytest
import requests.exceptions

from emissor.services.http_retry import (
    ADN_READ,
    SEFIN_SUBMIT,
    RetryableHTTPError,
    RetryPolicy,
    _calc_delay,
    retry_call,
)


class TestRetryCall:
    def test_success_first_attempt(self):
        result = retry_call(lambda: 42, SEFIN_SUBMIT, sleep_func=lambda _: None)
        assert result == 42

    def test_retries_connection_error_then_succeeds(self):
        calls = []

        def func():
            calls.append(1)
            if len(calls) < 2:
                raise requests.exceptions.ConnectionError("reset")
            return "ok"

        result = retry_call(func, SEFIN_SUBMIT, sleep_func=lambda _: None)
        assert result == "ok"
        assert len(calls) == 2

    def test_exhausts_retries_and_reraises(self):
        def func():
            raise requests.exceptions.ConnectionError("down")

        with pytest.raises(requests.exceptions.ConnectionError, match="down"):
            retry_call(func, SEFIN_SUBMIT, sleep_func=lambda _: None)

    def test_does_not_retry_non_retryable(self):
        calls = []

        def func():
            calls.append(1)
            raise RuntimeError("fatal")

        with pytest.raises(RuntimeError, match="fatal"):
            retry_call(func, SEFIN_SUBMIT, sleep_func=lambda _: None)
        assert len(calls) == 1

    def test_retries_retryable_http_error(self):
        calls = []

        def func():
            calls.append(1)
            if len(calls) < 3:
                raise RetryableHTTPError("503")
            return "recovered"

        result = retry_call(func, ADN_READ, sleep_func=lambda _: None)
        assert result == "recovered"
        assert len(calls) == 3

    def test_backoff_delays_increase(self):
        delays: list[float] = []

        def func():
            if len(delays) < 2:
                raise requests.exceptions.ConnectionError("err")
            return "done"

        result = retry_call(func, SEFIN_SUBMIT, sleep_func=delays.append)
        assert result == "done"
        assert len(delays) == 2
        assert delays[1] > delays[0]

    def test_delay_capped_at_max(self):
        policy = RetryPolicy(
            max_attempts=6,
            base_delay=5.0,
            max_delay=8.0,
            backoff_factor=3.0,
            jitter=0.0,
            retryable_exceptions=(requests.exceptions.ConnectionError,),
        )
        delays: list[float] = []

        def func():
            if len(delays) < 5:
                raise requests.exceptions.ConnectionError("err")
            return "done"

        retry_call(func, policy, sleep_func=delays.append)
        # With jitter=0, all delays after the first should be capped at 8.0
        for d in delays:
            assert d <= policy.max_delay

    def test_sleep_func_called_between_retries(self):
        sleep_calls: list[float] = []

        def func():
            if len(sleep_calls) < 1:
                raise requests.exceptions.ConnectionError("err")
            return "ok"

        retry_call(func, SEFIN_SUBMIT, sleep_func=sleep_calls.append)
        assert len(sleep_calls) == 1
        assert sleep_calls[0] > 0


class TestSefinPolicy:
    def test_does_not_retry_read_timeout(self):
        calls = []

        def func():
            calls.append(1)
            raise requests.exceptions.ReadTimeout("read timed out")

        with pytest.raises(requests.exceptions.ReadTimeout):
            retry_call(func, SEFIN_SUBMIT, sleep_func=lambda _: None)
        assert len(calls) == 1

    def test_retries_connect_timeout(self):
        """ConnectTimeout inherits from ConnectionError, so SEFIN_SUBMIT retries it."""
        calls = []

        def func():
            calls.append(1)
            if len(calls) < 2:
                raise requests.exceptions.ConnectTimeout("connect timed out")
            return "ok"

        result = retry_call(func, SEFIN_SUBMIT, sleep_func=lambda _: None)
        assert result == "ok"
        assert len(calls) == 2

    def test_max_attempts(self):
        assert SEFIN_SUBMIT.max_attempts == 3


class TestAdnPolicy:
    def test_retries_timeout(self):
        calls = []

        def func():
            calls.append(1)
            if len(calls) < 2:
                raise requests.exceptions.Timeout("timed out")
            return "ok"

        result = retry_call(func, ADN_READ, sleep_func=lambda _: None)
        assert result == "ok"

    def test_retries_read_timeout(self):
        calls = []

        def func():
            calls.append(1)
            if len(calls) < 2:
                raise requests.exceptions.ReadTimeout("read timed out")
            return "ok"

        result = retry_call(func, ADN_READ, sleep_func=lambda _: None)
        assert result == "ok"

    def test_retries_retryable_http_error(self):
        calls = []

        def func():
            calls.append(1)
            if len(calls) < 2:
                raise RetryableHTTPError("502")
            return "ok"

        result = retry_call(func, ADN_READ, sleep_func=lambda _: None)
        assert result == "ok"

    def test_retryable_status_codes(self):
        assert ADN_READ.retryable_status_codes == frozenset({429, 502, 503, 504})

    def test_max_attempts(self):
        assert ADN_READ.max_attempts == 4


class TestCalcDelay:
    def test_exponential_growth(self):
        policy = RetryPolicy(
            max_attempts=5,
            base_delay=1.0,
            max_delay=100.0,
            backoff_factor=2.0,
            jitter=0.0,
            retryable_exceptions=(),
        )
        d0 = _calc_delay(0, policy)
        d1 = _calc_delay(1, policy)
        d2 = _calc_delay(2, policy)
        assert d0 == pytest.approx(1.0)
        assert d1 == pytest.approx(2.0)
        assert d2 == pytest.approx(4.0)

    def test_capped_at_max_delay(self):
        policy = RetryPolicy(
            max_attempts=5,
            base_delay=10.0,
            max_delay=15.0,
            backoff_factor=2.0,
            jitter=0.0,
            retryable_exceptions=(),
        )
        d3 = _calc_delay(3, policy)  # 10 * 2^3 = 80 → capped at 15
        assert d3 == pytest.approx(15.0)

    def test_jitter_within_bounds(self):
        policy = RetryPolicy(
            max_attempts=5,
            base_delay=4.0,
            max_delay=100.0,
            backoff_factor=1.0,
            jitter=0.25,
            retryable_exceptions=(),
        )
        # base delay = 4.0, jitter range = ±1.0, so delay in [3.0, 5.0]
        for _ in range(100):
            d = _calc_delay(0, policy)
            assert 3.0 <= d <= 5.0
