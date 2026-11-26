from pathlib import Path
from typing import Literal

from pydantic import Field, PositiveInt, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILE = Path(__file__).resolve().parents[3] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
        hide_input_in_errors=True,
    )

    secret_key: str = Field(repr=False)
    algorithm: Literal["HS256"] = "HS256"
    access_token_expire_minutes: PositiveInt = 30
    refresh_token_expire_days: PositiveInt = 7
    database_url: str = Field(min_length=1)

    CORS_ORIGINS: str = "http://localhost:8800,https://moisesmayyer.github.io"

    @field_validator("secret_key")
    @classmethod
    def validar_chave_jwt(cls, chave: str) -> str:
        if not chave.strip() or len(chave.encode("utf-8")) < 32:
            raise ValueError("SECRET_KEY deve ser uma chave aleatória de ao menos 32 bytes.")

        return chave

    @property
    def cors_origins(self) -> list[str]:
        return [origem.strip() for origem in self.CORS_ORIGINS.split(",") if origem.strip()]


settings = Settings()  # type: ignore[call-arg]  # valores vindos do .env
