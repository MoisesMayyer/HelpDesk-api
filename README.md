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

</div>


API REST para suporte técnico interno de uma empresa. Funcionários abrem e acompanham chamados, técnicos atendem pela fila e o solicitante confirma a solução ou devolve o chamado para atendimento.

> [!WARNING]
> **Somente para uso local.** A configuração atual inclui um atalho de desenvolvimento que permite a autopromoção a administrador. Não exponha a API publicamente sem remover ou proteger esse atalho e revisar a inicialização do primeiro administrador.

## Funcionalidades

- **Autenticação e permissões:** tokens JWT de acesso e renovação, senhas com hash Argon2 e acesso controlado pelo perfil e pela relação do usuário com o chamado.
- **Fila de atendimento:** técnicos assumem chamados disponíveis, com proteção contra atribuição simultânea do mesmo chamado a dois técnicos. Administradores podem redistribuir atendimentos.
- **Ciclo do chamado:** a API valida as mudanças de status. O técnico responsável registra a solução; só o solicitante pode fechar o chamado ou devolvê-lo para atendimento.
- **Consultas e supervisão:** listagem com filtros, ordenação e paginação, comentários internos e histórico de alterações. Administradores gerenciam usuários e categorias e consultam o histórico.

## Perfis de acesso

| Perfil | Descrição |
| --- | --- |
| Funcionário | Abre chamados e acompanha as próprias solicitações. |
| Técnico | Consulta a fila, assume chamados e atende os que estão sob sua responsabilidade. |
| Administrador | Supervisiona os atendimentos sem herdar automaticamente as permissões de técnico. |

**Stack:** Python 3.11+, FastAPI, MySQL com PyMySQL, SQLAlchemy, Alembic e pytest.

## Como funciona o atendimento

| Etapa | O que acontece |
| --- | --- |
| **Abertura** | Qualquer perfil autenticado pode abrir um chamado com título, descrição e uma categoria ativa. A API identifica o solicitante pelo token e cria o chamado como `aberto`, sem técnico e com prioridade `nao_classificada`. |
| **Triagem e atribuição** | Técnicos podem classificar a prioridade e corrigir a categoria de chamados não fechados, mesmo antes de assumirem o atendimento. Quando um técnico assume um chamado disponível, a API vincula o responsável e muda o status para `em_andamento`. |
| **Atendimento** | O técnico responsável pode colocar o chamado em `aguardando_resposta` e retomá-lo depois. Para marcar um chamado como `resolvido`, ele precisa registrar a solução enquanto o chamado está `em_andamento`. |
| **Confirmação** | O solicitante consulta a solução registrada. Se o problema foi resolvido, confirma o fechamento. Se persistir, informa o motivo da devolução, e o chamado volta para `em_andamento` com o mesmo técnico. |
| **Redistribuição** | O administrador pode transferir um chamado já atribuído e ainda não fechado para outro técnico ativo. A troca não altera o status. |

### Regras de negócio

- **Concorrência na fila:** ao assumir um chamado, a API bloqueia o registro no MySQL durante a transação e verifica se ele ainda está disponível. Se dois técnicos tentarem assumi-lo ao mesmo tempo, apenas um fica responsável; a outra tentativa recebe `409 Conflict`.
- **Visibilidade:** funcionários só veem os próprios chamados. Técnicos e administradores veem todos, mas as ações dependem do perfil e, quando necessário, de ser o técnico responsável ou o solicitante. Um perfil administrativo, por si só, não permite assumir ou resolver chamados.
- **Comentários e histórico:** técnicos criam comentários internos; técnicos e administradores podem lê-los. O histórico é exclusivo de administradores e registra ações como abertura, atribuição, mudanças de status, prioridade e categoria, resolução, devolução e fechamento, com autor, data e valores anterior e novo quando aplicável.
- **Contas e categorias:** a exclusão é lógica: o registro é desativado, não apagado. Categorias inativas permanecem nos chamados já associados, mas não podem ser selecionadas na abertura ou na troca de categoria. A API impede desativar ou rebaixar o último administrador ativo.
- **Sessão:** o login recebe o e-mail no campo `username` e retorna um token de acesso e outro de renovação. A renovação emite apenas um novo token de acesso. Alterar a senha ou desativar a conta invalida os tokens anteriores.

