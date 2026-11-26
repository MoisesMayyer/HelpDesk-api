"""Testes das rotas de chamados."""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.dados.database import Base
from app.dados.dependencies import get_db, get_usuario_atual
from app.dados.models import Categoria, Chamados, HistoricoChamado, Usuario
from app.dados.perfis import PerfilUsuario
from app.main import app
from app.rotas.rota_chamados import assumir_chamado, rota_chamados


def test_chamados_exigem_autenticacao():
    with TestClient(app) as client:
        assert client.get("/chamados").status_code == 401


@pytest.fixture
def ambiente():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)

    @event.listens_for(engine, "connect")
    def habilitar_fk(conexao, _):
        conexao.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add_all(
            [
                Usuario(id=1, nome="Solicitante", email="a@teste.com", senha_hash="x", tipo=PerfilUsuario.FUNCIONARIO),
                Usuario(id=2, nome="Outro", email="b@teste.com", senha_hash="x", tipo=PerfilUsuario.FUNCIONARIO),
                Usuario(id=3, nome="Técnico", email="c@teste.com", senha_hash="x", tipo=PerfilUsuario.TECNICO),
                Usuario(id=4, nome="Técnico 2", email="d@teste.com", senha_hash="x", tipo=PerfilUsuario.TECNICO),
                Usuario(id=5, nome="Admin", email="e@teste.com", senha_hash="x", tipo=PerfilUsuario.ADMINISTRADOR),
                Usuario(
                    id=6, nome="Inativo", email="f@teste.com", senha_hash="x", tipo=PerfilUsuario.TECNICO, ativo=False
                ),
                Categoria(id=1, nome="Hardware", ativo=True),
                Categoria(id=2, nome="Rede", ativo=True),
                Categoria(id=3, nome="Inativa", ativo=False),
            ]
        )
        db.commit()

    app = FastAPI()
    app.include_router(rota_chamados)

    def db_teste():
        with Session(engine) as db:
            yield db

    def usuario_teste(x_usuario: int = Header(), db: Session = Depends(get_db)):
        return db.get(Usuario, x_usuario)

    app.dependency_overrides[get_db] = db_teste
    app.dependency_overrides[get_usuario_atual] = usuario_teste

    with TestClient(app) as client:
        client.headers["x-usuario"] = "1"
        yield client, engine
    engine.dispose()


def usuario(client, identificador):
    client.headers["x-usuario"] = str(identificador)


def criar(client, categoria=1):
    resposta = client.post(
        "/chamados", json={"titulo": "Impressora", "descricao": "Não imprime", "id_categoria": categoria}
    )

    assert resposta.status_code == 201, resposta.text
    return resposta.json()


def test_fluxo_devolucao_fechamento_e_auditoria(ambiente):
    client, _ = ambiente
    chamado = criar(client)
    cid = chamado["id"]
    url = f"/chamados/{cid}"

    assert (chamado["status"], chamado["prioridade"], chamado["id_usuario"]) == ("aberto", "nao_classificada", 1)

    usuario(client, 3)

    assert client.put(url + "/prioridade", json={"prioridade": "alta"}).status_code == 200
    assert client.put(url + "/categoria", json={"id_categoria": 2}).status_code == 200
    assert client.post(url + "/assumir").json()["status"] == "em_andamento"
    assert client.post(url + "/resolver", json={"resolucao": "Reiniciado"}).json()["status"] == "resolvido"

    usuario(client, 1)

    assert client.get(url + "/resolucao").json()["resolucao"] == "Reiniciado"
    assert client.post(url + "/devolver", json={"motivo": "Persiste"}).json()["status"] == "em_andamento"

    usuario(client, 5)

    resposta = client.put(url + "/responsavel", json={"id_tecnico": 4})

    assert resposta.status_code == 200 and resposta.json()["id_tecnico"] == 4

    usuario(client, 4)

    assert client.post(url + "/resolver", json={"resolucao": "Corrigido"}).status_code == 200

    usuario(client, 1)

    assert client.get(url + "/resolucao").json()["resolucao"] == "Corrigido"

    fechado = client.post(url + "/fechar")

    assert fechado.status_code == 200
    assert fechado.json()["status"] == "fechado" and fechado.json()["concluido_em"]

    usuario(client, 5)
    historico = client.get(url + "/historico").json()

    assert [e["tipo"] for e in historico] == [
        "criacao",
        "prioridade",
        "categoria",
        "atribuicao",
        "status",
        "status",
        "resolucao",
        "status",
        "devolucao",
        "redistribuicao",
        "status",
        "resolucao",
        "status",
        "fechamento",
    ]
    assert (historico[1]["anterior"], historico[1]["novo"], historico[1]["id_usuario"]) == (
        "nao_classificada",
        "alta",
        3,
    )
    assert (historico[2]["anterior"], historico[2]["novo"]) == ("1", "2")
    assert (historico[9]["anterior"], historico[9]["novo"], historico[9]["id_usuario"]) == ("3", "4", 5)
    assert all(e["id_chamado"] == cid and e["criado_em"] for e in historico)


