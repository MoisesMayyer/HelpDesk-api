<div align="center">

# Help Desk API

**API REST para gerenciamento de chamados de suporte técnico em ambientes empresariais.**

![Python](https://img.shields.io/badge/Python-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![MySQL](https://img.shields.io/badge/MySQL-4479A1?logo=mysql&logoColor=white)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-D71F00?logo=sqlalchemy&logoColor=white)
![Alembic](https://img.shields.io/badge/Alembic-6BA81E)
![PyJWT](https://img.shields.io/badge/PyJWT-000000?logo=jsonwebtokens&logoColor=white)
![pytest](https://img.shields.io/badge/pytest-0A9EDC?logo=pytest&logoColor=white)
![Licença MIT](https://img.shields.io/badge/Licen%C3%A7a-MIT-yellow)

</div>

O projeto centraliza solicitações de suporte, organiza o atendimento técnico e permite acompanhar cada chamado desde a abertura até a confirmação da resolução.

> [!IMPORTANT]
> **Em desenvolvimento.** O projeto está na fase inicial de estruturação do MVP. As funcionalidades abaixo representam o escopo planejado.

## Funcionalidades planejadas

- [ ] Autenticação e autorização baseadas em perfis (RBAC)
- [ ] Abertura e gerenciamento de chamados
- [ ] Fila de atendimento com atribuição de técnicos
- [ ] Classificação de prioridade
- [ ] Controle do ciclo de vida dos chamados
- [ ] Confirmação de resolução pelo solicitante
- [ ] Gerenciamento de categorias
- [ ] Comentários internos para a equipe técnica
- [ ] Histórico de alterações e auditoria
- [ ] Consultas com filtros, ordenação e paginação

## Perfis de acesso

| Perfil | Descrição |
| --- | --- |
| Funcionário | Abre chamados e acompanha as próprias solicitações. |
| Técnico | Atende e atualiza os chamados atribuídos. |
| Administrador | Acesso administrativo ao sistema. |

## Estrutura do projeto

```text
HelpDesk-api/
├── alembic/              # Configuração e versões das migrações
├── docs/                 # Frontend estático
├── src/
│   └── app/              # Aplicação FastAPI
├── tests/                # Testes automatizados
├── alembic.ini           # Configuração do Alembic
├── pyproject.toml        # Metadados e dependências do projeto
├── .env.example          # Modelo de variáveis de ambiente
├── LICENSE
└── README.md
```

## Executar localmente

Em um ambiente virtual, instale a aplicação e as dependências de teste:

```sh
python -m pip install -e '.[test]'
```

Antes de iniciar a API, copie `.env.example` para `.env` e preencha `DATABASE_URL` e `SECRET_KEY`. O JWT usa apenas HS256, com prazos positivos e uma chave aleatória de pelo menos 32 bytes. Gere a chave com `python -c "import secrets; print(secrets.token_hex(32))"`.

```sh
alembic upgrade head
python -m uvicorn app.main:app --reload
```

`GET /` não abre conexão com o banco. Execute os testes com `python -m pytest`.

## Licença

Distribuído sob a licença **MIT**. Consulte o arquivo [LICENSE](LICENSE) para mais detalhes.
