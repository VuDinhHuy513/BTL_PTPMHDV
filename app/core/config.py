"""Cấu hình đọc từ biến môi trường / file .env"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    PROJECT_NAME: str = "Hotel PMS API"
    API_V1_PREFIX: str = "/api/v1"

    DATABASE_URL: str = "sqlite:///./hotel_pms.db"

    JWT_SECRET: str = "change-me"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Quy tắc nghiệp vụ
    VAT_RATE: float = 0.08              # thuế VAT 8%
    CANCEL_FREE_BEFORE_DAYS: int = 2    # hủy miễn phí trước N ngày

    @property
    def is_postgres(self) -> bool:
        return self.DATABASE_URL.startswith("postgresql")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
