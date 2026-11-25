import os
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, delete, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from app.dados.config import settings
from app.dados.database import Base
from app.dados.dependencies import get_db, hash_senha
from app.dados.models.usuario import Usuario
from app.dados.perfis import PerfilUsuario
from app.main import app


@pytest.fixture(scope="session")
def engine_teste():
    url = make_url(os.getenv("TEST_DATABASE_URL", settings.database_url))
    if url.get_backend_name() != "mysql":
        raise pytest.UsageError("TEST_DATABASE_URL deve apontar para um servidor MySQL.")

    # O nome aleatório impede qualquer alteração no banco informado na URL.
    nome = f"test_helpdesk_{uuid4().hex}"
    servidor = create_engine(url.set(database=None))
    criado = False
    engine = None
    try:
        with servidor.begin() as conexao:
            conexao.execute(text(f"CREATE DATABASE `{nome}` CHARACTER SET utf8mb4"))
        criado = True
        engine = create_engine(url.set(database=nome))
        Base.metadata.create_all(engine)
        yield engine
    finally:
        if engine is not None:
            engine.dispose()
        if criado:
            with servidor.begin() as conexao:
                conexao.execute(text(f"DROP DATABASE `{nome}`"))
        servidor.dispose()


@pytest.fixture
def db(engine_teste):
    fabrica = sessionmaker(bind=engine_teste, autoflush=False)
    with fabrica() as sessao:
        yield sessao
        sessao.rollback()
    with engine_teste.begin() as conexao:
        for tabela in reversed(Base.metadata.sorted_tables):
            conexao.execute(delete(tabela))


@pytest.fixture
def client(db):
    def substituir_db():
        yield db

    app.dependency_overrides[get_db] = substituir_db
    try:
        with TestClient(app) as cliente:
            yield cliente
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.fixture(scope="session")
def senha_hash():
    return hash_senha.hash("senha-segura-123")


@pytest.fixture
def criar_usuario(db, senha_hash):
    def criar(email, tipo=PerfilUsuario.FUNCIONARIO, ativo=True):
        usuario = Usuario(nome="Usuário Teste", email=email, senha_hash=senha_hash,
                          tipo=tipo, ativo=ativo)
        db.add(usuario)
        db.commit()
        db.refresh(usuario)
        return usuario
    return criar


@pytest.fixture
def usuario(criar_usuario):
    return criar_usuario("usuario@example.com")


@pytest.fixture
def outro_usuario(criar_usuario):
    return criar_usuario("outro@example.com")


@pytest.fixture
def admin(criar_usuario):
    return criar_usuario("admin@example.com", PerfilUsuario.ADMINISTRADOR)


@pytest.fixture
def autenticar(client):
    def autenticar_usuario(usuario):
        resposta = client.post("/auth/login", data={"username": usuario.email, "password": "senha-segura-123"})
        assert resposta.status_code == 200
        return {"Authorization": f"Bearer {resposta.json()['access_token']}"}
    return autenticar_usuario
