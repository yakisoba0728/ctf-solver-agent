"""Tests for circuit breaker."""

import time

from ctf_solver.tracking.circuit_breaker import CircuitBreaker


def test_starts_available():
    cb = CircuitBreaker()
    assert cb.is_available()


def test_trips_after_threshold():
    cb = CircuitBreaker(failure_threshold=3)
    cb.record_failure()
    cb.record_failure()
    assert cb.is_available()
    cb.record_failure()
    assert not cb.is_available()


def test_success_resets():
    cb = CircuitBreaker(failure_threshold=3)
    cb.record_failure()
    cb.record_failure()
    cb.record_success()
    cb.record_failure()
    cb.record_failure()
    assert cb.is_available()


def test_recovery_after_timeout(monkeypatch):
    cb = CircuitBreaker(failure_threshold=1, recovery_timeout=10.0)
    cb.record_failure()
    assert not cb.is_available()
    current_time = time.monotonic()
    monkeypatch.setattr("time.monotonic", lambda: current_time + 11.0)
    assert cb.is_available()
