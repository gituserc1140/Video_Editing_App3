"""Configuration settings for the Creatomate Streamlit micro-app."""

import os

try:
    import streamlit as _st

    _secrets = _st.secrets
except Exception:  # pragma: no cover - streamlit secrets are optional (e.g. outside Streamlit runtime)
    _secrets = {}


def _forward_secret_to_env(name: str) -> None:
    """Forward a Streamlit secret into the process environment if not already set.

    boto3 (and other SDKs) read credentials from environment variables, not from
    st.secrets directly, so Streamlit Cloud deployments that configure secrets via
    the dashboard need those values copied into os.environ at startup.
    """
    if name in os.environ:
        return
    try:
        if name in _secrets:
            os.environ[name] = str(_secrets[name])
    except Exception:  # pragma: no cover - defensive against non-mapping secrets objects
        pass


for _name in (
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
    "AWS_SESSION_TOKEN",
    "AWS_S3_BUCKET",
    "AWS_S3_REGION",
):
    _forward_secret_to_env(_name)


CREATOMATE_BASE_URL = os.getenv("CREATOMATE_BASE_URL", "https://api.creatomate.com/v1")
DEFAULT_TIMEOUT = int(os.getenv("DEFAULT_TIMEOUT", "30"))
POLL_INTERVAL_SECONDS = int(os.getenv("POLL_INTERVAL_SECONDS", "3"))
RENDER_WAIT_TIMEOUT = int(os.getenv("RENDER_WAIT_TIMEOUT", "300"))

# Private S3 upload settings for the "Upload video" tab. AWS credentials
# (AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY / AWS_SESSION_TOKEN) are read by
# boto3's standard credential chain from the environment - they are never
# hard-coded here and should be set via environment variables or Streamlit secrets.
AWS_S3_BUCKET = os.getenv("AWS_S3_BUCKET", "")
AWS_S3_REGION = os.getenv("AWS_S3_REGION", "us-east-1")
S3_UPLOAD_PREFIX = os.getenv("S3_UPLOAD_PREFIX", "uploads")
S3_PRESIGNED_URL_EXPIRY_SECONDS = int(os.getenv("S3_PRESIGNED_URL_EXPIRY_SECONDS", "3600"))
