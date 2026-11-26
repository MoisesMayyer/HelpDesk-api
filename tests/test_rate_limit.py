import pytest
from fastapi.testclient import TestClient

from app.dados.dependencies import get_db, hash_senha
from app.dados.rate_limit import limiter
from app.main import app


@pytest.fixture(autouse=True)
def ativar_rate_limit(desativar_rate_limit, monkeypatch):
    monkeypatch.setattr(limiter, "enabled", True)


def test_limite_padrao_e_retry_after():
    limiter.reset()
    with TestClient(app, client=("192.0.2.1", 1234)) as cliente:
        for _ in range(120):
            assert cliente.get("/").status_code == 200
        resposta = cliente.get("/")
        assert resposta.status_code == 429
        assert int(resposta.headers["retry-after"]) >= 1
        assert cliente.get("/", headers={"X-Forwarded-For": "192.0.2.2"}).status_code == 429
    limiter.reset()


def test_login_tem_limite_proprio(monkeypatch):
    class Banco:
        def scalar(self, consulta):
            return None

    limiter.reset()
    monkeypatch.setattr(hash_senha, "verify", lambda *args: False)
    app.dependency_overrides[get_db] = lambda: Banco()
    try:
        with TestClient(app, client=("192.0.2.2", 1234)) as cliente:
            for _ in range(10):
                resposta = cliente.post("/auth/login", data={"username": "teste@example.com", "password": "x"})
                assert resposta.status_code == 401
            resposta = cliente.post("/auth/login", data={"username": "teste@example.com", "password": "x"})
            assert resposta.status_code == 429
            assert int(resposta.headers["retry-after"]) >= 1
            assert cliente.get("/").status_code == 200
    finally:
        app.dependency_overrides.pop(get_db, None)
        limiter.reset()
