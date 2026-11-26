from datetime import UTC, datetime, timedelta
from typing import Annotated, Literal

import jwt
from fastapi import APIRouter, Depends, Request, Response
from fastapi.security import OAuth2PasswordRequestForm
from pwdlib.exceptions import PwdlibError
from sqlalchemy import select

from app.dados.config import settings
from app.dados.dependencies import (
    SessaoDb,
    hash_senha,
    nao_autorizado,
    usuario_do_token,
)
from app.dados.models.usuario import Usuario
from app.dados.rate_limit import LIMITE_LOGIN, limiter
from app.rotas.validacao import RotaComValidacaoProtegida
from app.schemas.token import RenovacaoToken, TokenAcesso, TokenLogin

rota_auth = APIRouter(prefix="/auth", tags=["autenticação"], route_class=RotaComValidacaoProtegida)

# Faz uma verificação de custo semelhante mesmo quando o e-mail não existe.
hash_ficticio = hash_senha.hash("senha fictícia para verificação")


def _emitir_token(usuario: Usuario, tipo: Literal["access", "refresh"]) -> str:
    prazo = (
        timedelta(minutes=settings.access_token_expire_minutes)
        if tipo == "access"
        else timedelta(days=settings.refresh_token_expire_days)
    )
    return jwt.encode(
        {
            "sub": str(usuario.id),
            "exp": datetime.now(UTC) + prazo,
            "tipo": tipo,
            "versao": usuario.versao_token,
        },
        settings.secret_key,
        algorithm=settings.algorithm,
    )


@rota_auth.post("/login", response_model=TokenLogin)
@limiter.limit(LIMITE_LOGIN)
def login(
    request: Request,
    response: Response,
    formulario: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: SessaoDb,
) -> TokenLogin:
    usuario = db.scalar(select(Usuario).where(Usuario.email == formulario.username))
    hash_armazenado = usuario.senha_hash if usuario is not None else hash_ficticio

    try:
        senha_valida = hash_senha.verify(formulario.password, hash_armazenado)
    except PwdlibError:
        senha_valida = False

    if usuario is None or not usuario.ativo or not senha_valida:
        raise nao_autorizado("E-mail ou senha inválidos.")

    return TokenLogin(
        access_token=_emitir_token(usuario, "access"),
        refresh_token=_emitir_token(usuario, "refresh"),
    )


@rota_auth.post("/refresh", response_model=TokenAcesso)
def renovar_token(dados: RenovacaoToken, db: SessaoDb) -> TokenAcesso:
    usuario = usuario_do_token(dados.refresh_token, "refresh", db, "Token de renovação inválido ou expirado.")

    return TokenAcesso(access_token=_emitir_token(usuario, "access"))
