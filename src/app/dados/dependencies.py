from collections.abc import Iterator
from typing import Annotated, Literal

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pwdlib import PasswordHash
from sqlalchemy.orm import Session

from app.dados.config import settings
from app.dados.database import SessionLocal
from app.dados.models.usuario import Usuario
from app.dados.perfis import PerfilUsuario


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
hash_senha = PasswordHash.recommended()


def get_db() -> Iterator[Session]:
    with SessionLocal() as db:
        yield db


SessaoDb = Annotated[Session, Depends(get_db)]


def nao_autorizado(mensagem: str) -> HTTPException:
    return HTTPException(
        status.HTTP_401_UNAUTHORIZED,
        mensagem,
        headers={"WWW-Authenticate": "Bearer"},
    )


def usuario_do_token(
    token: str, tipo: Literal["access", "refresh"], db: Session, mensagem: str
) -> Usuario:
    try:
        claims = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm],
            options={"require": ["sub", "exp", "tipo"]},
        )
        usuario_id = int(claims["sub"])
    except (jwt.InvalidTokenError, ValueError, TypeError, OverflowError):
        raise nao_autorizado(mensagem) from None

    if (
        claims["tipo"] != tipo
        or not 0 < usuario_id < 2**63
        or claims["sub"] != str(usuario_id)
    ):
        raise nao_autorizado(mensagem)

    usuario = db.get(Usuario, usuario_id)
    if usuario is None or not usuario.ativo:
        raise nao_autorizado(mensagem)

    return usuario


def get_usuario_atual(
    token: Annotated[str, Depends(oauth2_scheme)], db: SessaoDb
) -> Usuario:
    return usuario_do_token(token, "access", db, "Token de acesso inválido ou expirado.")


UsuarioAtual = Annotated[Usuario, Depends(get_usuario_atual)]


def exigir_administrador(usuario: UsuarioAtual) -> None:
    if usuario.tipo != PerfilUsuario.ADMINISTRADOR:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Operação restrita a administradores.",
        )
