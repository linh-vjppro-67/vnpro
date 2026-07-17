from functools import lru_cache
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "PRO Enterprise Hub API"
    environment: str = "development"
    database_url: str = "sqlite:///./pro_erp.db"
    secret_key: str = "local-development-secret-key-change-me"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 480
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

        local_origins = [
            "http://localhost",
            "http://localhost:5173",
            "http://127.0.0.1",
            "http://127.0.0.1:5173",
        ]
        for origin in local_origins:
            if origin not in parsed:
                parsed.append(origin)
        return parsed


@lru_cache

def get_settings() -> Settings:
    return Settings()


settings = get_settings()
