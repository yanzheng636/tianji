"""环境配置。启动即校验，缺关键项直接崩（fail-fast）。"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    env: str = "development"
    port: int = 3001
    web_origin: str = "http://localhost:5173"

    database_url: str = "postgresql+asyncpg://tianji:tianji@localhost:5433/tianji"
    redis_url: str = "redis://localhost:6380"

    jwt_secret: str = "dev-only-secret-change-me-in-production-0123456789"
    jwt_expires_days: int = 30

    # Quota（0 表示无限；当前求签默认不限次数）
    qian_daily_limit: int = Field(default=0, ge=0)

    # LLM
    llm_provider: str = "mock"  # mock | deepseek
    deepseek_api_key: str | None = None
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"

    # Embedding
    embedding_provider: str = "none"  # none | openai
    embedding_api_key: str | None = None
    embedding_base_url: str | None = None
    embedding_model: str | None = None

    # SMS
    sms_provider: str = "console"  # console | aliyun
    aliyun_sms_access_key_id: str | None = None
    aliyun_sms_access_key_secret: str | None = None
    aliyun_sms_sign_name: str | None = None
    aliyun_sms_template_code: str | None = None
    aliyun_sms_region_id: str = "cn-hangzhou"
    aliyun_sms_endpoint: str = "https://dysmsapi.aliyuncs.com/"

    # Moderation
    moderation_provider: str = "keyword"  # keyword | aliyun
    aliyun_green_access_key_id: str | None = None
    aliyun_green_access_key_secret: str | None = None

    # Payment
    payment_provider: str = "mock"  # mock | wechat | alipay
    payment_notify_base_url: str = "http://localhost:3001"
    wechat_app_id: str | None = None
    wechat_mch_id: str | None = None
    wechat_api_v3_key: str | None = None
    wechat_cert_serial_no: str | None = None
    wechat_private_key_path: str | None = None
    alipay_app_id: str | None = None
    alipay_private_key: str | None = None
    alipay_public_key: str | None = None

    @property
    def is_dev(self) -> bool:
        return self.env == "development"

    @property
    def is_prod(self) -> bool:
        return self.env == "production"

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.web_origin.split(",") if o.strip()]

    @model_validator(mode="after")
    def validate_production(self) -> Settings:
        if self.is_prod:
            if self.jwt_secret == "dev-only-secret-change-me-in-production-0123456789":
                raise ValueError("生产环境必须设置随机 JWT_SECRET")
            if self.sms_provider != "aliyun":
                raise ValueError("生产环境必须使用 SMS_PROVIDER=aliyun")
            if not all(
                (
                    self.aliyun_sms_access_key_id,
                    self.aliyun_sms_access_key_secret,
                    self.aliyun_sms_sign_name,
                    self.aliyun_sms_template_code,
                )
            ):
                raise ValueError("生产环境阿里云短信凭证、签名和模板不能为空")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
