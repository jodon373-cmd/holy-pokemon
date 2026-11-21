"""TLS and redacted errors for the reviewed Browse adapter."""

import ssl


class NetworkProblem(RuntimeError):
    def __init__(self, code):
        super().__init__("eBay network failure: " + code)


def context():
    try:
        import certifi

        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


def failure(exc):
    return NetworkProblem("CONNECTION")
