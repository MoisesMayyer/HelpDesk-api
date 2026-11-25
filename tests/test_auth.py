from datetime import UTC, datetime, timedelta

import jwt
import pytest

from app.dados.config import settings
from app.rotas.rota_auth import _emitir_token


def test_login(client, usuario):
    resposta = client.post('/auth/login', data={'username': usuario.email, 'password': 'senha-segura-123'})
    assert resposta.status_code == 200
    assert resposta.json()['token_type'] == 'bearer'
    assert resposta.json()['access_token']
    assert resposta.json()['refresh_token']


@pytest.mark.parametrize('caso', ['email_inexistente', 'senha_incorreta', 'inativo'])
def test_login_credenciais_invalidas(client, usuario, db, caso):
    email, senha = usuario.email, 'senha-segura-123'
    if caso == 'email_inexistente':
        email = 'inexistente@example.com'
    elif caso == 'senha_incorreta':
        senha = 'incorreta'
    else:
        usuario.ativo = False
        db.commit()
    resposta = client.post('/auth/login', data={'username': email, 'password': senha})
    assert resposta.status_code == 401
    assert resposta.json()['detail'] == 'E-mail ou senha inválidos.'


def test_login_sem_campos(client):
    assert client.post('/auth/login', data={}).status_code == 422


def test_refresh(client, usuario):
    token = _emitir_token(usuario.id, 'refresh')
    resposta = client.post('/auth/refresh', json={'refresh_token': token})
    assert resposta.status_code == 200
    assert resposta.json()['token_type'] == 'bearer'
    assert resposta.json()['access_token']


@pytest.mark.parametrize('caso', ['invalido', 'access', 'expirado', 'inexistente', 'inativo'])
def test_refresh_token_invalido(client, usuario, db, caso):
    if caso == 'invalido':
        token = 'invalido'
    elif caso == 'access':
        token = _emitir_token(usuario.id, 'access')
    elif caso == 'expirado':
        token = jwt.encode({'sub': str(usuario.id), 'tipo': 'refresh', 'exp': datetime.now(UTC) - timedelta(seconds=1)}, settings.secret_key, algorithm=settings.algorithm)
    elif caso == 'inexistente':
        token = _emitir_token(2147483647, 'refresh')
    else:
        token = _emitir_token(usuario.id, 'refresh')
        usuario.ativo = False
        db.commit()
    assert client.post('/auth/refresh', json={'refresh_token': token}).status_code == 401


def test_refresh_sem_token(client):
    assert client.post('/auth/refresh', json={}).status_code == 422


@pytest.mark.parametrize('caso', ['ausente', 'invalido', 'refresh', 'inativo'])
def test_perfil_token_invalido(client, usuario, db, caso):
    headers = {}
    if caso != 'ausente':
        token = 'invalido' if caso == 'invalido' else _emitir_token(usuario.id, 'refresh' if caso == 'refresh' else 'access')
        headers = {'Authorization': f'Bearer {token}'}
    if caso == 'inativo':
        usuario.ativo = False
        db.commit()
    assert client.get('/usuario/me', headers=headers).status_code == 401
