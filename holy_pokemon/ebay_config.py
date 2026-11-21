"""Private backend configuration. Never execute a credential file as shell code."""

import os
import shlex
import stat
from pathlib import Path

ENV_FILE = Path.home() / ".config/holy-pokemon/ebay.env"
KEYS = {
    "EBAY_CLIENT_ID",
    "EBAY_CLIENT_SECRET",
    "EBAY_ENABLED",
    "EBAY_PRODUCTION_APPROVED",
}


def read_env_file(path=ENV_FILE):
    path = Path(path)
    info = path.lstat()
    if (
        not stat.S_ISREG(info.st_mode)
        or stat.S_IMODE(info.st_mode) & 0o077
        or info.st_uid != os.getuid()
        or info.st_size > 65536
    ):
        raise ValueError("eBay configuration must be an owner-only regular file (0600)")
    values = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].strip()
        key, separator, raw = line.partition("=")
        key = key.strip()
        if not separator or key not in KEYS:
            raise ValueError("Unsupported eBay configuration entry; contents withheld")
        try:
            parts = shlex.split(raw, comments=True)
        except ValueError:
            raise ValueError(
                "Malformed eBay configuration value; contents withheld"
            ) from None
        if len(parts) != 1 or key in values:
            raise ValueError(
                "Invalid or duplicate eBay configuration entry; contents withheld"
            )
        values[key] = parts[0]
    return values


def is_fixture_database():
    """An explicit owner DB path is still the owner DB, including local workers."""
    from .store import DEFAULT_DB

    value = os.getenv("HOLY_DATABASE")
    return bool(value and Path(value).resolve() != DEFAULT_DB.resolve())


def load_backend_environment():
    """Normal app restart loads local secrets; fixture databases stay offline."""
    if (
        is_fixture_database()
        and os.getenv("HOLY_ALLOW_PRODUCTION_FOR_FIXTURE") != "true"
    ):
        return
    from .psa_config import load as load_psa
    load_psa()
    if ENV_FILE.exists():
        for key, value in read_env_file().items():
            os.environ.setdefault(key, value)


def operator_authorized():
    """Permission to attempt Production is distinct from endpoint authorization."""
    import json
    from .store import ROOT

    if os.getenv("EBAY_PRODUCTION_APPROVED") == "true":
        return True
    if is_fixture_database():
        return False
    path = ROOT / "outputs/ebay_production_authorization.json"
    try:
        return (
            json.loads(path.read_text()).get("owner_authorized_readonly_probe") is True
        )
    except (OSError, ValueError):
        return False
