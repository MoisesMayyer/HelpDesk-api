from datetime import UTC, datetime, timedelta

import jwt
import pytest
from sqlalchemy.orm import Session

from app.dados.config import settings
from app.dados.models.usuario import Usuario
from app.rotas.rota_auth import _emitir_token
from app.rotas.rota_usuario import put_perfil
from app.schemas.usuario import UsuarioAtualizacao


def test_login(client, usuario):
    resposta = client.post("/auth/login", data={"username": usuario.email, "password": "senha-segura-123"})

    assert resposta.status_code == 200
    assert resposta.json()["token_type"] == "bearer"
    assert resposta.json()["access_token"]
    assert resposta.json()["refresh_token"]


@pytest.mark.parametrize("caso", ["email_inexistente", "senha_incorreta", "inativo"])
def test_login_credenciais_invalidas(client, usuario, db, caso):
    email, senha = usuario.email, "senha-segura-123"

    if caso == "email_inexistente":
        email = "inexistente@example.com"

    elif caso == "senha_incorreta":
        senha = "incorreta"

    else:
        usuario.ativo = False
        db.commit()
    resposta = client.post("/auth/login", data={"username": email, "password": senha})

    assert resposta.status_code == 401
    assert resposta.json()["detail"] == "E-mail ou senha inválidos."


def test_login_sem_campos(client):
    assert client.post("/auth/login", data={}).status_code == 422


def test_refresh(client, usuario):
    token = _emitir_token(usuario, "refresh")
    resposta = client.post("/auth/refresh", json={"refresh_token": token})

    assert resposta.status_code == 200
    assert resposta.json()["token_type"] == "bearer"
    assert resposta.json()["access_token"]


@pytest.mark.parametrize("caso", ["invalido", "access", "expirado", "inexistente", "inativo"])
def test_refresh_token_invalido(client, usuario, db, caso):
    if caso == "invalido":
        token = "invalido"

    elif caso == "access":
        token = _emitir_token(usuario, "access")

    elif caso == "expirado":
        token = jwt.encode(
            {"sub": str(usuario.id), "tipo": "refresh", "exp": datetime.now(UTC) - timedelta(seconds=1)},
            settings.secret_key,
            algorithm=settings.algorithm,
        )

    elif caso == "inexistente":
        token = jwt.encode(
            {"sub": "2147483647", "tipo": "refresh", "versao": 0, "exp": datetime.now(UTC) + timedelta(minutes=5)},
            settings.secret_key,
            algorithm=settings.algorithm,
        )

    else:
        token = _emitir_token(usuario, "refresh")
        usuario.ativo = False
        db.commit()

    assert client.post("/auth/refresh", json={"refresh_token": token}).status_code == 401


def test_refresh_sem_token(client):
    assert client.post("/auth/refresh", json={}).status_code == 422


@pytest.mark.parametrize("caso", ["ausente", "invalido", "refresh", "inativo"])
def test_perfil_token_invalido(client, usuario, db, caso):
    headers = {}

    if caso != "ausente":
        token = (
            "invalido" if caso == "invalido" else _emitir_token(usuario, "refresh" if caso == "refresh" else "access")
        )
        headers = {"Authorization": f"Bearer {token}"}

    if caso == "inativo":
        usuario.ativo = False
        db.commit()

    assert client.get("/usuario/me", headers=headers).status_code == 401


def test_troca_senha_revoga_tokens(client, usuario):
    login = client.post("/auth/login", data={"username": usuario.email, "password": "senha-segura-123"}).json()

    headers = {"Authorization": f"Bearer {login['access_token']}"}

    assert client.put("/usuario/me", json={"senha": "nova-senha-123"}, headers=headers).status_code == 200
    assert client.get("/usuario/me", headers=headers).status_code == 401
    assert client.post("/auth/refresh", json={"refresh_token": login["refresh_token"]}).status_code == 401
    assert (
        client.post("/auth/login", data={"username": usuario.email, "password": "senha-segura-123"}).status_code == 401
    )

    novo = client.post("/auth/login", data={"username": usuario.email, "password": "nova-senha-123"}).json()
    assert client.get("/usuario/me", headers={"Authorization": f"Bearer {novo['access_token']}"}).status_code == 200
    assert client.post("/auth/refresh", json={"refresh_token": novo["refresh_token"]}).status_code == 200


def test_reativacao_nao_restabelece_tokens(client, usuario, admin, autenticar):
    login = client.post("/auth/login", data={"username": usuario.email, "password": "senha-segura-123"}).json()
    headers_admin = autenticar(admin)
    headers = {"Authorization": f"Bearer {login['access_token']}"}

    assert client.delete(f"/usuario/{usuario.id}", headers=headers_admin).status_code == 204
    assert client.put(f"/usuario/{usuario.id}", json={"ativo": True}, headers=headers_admin).status_code == 200
    assert client.get("/usuario/me", headers=headers).status_code == 401
    assert client.post("/auth/refresh", json={"refresh_token": login["refresh_token"]}).status_code == 401

    novo = client.post("/auth/login", data={"username": usuario.email, "password": "senha-segura-123"}).json()
    assert client.get("/usuario/me", headers={"Authorization": f"Bearer {novo['access_token']}"}).status_code == 200
    assert client.post("/auth/refresh", json={"refresh_token": novo["refresh_token"]}).status_code == 200


@pytest.mark.parametrize("metodo", ["put", "delete"])
def test_troca_senha_concorrente_com_desativacao(client, db, usuario, admin, autenticar, engine_teste, metodo):
    login = client.post("/auth/login", data={"username": usuario.email, "password": "senha-segura-123"}).json()
    headers_admin = autenticar(admin)
    usuario_id = usuario.id

    with Session(engine_teste, autoflush=False) as sessao_senha:
        usuario_antigo = sessao_senha.get(Usuario, usuario_id)
        assert usuario_antigo.versao_token == 0

        if metodo == "put":
            resposta = client.put(f"/usuario/{usuario_id}", json={"ativo": False}, headers=headers_admin)
            assert resposta.status_code == 200

        else:
            assert client.delete(f"/usuario/{usuario_id}", headers=headers_admin).status_code == 204
        assert client.put(f"/usuario/{usuario_id}", json={"ativo": True}, headers=headers_admin).status_code == 200

        intermediario = client.post(
            "/auth/login", data={"username": usuario.email, "password": "senha-segura-123"}
        ).json()

        put_perfil(UsuarioAtualizacao(senha="nova-senha-123"), usuario_antigo, sessao_senha)

    # O client de teste reutiliza uma sessão; requisições reais usam novas sessões.
    db.rollback()
    with Session(engine_teste) as verificacao:
        assert verificacao.get(Usuario, usuario_id).versao_token == 2

    for tokens in (login, intermediario):
        assert (
            client.get("/usuario/me", headers={"Authorization": f"Bearer {tokens['access_token']}"}).status_code == 401
        )
        assert client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]}).status_code == 401
    novo = client.post("/auth/login", data={"username": usuario.email, "password": "nova-senha-123"}).json()

    assert client.get("/usuario/me", headers={"Authorization": f"Bearer {novo['access_token']}"}).status_code == 200
    assert client.post("/auth/refresh", json={"refresh_token": novo["refresh_token"]}).status_code == 200