def test_aguardar_resposta_e_retomar(ambiente):
    client, _ = ambiente
    url = f"/chamados/{criar(client)['id']}"

    usuario(client, 3)

    assert client.post(url + "/aguardar-resposta").status_code == 403
    assert client.post(url + "/assumir").status_code == 200
    assert client.post(url + "/retomar").status_code == 409

    for perfil in (1, 4, 5):
        usuario(client, perfil)
        assert client.post(url + "/aguardar-resposta").status_code == 403

    usuario(client, 3)
    resposta = client.post(url + "/aguardar-resposta")

    assert resposta.status_code == 200
    assert resposta.json()["status"] == "aguardando_resposta"
    assert client.post(url + "/aguardar-resposta").status_code == 409
    assert client.post(url + "/resolver", json={"resolucao": "Corrigido"}).status_code == 409
    for perfil in (1, 4, 5):
        usuario(client, perfil)
        assert client.post(url + "/retomar").status_code == 403

    usuario(client, 3)
    resposta = client.post(url + "/retomar")

    assert resposta.status_code == 200
    assert resposta.json()["status"] == "em_andamento"
    assert client.post(url + "/retomar").status_code == 409

    usuario(client, 5)
    historico = client.get(url + "/historico").json()
    mudancas = [(e["anterior"], e["novo"], e["id_usuario"]) for e in historico if e["tipo"] == "status"]

    assert mudancas == [
        ("aberto", "em_andamento", 3),
        ("em_andamento", "aguardando_resposta", 3),
        ("aguardando_resposta", "em_andamento", 3),
    ]

    usuario(client, 3)
    assert client.post(url + "/resolver", json={"resolucao": "Corrigido"}).status_code == 200


def test_permissoes_e_comentarios(ambiente):
    client, _ = ambiente
    cid = criar(client)["id"]
    url = f"/chamados/{cid}"

    assert client.post(url + "/comentarios", json={"conteudo": "x"}).status_code == 403
    assert client.get(url + "/comentarios").status_code == 403
    assert client.get(url + "/historico").status_code == 403
    assert client.put(url + "/prioridade", json={"prioridade": "alta"}).status_code == 403

    usuario(client, 2)

    assert client.get(url).status_code == 404
    assert client.get(url + "/resolucao").status_code == 404
    assert client.get("/chamados").json() == []

    usuario(client, 5)

    assert client.post(url + "/assumir").status_code == 403
    assert client.put(url + "/categoria", json={"id_categoria": 2}).status_code == 403
    assert client.post(url + "/comentarios", json={"conteudo": "x"}).status_code == 403

    usuario(client, 3)
    comentario = client.post(url + "/comentarios", json={"conteudo": "  Observação técnica  "})

    assert comentario.status_code == 201
    assert comentario.json()["conteudo"] == "Observação técnica"
    assert comentario.json()["id_usuario"] == 3 and comentario.json()["id_chamado"] == cid
    assert client.get(url + "/historico").status_code == 403
    assert client.get(url + "/comentarios").json() == [comentario.json()]

    usuario(client, 5)

    assert client.get(url + "/comentarios").json() == [comentario.json()]

    usuario(client, 3)

    assert client.post(url + "/assumir").status_code == 200

    usuario(client, 4)

    assert client.post(url + "/resolver", json={"resolucao": "ok"}).status_code == 403

    usuario(client, 3)

    assert client.post(url + "/resolver", json={"resolucao": "ok"}).status_code == 200
    assert client.post(url + "/fechar").status_code == 403
    assert client.post(url + "/devolver", json={"motivo": "x"}).status_code == 403


