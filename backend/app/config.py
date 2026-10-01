from pathlib import Path
from typing import Literal
from pydantic import Field, SecretStr, model_validator, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CARBENTRA_", extra="ignore", hide_input_in_errors=True)
    env: Literal["development", "test", "production"] = "development"
    deployment_mode: Literal["standard", "public_simulation"] = "standard"
    public_demo_id: str | None = Field(default=None, pattern=r"^[a-z0-9][a-z0-9-]{7,47}$")
    public_demo_lifetime_hours: int = Field(default=0, ge=0, le=720)
    public_demo_max_database_mb: int = Field(default=4096, ge=512, le=16384)
    public_demo_visitor_username: str = Field(default="visitor", min_length=1, max_length=80)
    public_demo_operator_username: str = Field(default="simulation-operator", min_length=1, max_length=80)
    public_demo_visitor_password: SecretStr | None = None
    public_demo_operator_password: SecretStr | None = None
    database_url: str = f"sqlite:///{ROOT / 'backend' / 'campus-dev.db'}"
    dev_auth: bool = False
    admin_username: str = "admin"
    admin_password: SecretStr | None = None
    adapter_token: SecretStr | None = None
    adapter_allowed_device_ids: list[str] = Field(default_factory=list)
    allowed_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:8080", "http://127.0.0.1:8080"])
    trusted_hosts: list[str] = Field(default_factory=lambda: ["localhost", "127.0.0.1", "testserver"])
    trusted_proxy_cidrs: list[str] = Field(default_factory=list)
    cookie_secure: bool = False
    session_hours: int = Field(default=8, ge=1, le=24)
    seed_demo: bool = False
    auto_migrate: bool = True
    simulation_enabled: bool = False
    worker_enabled: bool = True
    physical_dispatch_enabled: bool = False
    physical_release_ids: list[str] = Field(default_factory=list)
    worker_interval_seconds: float = Field(default=0.25, ge=0.1, le=1)
    simulation_batch_size: int = Field(default=25, ge=1, le=100)
    control_batch_size: int = Field(default=32, ge=1, le=128)
    simulation_interval_seconds: int = Field(default=30, ge=5, le=300)
    classroom_simulation_interval_seconds: int = Field(default=60, ge=30, le=900)
    analysis_interval_seconds: float = Field(default=1.0, ge=0.1, le=30)
    forecast_max_pending: int = Field(default=128, ge=8, le=1000)
    forecast_max_cached_runs: int = Field(default=4096, ge=128, le=50000)
    stale_after_seconds: int = Field(default=120, ge=10, le=3600)
    offline_after_seconds: int = Field(default=600, ge=30, le=86400)
    spatial_seed_path: Path = ROOT / "packages" / "spatial" / "dist" / "seed.json"
    spatial_manifest_path: Path = ROOT / "packages" / "spatial" / "dist" / "manifest.json"
    product_asset_dir: Path = ROOT / "packages" / "product" / "dist"
    max_body_bytes: int = 2 * 1024 * 1024
    enable_docs: bool = True

    @field_validator("physical_dispatch_enabled", mode="before")
    @classmethod
    def explicit_physical_flag(cls, value):
        if type(value) is bool:
            return value
        if value in ("true", "false"):
            return value == "true"
        raise ValueError("Physical dispatch flag accepts only explicit true/false")

    @model_validator(mode="after")
    def validate_deployment(self):
        import ipaddress
        for cidr in self.trusted_proxy_cidrs:
            ipaddress.ip_network(cidr)
        if self.offline_after_seconds <= self.stale_after_seconds:
            raise ValueError("offline_after_seconds must exceed stale_after_seconds")
        if "*" in self.allowed_origins or "*" in self.trusted_hosts:
            raise ValueError("Wildcard origins and hosts are prohibited")
        if self.env == "production":
            if self.dev_auth:
                raise ValueError("Development authentication is prohibited in production")
            if not self.database_url.startswith("postgresql"):
                raise ValueError("Production requires PostgreSQL; SQLite is development/test only")
            if not self.cookie_secure:
                raise ValueError("Production session cookies must be Secure")
            if self.auto_migrate:
                raise ValueError("Run explicit migrations before production startup")
            if self.seed_demo:
                raise ValueError("Demo seeding is prohibited in production")
            if self.simulation_enabled and self.deployment_mode != "public_simulation":
                raise ValueError("Production simulation requires the isolated public_simulation deployment mode")
            if not self.allowed_origins or any(not x.startswith("https://") for x in self.allowed_origins):
                raise ValueError("Production requires explicit HTTPS origins")
        if self.deployment_mode == "public_simulation":
            from sqlalchemy.engine import make_url
            url = make_url(self.database_url)
            if self.env != "production" or not self.public_demo_id:
                raise ValueError("Public simulation requires production security and an explicit deployment ID")
            if url.database != "carbentra_public_demo" or url.username != "carbentra_public_demo":
                raise ValueError("Public simulation requires its dedicated database and non-production application role")
            if not self.simulation_enabled or self.worker_enabled:
                raise ValueError("Public simulation requires explicit simulation and supervised separate workers")
            if self.physical_dispatch_enabled or self.physical_release_ids or self.adapter_token or self.adapter_allowed_device_ids:
                raise ValueError("Public simulation permanently prohibits physical dispatch and external adapters")
            if len({self.admin_username, self.public_demo_visitor_username, self.public_demo_operator_username}) != 3:
                raise ValueError("Public simulation administrator, operator and visitor must be separate accounts")
            for secret in (self.public_demo_visitor_password, self.public_demo_operator_password):
                if secret and (len(secret.get_secret_value()) < 20 or secret.get_secret_value().lower() in {
                    "development-only", "change-me-please-now", "your-password-here"}):
                    raise ValueError("Public simulation passwords must be independently supplied and >=20 characters")
        if self.admin_password:
            value = self.admin_password.get_secret_value()
            if len(value) < 16 or value.lower() in {"development-only", "change-me-please-now", "your-password-here"}:
                raise ValueError("Admin password must be operator-provided, non-placeholder and >=16 characters")
        if self.adapter_token:
            token = self.adapter_token.get_secret_value()
            if len(token) < 32 or not token.isascii() or any(ord(ch) < 33 or ord(ch) > 126 for ch in token):
                raise ValueError("Operator-provided adapter token must contain >=32 printable non-whitespace ASCII characters")
        return self
