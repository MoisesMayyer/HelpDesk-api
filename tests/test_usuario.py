import pytest

from app.dados.dependencies import hash_senha
from app.dados.models.usuario import Usuario
from app.dados.perfis import PerfilUsuario


@pytest.mark.parametrize(
    ("metodo", "rota", "dados"),
    [
        ("get", "/usuario", None),
        ("get", "/usuario/1", None),
        ("post", "/usuario", {"nome": "Novo", "email": "novo@example.com", "senha": "senha-123"}),
        ("put", "/usuario/1", {"ativo": False}),
        ("delete", "/usuario/1", None),
    ],
)
def test_rotas_administrativas_exigem_autenticacao(client, metodo, rota, dados):
    assert client.request(metodo, rota, json=dados).status_code == 401


@pytest.mark.parametrize(
    ("metodo", "rota", "dados"),
    [
        ("get", "/usuario", None),
        ("get", "/usuario/{id}", None),
        ("post", "/usuario", {"nome": "Novo", "email": "novo@example.com", "senha": "senha-123"}),
        ("put", "/usuario/{id}", {"ativo": False}),
        ("delete", "/usuario/{id}", None),
    ],
)
def test_usuario_nao_acessa_dados_de_outro(client, usuario, outro_usuario, autenticar, metodo, rota, dados, db):
    resposta = client.request(metodo, rota.format(id=outro_usuario.id), json=dados, headers=autenticar(usuario))
    assert resposta.status_code == 403
    db.refresh(outro_usuario)
    assert outro_usuario.ativo is True
    assert outro_usuario.tipo == PerfilUsuario.FUNCIONARIO


def test_listar_usuarios_admin(client, admin, usuario, autenticar):
    resposta = client.get("/usuario", headers=autenticar(admin))
    assert resposta.status_code == 200
    assert {item["id"] for item in resposta.json()} == {admin.id, usuario.id}
    assert all("senha_hash" not in item for item in resposta.json())


def test_consultar_outro_usuario_admin(client, admin, usuario, autenticar):
    resposta = client.get(f"/usuario/{usuario.id}", headers=autenticar(admin))
    assert resposta.status_code == 200
    assert resposta.json()["id"] == usuario.id


def test_consultar_perfil_proprio(client, usuario, outro_usuario, autenticar):
    resposta = client.get("/usuario/me", headers=autenticar(usuario))
    assert resposta.status_code == 200
    assert resposta.json()["id"] == usuario.id
    assert resposta.json()["id"] != outro_usuario.id
    assert "senha_hash" not in resposta.json()


def test_criar_usuario_admin(client, admin, autenticar, db):
    dados = {"nome": "Novo Usuário", "email": "novo@example.com", "senha": "senha-123"}
    resposta = client.post("/usuario", json=dados, headers=autenticar(admin))
    assert resposta.status_code == 201
    assert resposta.json()["tipo"] == "funcionario"
    assert "senha" not in resposta.json()
    criado = db.get(Usuario, resposta.json()["id"])
    assert hash_senha.verify(dados["senha"], criado.senha_hash)


def test_criar_usuario_email_duplicado(client, admin, usuario, autenticar):
    resposta = client.post(
        "/usuario", json={"nome": "Novo", "email": usuario.email, "senha": "senha-123"}, headers=autenticar(admin)
    )
    assert resposta.status_code == 409


@pytest.mark.parametrize(
    "dados",
    [
        {},
        {"nome": "", "email": "novo@example.com", "senha": "senha-123"},
        {"nome": "Novo", "email": "invalido", "senha": "senha-123"},
        {"nome": "Novo", "email": "novo@example.com", "senha": "curta"},
        {"nome": "Novo", "email": "novo@example.com", "senha": "        "},
        {"nome": "Novo", "email": "novo@example.com", "senha": "senha-123", "tipo": "administrador"},
    ],
)
def test_criar_usuario_dados_invalidos(client, admin, autenticar, dados):
    assert client.post("/usuario", json=dados, headers=autenticar(admin)).status_code == 422


