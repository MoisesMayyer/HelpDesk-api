from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

TokenNaoVazio = Annotated[str, Field(min_length=1, pattern=r"^\S+$")]


class TokenAcesso(BaseModel):
    access_token: TokenNaoVazio
    token_type: Literal["bearer"] = "bearer"


class TokenLogin(TokenAcesso):
    refresh_token: TokenNaoVazio


class RenovacaoToken(BaseModel):
    model_config = ConfigDict(extra="forbid")

    refresh_token: TokenNaoVazio