## Endpoints principais

| Operação | Rota | Quem pode usar |
| --- | --- | --- |
| Fazer login ou renovar o acesso | `POST /auth/login` · `POST /auth/refresh` | Login com credenciais; renovação com refresh token |
| Abrir, listar ou consultar chamados | `POST /chamados` · `GET /chamados` · `GET /chamados/{chamado_id}` | Qualquer perfil autenticado, conforme a regra de visibilidade |
| Assumir um chamado | `POST /chamados/{chamado_id}/assumir` | Técnico |
| Registrar a solução | `POST /chamados/{chamado_id}/resolver` | Técnico responsável |
| Consultar a última solução | `GET /chamados/{chamado_id}/resolucao` | Quem tem acesso ao chamado |
| Fechar ou devolver | `POST /chamados/{chamado_id}/fechar` · `POST /chamados/{chamado_id}/devolver` | Solicitante do chamado |
| Redistribuir ou consultar o histórico | `PUT /chamados/{chamado_id}/responsavel` · `GET /chamados/{chamado_id}/historico` | Administrador |

Na listagem, é possível filtrar por status, prioridade, categoria, técnico responsável ou ausência de técnico. Por exemplo, `GET /chamados?status=aberto&sem_tecnico=true` mostra os chamados disponíveis na fila de atendimento. Por padrão, a API retorna até 20 chamados, dos mais recentes para os mais antigos. Use `limite` (até 100) e `deslocamento` para paginar; a resposta não inclui o total de registros.

Consulte o [Swagger](http://127.0.0.1:8000/docs) ou o [ReDoc](http://127.0.0.1:8000/redoc) para ver os campos e as respostas de cada rota.

## Executar localmente

Você precisa de Python 3.11+ e de um servidor MySQL acessível com um banco já criado. O Alembic cria as tabelas, mas não cria o banco. Na raiz do projeto, crie e ative um ambiente virtual e instale a aplicação:

```sh
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .
cp .env.example .env
```

No Windows, ative o ambiente com `.venv\Scripts\activate` no Prompt de Comando ou `.venv\Scripts\Activate.ps1` no PowerShell, e copie o arquivo com `copy .env.example .env`.

Edite `.env` e preencha `DATABASE_URL` (por exemplo, `mysql+pymysql://usuario:senha@localhost:3306/nome_do_banco?charset=utf8mb4`) e `SECRET_KEY` com uma chave aleatória de pelo menos 32 bytes. Gere uma chave com `python -c "import secrets; print(secrets.token_hex(32))"`. Não versione o `.env` nem compartilhe suas credenciais.

Na raiz do projeto, aplique as migrações e inicie a API:

```sh
alembic upgrade head
python -m uvicorn app.main:app --reload
```

Abra o [Swagger](http://127.0.0.1:8000/docs). Em um banco novo:

1. Use `POST /usuario/inicializar-admin` com `nome`, `email` e `senha` para criar o primeiro administrador. A rota é pública, exige MySQL e só funciona enquanto não existir nenhum usuário no banco, mesmo inativo.
2. Faça login em `POST /auth/login`, usando o e-mail no campo `username` e a senha em `password`. No Swagger, autorize-se com o token de acesso.
3. Crie uma categoria em `POST /categoria` antes de abrir o primeiro chamado. Não há categoria inicial automática em um banco novo.

Para executar os testes, instale também as dependências opcionais com `python -m pip install -e '.[test]'`.

## Testes

A suíte com pytest cobre autenticação, permissões, atribuição concorrente e transições de status dos chamados. O [workflow do GitHub Actions](.github/workflows/tests.yml) executa os testes com Python 3.11 e MySQL 8.4.

Para executar a suíte completa localmente, use `python -m pytest`. Prefira um servidor MySQL de testes isolado via `TEST_DATABASE_URL`: a suíte precisa de permissão para criar e excluir bancos temporários.

## Licença

Distribuído sob a licença **MIT**. Consulte o arquivo [LICENSE](LICENSE) para mais detalhes.
