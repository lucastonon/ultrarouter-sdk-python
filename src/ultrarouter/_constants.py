"""Default configuration values and environment variable names."""

from __future__ import annotations

from ._version import __version__

__all__ = [
    "API_KEY_ENV_VARS",
    "BASE_URL_ENV_VARS",
    "DEFAULT_BASE_URL",
    "DEFAULT_MAX_RETRIES",
    "DEFAULT_TIMEOUT_S",
    "USER_AGENT",
]

#: The hosted gateway. Pass ``base_url=`` (or set ``ULTRAROUTER_BASE_URL``) for any other
#: deployment, such as a self-hosted gateway or a local development stack.
DEFAULT_BASE_URL = "https://api.ultrarouter.dev"

#: Total time budget for one call, across retries, in seconds.
DEFAULT_TIMEOUT_S = 600.0

#: Automatic retries for retryable failures (so up to three attempts in total).
DEFAULT_MAX_RETRIES = 2

#: Environment variables read for the API key, in priority order.
API_KEY_ENV_VARS: tuple[str, ...] = ("ULTRAROUTER_API_KEY", "UR_API_KEY")

#: Environment variables read for the base URL, in priority order.
BASE_URL_ENV_VARS: tuple[str, ...] = ("ULTRAROUTER_BASE_URL", "UR_BASE_URL")

#: The ``User-Agent`` header every request carries.
USER_AGENT = f"ultrarouter-python/{__version__}"
