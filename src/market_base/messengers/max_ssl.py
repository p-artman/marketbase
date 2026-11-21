"""SSL trust helpers for Max API (Минцифры / Russian Trusted CA).

platform-api2.max.ru is signed by the Russian Trusted CA chain, which is not
in the default certifi bundle used by requests.
"""

from __future__ import annotations

import logging
import os
import tempfile
from functools import lru_cache
from pathlib import Path
from typing import Union

logger = logging.getLogger(__name__)

_CERT_NAMES = (
    'russian_trusted_root_ca.cer',
    'russian_trusted_sub_ca.cer',
)

VerifyArg = Union[bool, str]


def ssl_verify_arg() -> VerifyArg:
    """Return requests `verify=` value for Max HTTPS calls.

    - MAX_SSL_VERIFY=false|0|no|off → disable verification (local escape hatch)
    - otherwise → path to a CA bundle (certifi + Russian Trusted CAs)
    """
    flag = os.getenv('MAX_SSL_VERIFY', 'true').strip().lower()
    if flag in {'0', 'false', 'no', 'off'}:
        logger.warning('MAX_SSL_VERIFY disabled — Max API TLS is not verified')
        return False
    custom = os.getenv('MAX_SSL_CA_BUNDLE', '').strip()
    if custom:
        return custom
    return _ca_bundle_path()


@lru_cache(maxsize=1)
def _ca_bundle_path() -> str:
    try:
        import certifi
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            'certifi is required for Max SSL verification (comes with requests)'
        ) from exc

    cert_dir = Path(__file__).resolve().parent / 'certs'
    parts = [Path(certifi.where()).read_bytes()]
    missing = []
    for name in _CERT_NAMES:
        path = cert_dir / name
        if not path.is_file():
            missing.append(str(path))
            continue
        data = path.read_bytes().replace(b'\r\n', b'\n')
        if not data.endswith(b'\n'):
            data += b'\n'
        parts.append(data)

    if missing:
        logger.warning(
            'Russian Trusted CA files missing (%s); Max SSL may fail',
            ', '.join(missing),
        )

    fd, bundle_path = tempfile.mkstemp(prefix='bsl_max_ca_', suffix='.pem')
    try:
        with os.fdopen(fd, 'wb') as handle:
            for chunk in parts:
                handle.write(chunk)
                if not chunk.endswith(b'\n'):
                    handle.write(b'\n')
    except Exception:
        try:
            os.unlink(bundle_path)
        except OSError:
            pass
        raise

    return bundle_path
