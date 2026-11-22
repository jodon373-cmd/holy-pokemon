"""Restricted TLS context and sanitized network error helpers for eBay Browse."""
from __future__ import annotations

import ssl


class NetworkProblem(RuntimeError):
    """Sanitized network failure that never exposes credentials or raw headers."""


def context() -> ssl.SSLContext:
    """Return a strict TLS 1.2+ SSL context using system trust roots."""
    ctx = ssl.create_default_context()
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    return ctx


def failure(exc: BaseException) -> NetworkProblem:
    """Map low-level socket/URL errors to a safe, non-leaky NetworkProblem."""
    name = type(exc).__name__
    return NetworkProblem(f"NETWORK_ERROR:{name}")
