import pytest

from app.dados.models.categoria import Categoria
from app.dados.perfis import PerfilUsuario


@pytest.fixture
def categoria(db):
    categoria = Categoria(nome="Hardware")
    db.add(categoria)
    db.commit()
    db.refresh(categoria)
    return categoria


@pytest.mark.parametrize(
    ("metodo", "rota", "dados"),
    [
        ("get", "/categoria", None),
        ("get", "/categoria/1", None),
        ("post", "/categoria", {"nome": "Rede"}),
        ("put", "/categoria/1", {"nome": "Rede"}),
        ("delete", "/categoria/1", None),
    ],
)
def test_categorias_exigem_autenticacao(client, metodo, rota, dados):
    assert client.request(metodo, rota, json=dados).status_code == 401


@pytest.mark.parametrize("perfil", [PerfilUsuario.FUNCIONARIO, PerfilUsuario.TECNICO])
@pytest.mark.parametrize(("metodo", "dados"), [("post", {"nome": "Rede"}), ("put", {"nome": "Rede"}), ("delete", None)])
def test_gestao_restrita_a_admin(client, criar_usuario, autenticar, categoria, perfil, metodo, dados, db):
    usuario = criar_usuario("perfil@example.com", perfil)
    rota = "/categoria" if metodo == "post" else f"/categoria/{categoria.id}"

    assert client.request(metodo, rota, json=dados, headers=autenticar(usuario)).status_code == 403

    db.refresh(categoria)

    assert categoria.nome == "Hardware" and categoria.ativo


def test_criar_editar_desativar_e_reativar(client, admin, autenticar, db):
    headers = autenticar(admin)
    resposta = client.post("/categoria", json={"nome": "  Rede  "}, headers=headers)

    assert resposta.status_code == 201
    assert resposta.json()["nome"] == "Rede"
    assert resposta.json()["ativo"] is True

    categoria_id = resposta.json()["id"]
    resposta = client.put(f"/categoria/{categoria_id}", json={"nome": "Internet"}, headers=headers)

    assert resposta.status_code == 200
    assert resposta.json()["nome"] == "Internet"
    assert client.delete(f"/categoria/{categoria_id}", headers=headers).status_code == 204

    db.expire_all()

    assert db.get(Categoria, categoria_id).ativo is False

    resposta = client.put(f"/categoria/{categoria_id}", json={"ativo": True}, headers=headers)

    assert resposta.status_code == 200 and resposta.json()["ativo"] is True


def test_listagem_e_consulta(client, admin, usuario, autenticar, categoria, db):
    inativa = Categoria(nome="Antiga", ativo=False)
    db.add(inativa)
    db.commit()
    headers = autenticar(usuario)

    assert [c["id"] for c in client.get("/categoria", headers=headers).json()] == [categoria.id]
    assert client.get(f"/categoria/{categoria.id}", headers=headers).status_code == 200
    assert client.get(f"/categoria/{inativa.id}", headers=headers).status_code == 404
    assert client.get("/categoria?incluir_inativas=true", headers=headers).status_code == 403

    headers = autenticar(admin)

    assert {c["id"] for c in client.get("/categoria?incluir_inativas=true", headers=headers).json()} == {
        categoria.id,
        inativa.id,
    }
    assert client.get(f"/categoria/{inativa.id}", headers=headers).status_code == 200


@pytest.mark.parametrize(
    "dados", [{}, {"nome": ""}, {"nome": "   "}, {"nome": "a" * 151}, {"nome": "Rede", "ativo": False}]
)
def test_criacao_invalida(client, admin, autenticar, dados):
    assert client.post("/categoria", json=dados, headers=autenticar(admin)).status_code == 422


@pytest.mark.parametrize(
    "dados", [{}, {"nome": None}, {"ativo": None}, {"ativo": "false"}, {"nome": " "}, {"outro": 1}]
)
def test_atualizacao_invalida(client, admin, autenticar, categoria, dados):
    assert client.put(f"/categoria/{categoria.id}", json=dados, headers=autenticar(admin)).status_code == 422


@pytest.mark.parametrize("metodo", ["get", "put", "delete"])
def test_categoria_inexistente(client, admin, autenticar, metodo):
    assert (
        client.request(
            metodo,
            "/categoria/2147483647",
            json={"nome": "Rede"} if metodo == "put" else None,
            headers=autenticar(admin),
        ).status_code
        == 404
    )


@pytest.mark.parametrize("categoria_id", ["0", "-1", "2147483648", "abc"])
def test_categoria_id_invalido(client, admin, autenticar, categoria_id):
    assert client.get(f"/categoria/{categoria_id}", headers=autenticar(admin)).status_code == 422