def test_filtros_ordenacao_paginacao_e_visibilidade(ambiente):
    client, _ = ambiente
    primeiro = criar(client, 1)["id"]
    segundo = criar(client, 2)["id"]

    usuario(client, 2)

    terceiro = criar(client, 2)["id"]
    usuario(client, 3)

    assert client.put(f"/chamados/{segundo}/prioridade", json={"prioridade": "alta"}).status_code == 200
    assert client.post(f"/chamados/{segundo}/assumir").status_code == 200

    def ids(params):
        resposta = client.get("/chamados", params=params)
        assert resposta.status_code == 200
        return [item["id"] for item in resposta.json()]

    assert ids({"status": "em_andamento", "prioridade": "alta", "id_categoria": 2, "id_tecnico": 3}) == [segundo]
    assert ids({"id_categoria": 2, "ordem": "id", "direcao": "asc"}) == [segundo, terceiro]
    assert ids({"ordem": "id", "direcao": "asc", "limite": 1, "deslocamento": 1}) == [segundo]

    usuario(client, 1)

    assert ids({"ordem": "id", "direcao": "asc"}) == [primeiro, segundo]

    usuario(client, 5)

    assert ids({"ordem": "id", "direcao": "desc"}) == [terceiro, segundo, primeiro]


def test_erros_e_operacoes_sem_alteracao_nao_geram_auditoria(ambiente):
    client, engine = ambiente
    dados = {"titulo": "Teste", "descricao": "Problema", "id_categoria": 3}

    assert client.post("/chamados", json=dados).status_code == 422
    assert client.post("/chamados", json=dados | {"id_categoria": 999}).status_code == 422
    assert client.post("/chamados", json=dados | {"id_categoria": 1, "status": "fechado"}).status_code == 422
    assert client.get("/chamados/0").status_code == 422
    assert client.get("/chamados/999").status_code == 404
    assert client.get("/chamados", params={"limite": 0}).status_code == 422
    assert client.get("/chamados", params={"status": "invalido"}).status_code == 422

    cid = criar(client)["id"]
    url = f"/chamados/{cid}"

    assert client.post(url + "/fechar").status_code == 409
    assert client.post(url + "/devolver", json={"motivo": "x"}).status_code == 409

    usuario(client, 3)

    assert client.post(url + "/resolver", json={"resolucao": "x"}).status_code == 403
    assert client.post(url + "/comentarios", json={"conteudo": " "}).status_code == 422
    assert client.put(url + "/categoria", json={"id_categoria": 3}).status_code == 422
    assert client.put(url + "/prioridade", json={"prioridade": "nao_classificada"}).status_code == 200
    assert client.post(url + "/assumir").status_code == 200

    usuario(client, 4)

    assert client.post(url + "/assumir").status_code == 409

    usuario(client, 5)

    for tecnico in (1, 6, 999):
        assert client.put(url + "/responsavel", json={"id_tecnico": tecnico}).status_code == 422
    assert client.put(url + "/responsavel", json={"id_tecnico": 3}).status_code == 200
    with Session(engine) as db:
        assert [h.tipo for h in db.scalars(select(HistoricoChamado).order_by(HistoricoChamado.id))] == [
            "criacao",
            "atribuicao",
            "status",
        ]


def test_assumir_concorrente_mysql(db, engine_teste):
    categoria = Categoria(nome="Rede")
    solicitante = Usuario(nome="Solicitante", email="sol@teste.com", senha_hash="x", tipo=PerfilUsuario.FUNCIONARIO)
    tecnicos = [
        Usuario(nome=f"Técnico {i}", email=f"tec{i}@teste.com", senha_hash="x", tipo=PerfilUsuario.TECNICO)
        for i in range(2)
    ]

    db.add_all([categoria, solicitante, *tecnicos])
    db.flush()
    chamado = Chamados(titulo="Teste", descricao="Falha", id_categoria=categoria.id, id_usuario=solicitante.id)
    db.add(chamado)
    db.commit()

    chamado_id = chamado.id
    ids = [tecnico.id for tecnico in tecnicos]
    # Encerra o snapshot REPEATABLE READ antes das alterações concorrentes.

    db.rollback()
    barreira = Barrier(2)

    def assumir(tecnico_id):
        with Session(engine_teste) as sessao:
            tecnico = sessao.get(Usuario, tecnico_id)
            barreira.wait(timeout=10)
            try:
                assumir_chamado(chamado_id, sessao, tecnico)
                return 200
            except HTTPException as erro:
                return erro.status_code

    with ThreadPoolExecutor(max_workers=2) as executor:
        assert sorted(executor.map(assumir, ids)) == [200, 409]
    db.expire_all()

    assert db.get(Chamados, chamado_id).id_tecnico in ids
    assert (
        len(
            list(
                db.scalars(
                    select(HistoricoChamado).where(
                        HistoricoChamado.id_chamado == chamado_id, HistoricoChamado.tipo == "atribuicao"
                    )
                )
            )
        )
        == 1
    )
