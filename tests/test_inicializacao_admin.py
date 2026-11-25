from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from sqlalchemy import func, select, text

from app.dados.dependencies import hash_senha
from app.dados.models.usuario import Usuario
from app.dados.perfis import PerfilUsuario


DADOS = {"nome": "Primeiro Admin", "email": "primeiro@example.com", "senha": "senha-segura-123"}
ROTA = "/usuario/inicializar-admin"


def test_inicializa_admin_publicamente(client, db):
    resposta = client.post(ROTA, json=DADOS)
    assert resposta.status_code == 201
    corpo = resposta.json()
    assert corpo["tipo"] == "administrador"
    assert corpo["ativo"] is True
    assert "senha" not in corpo and "senha_hash" not in corpo
    usuario = db.get(Usuario, corpo["id"])
    assert hash_senha.verify(DADOS["senha"], usuario.senha_hash)
    assert client.post(ROTA, json=DADOS).status_code == 409


@pytest.mark.parametrize("ativo", [True, False])
def test_usuario_existente_impede_inicializacao(client, criar_usuario, ativo):
    criar_usuario("existente@example.com", ativo=ativo)
    assert client.post(ROTA, json=DADOS).status_code == 409


@pytest.mark.parametrize("alteracoes", [
    {"senha": "curta"},
    {"senha": "        "},
    {"email": "invalido"},
    {"nome": ""},
    {"tipo": "administrador"},
])
def test_validacao_nao_expoe_senha(client, alteracoes):
    dados = DADOS | alteracoes
    resposta = client.post(ROTA, json=dados)
    assert resposta.status_code == 422
    assert dados["senha"] not in resposta.text


def test_lock_liberado_quando_hash_falha(client, monkeypatch, engine_teste):
    with monkeypatch.context() as m:
        def falhar(*args):
            raise RuntimeError("falha simulada")
        m.setattr(hash_senha, "hash", falhar)
        with pytest.raises(RuntimeError, match="falha simulada"):
            client.post(ROTA, json=DADOS)
    with engine_teste.connect() as conexao:
        assert conexao.scalar(text("SELECT IS_FREE_LOCK(CONCAT('helpdesk-bootstrap-', LEFT(SHA2(DATABASE(), 256), 40)))")) == 1
    assert client.post(ROTA, json=DADOS).status_code == 201


def test_requisicoes_concorrentes_usam_conexoes_reais(client, engine_teste):
    barreira = Barrier(2)

    def inicializar(numero):
        barreira.wait(timeout=10)
        return client.post(ROTA, json=DADOS | {"email": f"admin{numero}@example.com"}).status_code

    with ThreadPoolExecutor(max_workers=2) as executor:
        resultados = list(executor.map(inicializar, range(2)))
    assert sorted(resultados) == [201, 409]
    with engine_teste.connect() as conexao:
        assert conexao.scalar(select(func.count()).select_from(Usuario)) == 1
        assert conexao.scalar(select(Usuario.tipo)) == PerfilUsuario.ADMINISTRADOR
        assert conexao.scalar(text("SELECT IS_FREE_LOCK(CONCAT('helpdesk-bootstrap-', LEFT(SHA2(DATABASE(), 256), 40)))")) == 1