@pytest.mark.parametrize(
    ("campo", "valor"), [("nome", "Nome alterado"), ("email", "alterado@example.com"), ("senha", "nova-senha-123")]
)
def test_atualizar_proprio_perfil(client, usuario, outro_usuario, autenticar, db, campo, valor):
    resposta = client.put("/usuario/me", json={campo: valor}, headers=autenticar(usuario))
    assert resposta.status_code == 200
    db.refresh(usuario)
    db.refresh(outro_usuario)
    assert outro_usuario.nome == "Usuário Teste"
    if campo == "senha":
        assert hash_senha.verify(valor, usuario.senha_hash)
    else:
        assert getattr(usuario, campo) == valor


def test_atualizar_perfil_email_duplicado(client, usuario, outro_usuario, autenticar):
    assert (
        client.put("/usuario/me", json={"email": outro_usuario.email}, headers=autenticar(usuario)).status_code == 409
    )


@pytest.mark.parametrize(
    "dados",
    [{}, {"nome": None}, {"email": "invalido"}, {"senha": "curta"}, {"tipo": "administrador"}, {"ativo": False}],
)
def test_atualizar_perfil_dados_invalidos(client, usuario, autenticar, dados):
    assert client.put("/usuario/me", json=dados, headers=autenticar(usuario)).status_code == 422


@pytest.mark.parametrize(("campo", "valor"), [("tipo", "tecnico"), ("ativo", False)])
def test_admin_atualiza_outro_usuario(client, admin, usuario, autenticar, db, campo, valor):
    resposta = client.put(f"/usuario/{usuario.id}", json={campo: valor}, headers=autenticar(admin))
    assert resposta.status_code == 200
    db.refresh(usuario)
    assert getattr(usuario, campo) == valor


@pytest.mark.parametrize("dados", [{}, {"tipo": None}, {"tipo": "inexistente"}, {"ativo": "false"}, {"nome": "Outro"}])
def test_admin_atualizacao_dados_invalidos(client, admin, usuario, autenticar, dados):
    assert client.put(f"/usuario/{usuario.id}", json=dados, headers=autenticar(admin)).status_code == 422


def test_admin_desativa_outro_usuario(client, admin, usuario, autenticar, db):
    resposta = client.delete(f"/usuario/{usuario.id}", headers=autenticar(admin))
    assert resposta.status_code == 204
    db.refresh(usuario)
    assert usuario.ativo is False
    assert db.get(Usuario, usuario.id) is not None


@pytest.mark.parametrize(("metodo", "dados"), [("get", None), ("put", {"ativo": False}), ("delete", None)])
def test_usuario_inexistente(client, admin, autenticar, metodo, dados):
    assert client.request(metodo, "/usuario/2147483647", json=dados, headers=autenticar(admin)).status_code == 404


@pytest.mark.parametrize("id_invalido", ["0", "-1", "2147483648", "abc"])
def test_usuario_id_invalido(client, admin, autenticar, id_invalido):
    assert client.get(f"/usuario/{id_invalido}", headers=autenticar(admin)).status_code == 422


@pytest.mark.parametrize(
    ("metodo", "dados"), [("put", {"tipo": "funcionario"}), ("put", {"ativo": False}), ("delete", None)]
)
def test_nao_remove_ultimo_admin(client, admin, autenticar, metodo, dados, db):
    resposta = client.request(metodo, f"/usuario/{admin.id}", json=dados, headers=autenticar(admin))
    assert resposta.status_code == 409
    db.refresh(admin)
    assert admin.ativo is True
    assert admin.tipo == PerfilUsuario.ADMINISTRADOR


def test_promover_proprio_usuario(client, usuario, autenticar, db):
    resposta = client.patch("/usuario/admin", headers=autenticar(usuario))
    assert resposta.status_code == 200
    db.refresh(usuario)
    assert usuario.tipo == PerfilUsuario.ADMINISTRADOR


def test_promocao_exige_autenticacao(client):
    assert client.patch("/usuario/admin").status_code == 401
