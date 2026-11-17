"""All configuration, read once from environment variables."""

from functools import lru_cache
from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=None, extra="ignore")

    app_version: str = "0.1.0"

    database_url: str
    secret_key: str

    s3_endpoint: str = "http://objectstore:9000"
    s3_access_key: str
    s3_secret_key: str
    s3_bucket: str = "ailms"
    s3_region: str = "us-east-1"

    smtp_host: str = "mail"
    smtp_port: int = 1025
    mail_from: str = "AI-LMS <no-reply@ailms.example>"

    # Demo mode (ADR 0008 section G).
    demo_mode: bool = False
    public_demo: bool = False
    demo_access_code: str = ""
    signup_open: bool = False

    default_organisation_slug: str = "default"
    session_days: int = 30
    login_code_minutes: int = 10
    login_code_max_attempts: int = 5
    login_code_max_requests: int = 3  # per email, per login_code_minutes

    sample_data_dir: Path = Path("/app/sample-data")

    # Hosts whose X-Forwarded-Proto header is believed: the web server container only.
    trusted_proxy_hosts: list[str] = ["web"]

    @model_validator(mode="after")
    def _check(self) -> "Settings":
        if len(self.secret_key) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters; run the setup script")
        if self.public_demo and not self.demo_mode:
            raise ValueError("PUBLIC_DEMO needs DEMO_MODE to be true")
        if self.public_demo and not self.demo_access_code:
            raise ValueError("PUBLIC_DEMO needs DEMO_ACCESS_CODE to be set")
        return self

    @property
    def signup_is_open(self) -> bool:
        # Closed on a public demo, and whenever demo mode is off (no consent flow yet).
        return self.signup_open and self.demo_mode and not self.public_demo

    @property
    def access_code_required(self) -> bool:
        return self.demo_mode and self.public_demo

    @property
    def banner(self) -> str | None:
        if self.demo_mode and self.public_demo:
            return "This is a demonstration site. It holds sample data only."
        return None


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
