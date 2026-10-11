from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    model_dir: Path = REPO_ROOT / "models"
    serving_dir: Path = REPO_ROOT / "data" / "serving"
    queue_model_version: str = "v1.0.0"
    recon_model_version: str = "v1.0.0"
    allowed_origins: str = "http://localhost:3000"   # comma-separated
    log_level: str = "INFO"
    max_recon_hours: int = 6


settings = Settings()
