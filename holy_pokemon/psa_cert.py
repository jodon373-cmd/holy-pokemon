"""PSA public single-cert verification only. No private Vault endpoints."""

import os
import re
from .store import stable, now

SOURCE = "https://www.psacard.com/publicapi/documentation"


class PSACertificateAdapter:
    def __init__(self, store, token=None, request=None):
        self.store = store
        self.token = (
            token or os.getenv("PSA_API_TOKEN") or os.getenv("PSA_ACCESS_TOKEN")
        )
        self.request = request or self._request

    def _request(self, cert):
        from .psa_cert_check import check

        result = check(cert, token=self.token)
        return result.get("record") or {}

    def verify(self, cert):
        if not re.fullmatch(r"[0-9]{6,12}", str(cert)):
            raise ValueError("Numeric PSA certificate required")
        if not self.token:
            return {
                "status": "CREDENTIAL_MISSING",
                "cert_verified": False,
                "source": SOURCE,
            }
        prior = [
            r
            for r in self.store.rows("review")
            if r.get("type") == "psa_cert" and r.get("cert") == cert
        ]
        from datetime import datetime, timezone

        if (
            prior
            and (
                datetime.now(timezone.utc)
                - datetime.fromisoformat(prior[-1]["retrieved_at"])
            ).total_seconds()
            < 86400
        ):
            return prior[-1]
        payload = self.request(cert)
        data = payload.get("PSACert") or {}
        verified = (
            payload.get("IsValidRequest") is not False
            and str(data.get("CertNumber", "")) == str(cert)
            and str(payload.get("ServerMessage", "")).lower()
            in ("request successful", "request successful.")
        )
        result = {
            "type": "psa_cert",
            "cert": cert,
            "cert_verified": verified,
            "status": "MATCH" if verified else "UNVERIFIED_RESPONSE",
            "details": {
                k: data.get(k)
                for k in (
                    "CertNumber",
                    "Year",
                    "Brand",
                    "Subject",
                    "CardNumber",
                    "CardGrade",
                    "Variety",
                )
            },
            "retrieved_at": now(),
            "source": SOURCE,
        }
        self.store.put("review", stable("psa", cert, result["retrieved_at"]), result)
        return result
