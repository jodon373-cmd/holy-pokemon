"""Read-only individual PSA certificate verification; never bulk download or train on PSA data.

Use: PSA_ACCESS_TOKEN=<private> python -m holy_pokemon.psa_cert_check 12345678
Token must be supplied securely via environment; never commit or paste to logs.
"""

from __future__ import annotations
import argparse
import json
import os
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener, HTTPSHandler, HTTPRedirectHandler
from .ebay_network import context

CERT_PATTERN = re.compile(r"^[0-9]{6,12}$")
API_BASE = "https://api.psacard.com/publicapi/cert/GetByCertNumber/"


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *_args, **_kwargs):
        return None


def check(cert: str, *, token: str, request=None) -> dict:
    if not CERT_PATTERN.fullmatch(str(cert)):
        raise ValueError("Expected a 6–12-digit certification number")
    if not token or any(c in token for c in "\r\n"):
        raise ValueError("A private PSA bearer token is required")
    if request is None:

        def request(url, headers):
            opener = build_opener(NoRedirect, HTTPSHandler(context=context()))
            with opener.open(
                Request(url, headers=headers, method="GET"), timeout=15
            ) as response:
                if response.status != 200:
                    raise RuntimeError("PSA lookup returned non-200 HTTP status")
                return json.load(response)

    try:
        result = request(
            API_BASE + cert,
            {"Authorization": "bearer " + token, "Accept": "application/json"},
        )
    except (HTTPError, URLError, OSError, ValueError, RuntimeError):
        # Do not leak token, server body, or full trace to stdout.
        return {"cert": cert, "status": "LOOKUP_UNAVAILABLE", "verified": False}
    if not isinstance(result, dict):
        return {"cert": cert, "status": "INVALID_RESPONSE", "verified": False}
    valid = result.get("IsValidRequest")
    message = str(result.get("ServerMessage", "")).casefold()
    data = result.get("PSACert") or {}
    if not isinstance(data, dict):
        data = {}
    success = (
        valid is not False
        and message.rstrip(".") == "request successful"
        and str(data.get("CertNumber", "")) == str(cert)
    )
    return {
        "cert": cert,
        "status": "VERIFIED_CERT_RECORD" if success else "NOT_VERIFIED",
        "verified": success,
        "official_cert_url": "https://www.psacard.com/cert/" + cert,
        "record": result if success else None,
        "warning": "A matching cert does not authenticate the actual physical slab.",
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cert")
    args = parser.parse_args(argv)
    token = os.getenv("PSA_ACCESS_TOKEN") or os.getenv("PSA_API_TOKEN", "")
    if not token:
        print(
            json.dumps(
                {
                    "status": "NO_PSA_TOKEN",
                    "message": "Set PSA_ACCESS_TOKEN securely on your Mac",
                }
            )
        )
        return 2
    try:
        print(json.dumps(check(args.cert, token=token), indent=2))
    except ValueError as exc:
        print(json.dumps({"status": "INVALID_INPUT", "message": str(exc)}))
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
