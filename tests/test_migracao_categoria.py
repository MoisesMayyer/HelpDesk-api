from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError

import app.dados.database as database


@pytest.fixture
def banco_migracao(engine_teste, monkeypatch):
    nome = f"test_migracao_{uuid4().hex}"
    servidor = create_engine(engine_teste.url.set(database=None))
    with servidor.begin() as conexao:
        conexao.execute(text(f"CREATE DATABASE `{nome}` CHARACTER SET utf8mb4"))
    engine = create_engine(engine_teste.url.set(database=nome))
    monkeypatch.setattr(database, "engine", engine)
    try:
        yield engine, Config("alembic.ini")
    finally:
        engine.dispose()
        with servidor.begin() as conexao:
            conexao.execute(text(f"DROP DATABASE `{nome}`"))
        servidor.dispose()


@pytest.mark.parametrize("com_chamados", [False, True])
def test_migracao_preserva_chamados_e_aplica_restricoes(banco_migracao, com_chamados):
    engine, config = banco_migracao
    command.upgrade(config, "c2f3d4e5f6a7")
    with engine.begin() as conexao:
        # Mesmo nome e categoria inativa não devem ser confundidos com a nova.
        conexao.execute(text("INSERT INTO categorias (nome, ativo) VALUES ('Geral', 0)"))
        if com_chamados:
            conexao.execute(text(
                "INSERT INTO usuarios (id, nome, email, senha_hash, tipo, ativo, versao_token) "
                "VALUES (1, 'Pessoa', 'pessoa@example.com', 'hash', 'funcionario', 1, 0)"
            ))
            conexao.execute(text(
                "INSERT INTO chamados (id, id_usuario, titulo, descricao, aberto_em, status, prioridade) "
                "VALUES (1, 1, 'Primeiro', 'Descrição 1', '2024-01-01', 'aberto', 'alta'), "
                "(2, 1, 'Segundo', 'Descrição 2', '2024-01-02', 'fechado', 'baixa')"
            ))

    command.upgrade(config, "head")
    with engine.connect() as conexao:
        categorias = conexao.execute(text("SELECT id, nome, ativo FROM categorias ORDER BY id")).all()
        chamados = conexao.execute(text(
            "SELECT id, titulo, descricao, status, prioridade, id_categoria FROM chamados ORDER BY id"
        )).all()
        assert categorias[0][1:] == ("Geral", 0)
        if com_chamados:
            assert len(categorias) == 2 and categorias[1][1:] == ("Geral", 1)
            assert chamados == [
                (1, "Primeiro", "Descrição 1", "aberto", "alta", categorias[1].id),
                (2, "Segundo", "Descrição 2", "fechado", "baixa", categorias[1].id),
            ]
        else:
            assert len(categorias) == 1 and chamados == []
    coluna = next(c for c in inspect(engine).get_columns("chamados") if c["name"] == "id_categoria")
    assert not coluna["nullable"] and coluna["default"] is None
    assert any(fk["constrained_columns"] == ["id_categoria"] and fk["referred_table"] == "categorias"
               for fk in inspect(engine).get_foreign_keys("chamados"))
    if com_chamados:
        with pytest.raises(IntegrityError), engine.begin() as conexao:
            conexao.execute(text("UPDATE chamados SET id_categoria = 999999 WHERE id = 1"))
        with pytest.raises(IntegrityError), engine.begin() as conexao:
            conexao.execute(text("UPDATE chamados SET id_categoria = NULL WHERE id = 1"))

    command.downgrade(config, "c2f3d4e5f6a7")
    with engine.connect() as conexao:
        assert conexao.execute(text("SELECT COUNT(*) FROM chamados")).scalar_one() == (2 if com_chamados else 0)
        assert conexao.execute(text("SELECT COUNT(*) FROM categorias")).scalar_one() == (2 if com_chamados else 1)
