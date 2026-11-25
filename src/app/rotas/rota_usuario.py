from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.dados.dependencies import (
    SessaoDb,
    UsuarioAtual,
    exigir_administrador,
    hash_senha,
)
from app.dados.models.usuario import Usuario
from app.dados.perfis import PerfilUsuario
from app.rotas.validacao import RotaComValidacaoProtegida
from app.schemas.usuario import (
    UsuarioAtualizacao,
    UsuarioAtualizacaoAdmin,
    UsuarioCriacao,
    UsuarioLeitura,
)

rota_usuario = APIRouter(
    prefix="/usuario", tags=["usuario"], route_class=RotaComValidacaoProtegida
)
SomenteAdmin = [Depends(exigir_administrador)]
UsuarioId = Annotated[int, Path(gt=0, le=2**31 - 1)]


def _buscar_usuario(usuario_id: int, db: Session) -> Usuario:
    usuario = db.get(Usuario, usuario_id)

    if usuario is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Usuário não encontrado.")
    return usuario


def _alterar_acesso(
    usuario_id: int,
    db: Session,
    *,
    tipo: PerfilUsuario | None = None,
    ativo: bool | None = None,
) -> Usuario:
    # Bloqueia o conjunto em ordem fixa até o commit para evitar remoções concorrentes.

    administradores = db.scalars(
        select(Usuario.id)
        .where(Usuario.tipo == PerfilUsuario.ADMINISTRADOR, Usuario.ativo.is_(True))
        .order_by(Usuario.id)
        .with_for_update()
    ).all()

    # Usa uma leitura atual mesmo se a autenticação já carregou esse usuário.
    usuario = db.get(Usuario, usuario_id, populate_existing=True, with_for_update=True)
    if usuario is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Usuário não encontrado.")

    remove_admin = ativo is False or (
        tipo is not None and tipo != PerfilUsuario.ADMINISTRADOR
    )
    if remove_admin and len(administradores) == 1 and administradores[0] == usuario_id:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "O sistema precisa manter pelo menos um administrador ativo.",
        )

    if tipo is not None:
        usuario.tipo = tipo
    if ativo is not None:
        usuario.ativo = ativo
    db.commit()
    return usuario


def _salvar_usuario(usuario: Usuario, db: Session) -> Usuario:
    email, usuario_id = usuario.email, usuario.id

    try:
        db.commit()

    except IntegrityError:
        db.rollback()
        consulta = select(Usuario.id).where(Usuario.email == email)

        if usuario_id is not None:
            consulta = consulta.where(Usuario.id != usuario_id)

        if db.scalar(consulta) is not None:
            raise HTTPException(
                status.HTTP_409_CONFLICT, "E-mail já cadastrado."
            ) from None
        raise

    db.refresh(usuario)
    return usuario

@rota_usuario.patch("/admin", response_model=UsuarioLeitura)
def fazer_admin(usuario: UsuarioAtual, db: SessaoDb) -> Usuario:
    # rota funcional apenas para facilitar a criação de ADMIN em projetos reais de produção nao se deve criar rotas assim. Caso utilize esse projeto remova essa rota
    usuario.tipo = PerfilUsuario.ADMINISTRADOR
    return _salvar_usuario(usuario, db)


@rota_usuario.get("", response_model=list[UsuarioLeitura], dependencies=SomenteAdmin)
def get_usuarios(db: SessaoDb) -> list[Usuario]:
    return list(db.scalars(select(Usuario).order_by(Usuario.id)))


@rota_usuario.get("/me", response_model=UsuarioLeitura)
def get_perfil(usuario: UsuarioAtual) -> Usuario:
    return usuario


@rota_usuario.get(
    "/{usuario_id}", response_model=UsuarioLeitura, dependencies=SomenteAdmin
)
def get_usuario(usuario_id: UsuarioId, db: SessaoDb) -> Usuario:
    return _buscar_usuario(usuario_id, db)


@rota_usuario.post(
    "",
    response_model=UsuarioLeitura,
    status_code=status.HTTP_201_CREATED,
    dependencies=SomenteAdmin,
)
def post_usuario(dados: UsuarioCriacao, db: SessaoDb) -> Usuario:
    usuario = Usuario(
        nome=dados.nome,
        email=dados.email,
        senha_hash=hash_senha.hash(dados.senha.get_secret_value()),
        tipo=PerfilUsuario.FUNCIONARIO,
    )
    db.add(usuario)
    return _salvar_usuario(usuario, db)


@rota_usuario.put("/me", response_model=UsuarioLeitura)
def put_perfil(
    dados: UsuarioAtualizacao, usuario: UsuarioAtual, db: SessaoDb
) -> Usuario:

    if dados.nome is not None:
        usuario.nome = dados.nome

    if dados.email is not None:
        usuario.email = dados.email

    if dados.senha is not None:
        usuario.senha_hash = hash_senha.hash(dados.senha.get_secret_value())
    return _salvar_usuario(usuario, db)


@rota_usuario.put(
    "/{usuario_id}", response_model=UsuarioLeitura, dependencies=SomenteAdmin
)
def put_usuario(
    usuario_id: UsuarioId, dados: UsuarioAtualizacaoAdmin, db: SessaoDb
) -> Usuario:

    usuario = _alterar_acesso(usuario_id, db, tipo=dados.tipo, ativo=dados.ativo)
    db.refresh(usuario)
    return usuario


@rota_usuario.delete(
    "/{usuario_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=SomenteAdmin
)
def delete_usuario(usuario_id: UsuarioId, db: SessaoDb) -> None:
    _alterar_acesso(usuario_id, db, ativo=False)
