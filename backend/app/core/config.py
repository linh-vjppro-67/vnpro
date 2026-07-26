from functools import lru_cache
from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "VNPRO Enterprise Hub API"
    environment: str = "development"
    database_url: str = "sqlite:///./pro_erp.db"
    secret_key: str = "local-development-secret-key-change-me"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 480
    upload_dir: str = "./uploads"
    max_upload_bytes: int = 10 * 1024 * 1024
    cors_origins: list[str] | str = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost",
        "http://127.0.0.1",
    ]

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors(cls, value):
        if isinstance(value, str):
            parsed = [item.strip() for item in value.split(",") if item.strip()]
        else:
            parsed = list(value or [])

        return parsed

    @model_validator(mode="after")
    def validate_production_security(self):
        if self.environment.lower() == "production" and (
            len(self.secret_key) < 32 or "change-me" in self.secret_key or "replace-with" in self.secret_key
        ):
            raise ValueError("SECRET_KEY production phải là chuỗi ngẫu nhiên tối thiểu 32 ký tự")
        return self


@lru_cache

def get_settings() -> Settings:
    return Settings()


settings = get_settings()
