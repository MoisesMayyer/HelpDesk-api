from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Path, Query, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.dados.dependencies import SessaoDb, UsuarioAtual
from app.dados.models.categoria import Categoria
from app.dados.models.chamados import (
    Chamados,
    PrioridadeChamado,
    StatusChamado,
    agora_utc,
)
from app.dados.models.comentario_interno import ComentarioInterno
from app.dados.models.historico_chamado import HistoricoChamado
from app.dados.models.usuario import Usuario
from app.dados.perfis import PerfilUsuario
from app.dados.rate_limit import LIMITE_LISTAGEM_CHAMADOS, limiter
from app.rotas.validacao import RotaComValidacaoProtegida
from app.schemas.chamados import (
    CategoriaChamadoAtualizacao,
    ChamadoCriacao,
    ChamadoLeitura,
    DevolucaoChamado,
    PrioridadeAtualizacao,
    RedistribuicaoChamado,
    ResolucaoChamado,
    ResolucaoLeitura,
)
from app.schemas.comentario_interno import ComentarioCriacao, ComentarioLeitura
from app.schemas.historico_chamado import HistoricoLeitura

rota_chamados = APIRouter(
    prefix="/chamados",
    tags=["chamados"],
    route_class=RotaComValidacaoProtegida,
)
ChamadoId = Annotated[int, Path(gt=0, le=2**31 - 1)]


def _exigir_perfil(usuario: Usuario, *perfis: PerfilUsuario) -> None:
    if usuario.tipo not in perfis:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "Operação não permitida."
        )


def _buscar(
    db: Session, chamado_id: int, usuario: Usuario, bloquear: bool = False
) -> Chamados:
    consulta = select(Chamados).where(Chamados.id == chamado_id)
    if usuario.tipo == PerfilUsuario.FUNCIONARIO:
        consulta = consulta.where(Chamados.id_usuario == usuario.id)
    if bloquear:
        consulta = consulta.with_for_update()
    chamado = db.scalar(consulta)
    if chamado is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "Chamado não encontrado."
        )
    return chamado


def _categoria_ativa(db: Session, categoria_id: int) -> None:
    categoria = db.scalar(
        select(Categoria).where(Categoria.id == categoria_id).with_for_update()
    )
    if categoria is None or not categoria.ativo:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Categoria inexistente ou inativa.",
        )


def _registrar(
    db: Session,
    chamado: Chamados,
    usuario: Usuario,
    tipo: str,
    anterior: str | None = None,
    novo: str | None = None,
) -> None:
    db.add(
        HistoricoChamado(
            id_chamado=chamado.id,
            id_usuario=usuario.id,
            tipo=tipo,
            anterior=anterior,
            novo=novo,
        )
    )


def _salvar(db: Session, chamado: Chamados) -> Chamados:
    db.commit()
    db.refresh(chamado)
    return chamado


def _exigir_responsavel(chamado: Chamados, usuario: Usuario) -> None:
    _exigir_perfil(usuario, PerfilUsuario.TECNICO)
    if chamado.id_tecnico != usuario.id:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Chamado não está sob sua responsabilidade.",
        )


def _exigir_solicitante(chamado: Chamados, usuario: Usuario) -> None:
    if chamado.id_usuario != usuario.id:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "Operação restrita ao solicitante."
        )


def _exigir_status(chamado: Chamados, esperado: StatusChamado) -> None:
    if chamado.status != esperado:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Status do chamado incompatível com a operação.",
        )


@rota_chamados.get("", response_model=list[ChamadoLeitura])
@limiter.limit(LIMITE_LISTAGEM_CHAMADOS)
def listar_chamados(
    request: Request,
    response: Response,
    db: SessaoDb,
    usuario: UsuarioAtual,
    status_chamado: Annotated[
        StatusChamado | None, Query(alias="status")
    ] = None,
    prioridade: PrioridadeChamado | None = None,
    id_categoria: Annotated[int | None, Query(gt=0, le=2**31 - 1)] = None,
    id_tecnico: Annotated[int | None, Query(gt=0, le=2**31 - 1)] = None,
    sem_tecnico: bool = False,
    ordem: Literal["aberto_em", "id", "prioridade", "status"] = "aberto_em",
    direcao: Literal["asc", "desc"] = "desc",
    limite: Annotated[int, Query(ge=1, le=100)] = 20,
    deslocamento: Annotated[int, Query(ge=0)] = 0,
) -> list[Chamados]:
    consulta = select(Chamados)

    if usuario.tipo == PerfilUsuario.FUNCIONARIO:
        consulta = consulta.where(Chamados.id_usuario == usuario.id)

    if sem_tecnico:
        consulta = consulta.where(Chamados.id_tecnico.is_(None))

    for coluna, valor in (
        (Chamados.status, status_chamado),
        (Chamados.prioridade, prioridade),
        (Chamados.id_categoria, id_categoria),
        (Chamados.id_tecnico, id_tecnico),
    ):
        if valor is not None:
            consulta = consulta.where(coluna == valor)

    coluna = getattr(Chamados, ordem)
    ordenacao = coluna.asc() if direcao == "asc" else coluna.desc()

    return list(
        db.scalars(
            consulta.order_by(ordenacao, Chamados.id.desc())
            .offset(deslocamento)
            .limit(limite)
        )
    )


@rota_chamados.get("/{chamado_id}", response_model=ChamadoLeitura)
def consultar_chamado(
    chamado_id: ChamadoId, db: SessaoDb, usuario: UsuarioAtual
) -> Chamados:
    return _buscar(db, chamado_id, usuario)


@rota_chamados.post(
    "", response_model=ChamadoLeitura, status_code=status.HTTP_201_CREATED
)
def criar_chamado(
    dados: ChamadoCriacao, db: SessaoDb, usuario: UsuarioAtual
) -> Chamados:
    _categoria_ativa(db, dados.id_categoria)
    chamado = Chamados(**dados.model_dump(), id_usuario=usuario.id)
    db.add(chamado)
    db.flush()
    _registrar(
        db, chamado, usuario, "criacao", novo=StatusChamado.ABERTO.value
    )
    return _salvar(db, chamado)


@rota_chamados.put("/{chamado_id}/prioridade", response_model=ChamadoLeitura)
def classificar_chamado(
    chamado_id: ChamadoId,
    dados: PrioridadeAtualizacao,
    db: SessaoDb,
    usuario: UsuarioAtual,
) -> Chamados:
    _exigir_perfil(usuario, PerfilUsuario.TECNICO)
    chamado = _buscar(db, chamado_id, usuario, bloquear=True)

    if chamado.status == StatusChamado.FECHADO:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Chamado fechado não pode ser alterado."
        )

    if chamado.prioridade != dados.prioridade:
        _registrar(
            db,
            chamado,
            usuario,
            "prioridade",
            chamado.prioridade.value,
            dados.prioridade.value,
        )
        chamado.prioridade = dados.prioridade

    return _salvar(db, chamado)


@rota_chamados.put("/{chamado_id}/categoria", response_model=ChamadoLeitura)
def corrigir_categoria(
    chamado_id: ChamadoId,
    dados: CategoriaChamadoAtualizacao,
    db: SessaoDb,
    usuario: UsuarioAtual,
) -> Chamados:
    _exigir_perfil(usuario, PerfilUsuario.TECNICO)
    chamado = _buscar(db, chamado_id, usuario, bloquear=True)

    if chamado.status == StatusChamado.FECHADO:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Chamado fechado não pode ser alterado."
        )

    _categoria_ativa(db, dados.id_categoria)

    if chamado.id_categoria != dados.id_categoria:
        _registrar(
            db,
            chamado,
            usuario,
            "categoria",
            str(chamado.id_categoria),
            str(dados.id_categoria),
        )
        chamado.id_categoria = dados.id_categoria

    return _salvar(db, chamado)


@rota_chamados.post("/{chamado_id}/assumir", response_model=ChamadoLeitura)
def assumir_chamado(
    chamado_id: ChamadoId, db: SessaoDb, usuario: UsuarioAtual
) -> Chamados:
    _exigir_perfil(usuario, PerfilUsuario.TECNICO)
    chamado = _buscar(db, chamado_id, usuario, bloquear=True)
    _exigir_status(chamado, StatusChamado.ABERTO)

    if chamado.id_tecnico is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Chamado já possui técnico responsável."
        )
    chamado.id_tecnico = usuario.id
    chamado.status = StatusChamado.EM_ANDAMENTO
    _registrar(db, chamado, usuario, "atribuicao", novo=str(usuario.id))
    _registrar(
        db,
        chamado,
        usuario,
        "status",
        StatusChamado.ABERTO.value,
        chamado.status.value,
    )
    return _salvar(db, chamado)


def _alterar_status_responsavel(
    chamado_id: int, db: Session, usuario: Usuario,
    anterior: StatusChamado, novo: StatusChamado,
) -> Chamados:
    chamado = _buscar(db, chamado_id, usuario, bloquear=True)
    _exigir_responsavel(chamado, usuario)
    _exigir_status(chamado, anterior)
    chamado.status = novo
    _registrar(db, chamado, usuario, "status", anterior.value, novo.value)
    return _salvar(db, chamado)


@rota_chamados.post("/{chamado_id}/aguardar-resposta", response_model=ChamadoLeitura)
def aguardar_resposta(
    chamado_id: ChamadoId, db: SessaoDb, usuario: UsuarioAtual
) -> Chamados:
    return _alterar_status_responsavel(
        chamado_id, db, usuario,
        StatusChamado.EM_ANDAMENTO, StatusChamado.AGUARDANDO_RESPOSTA,
    )


@rota_chamados.post("/{chamado_id}/retomar", response_model=ChamadoLeitura)
def retomar_chamado(
    chamado_id: ChamadoId, db: SessaoDb, usuario: UsuarioAtual
) -> Chamados:
    return _alterar_status_responsavel(
        chamado_id, db, usuario,
        StatusChamado.AGUARDANDO_RESPOSTA, StatusChamado.EM_ANDAMENTO,
    )


@rota_chamados.post("/{chamado_id}/resolver", response_model=ChamadoLeitura)
def resolver_chamado(
    chamado_id: ChamadoId,
    dados: ResolucaoChamado,
    db: SessaoDb,
    usuario: UsuarioAtual,
) -> Chamados:
    chamado = _buscar(db, chamado_id, usuario, bloquear=True)
    _exigir_responsavel(chamado, usuario)
    _exigir_status(chamado, StatusChamado.EM_ANDAMENTO)
    chamado.status = StatusChamado.RESOLVIDO
    _registrar(
        db,
        chamado,
        usuario,
        "status",
        StatusChamado.EM_ANDAMENTO.value,
        chamado.status.value,
    )
    _registrar(db, chamado, usuario, "resolucao", novo=dados.resolucao)
    return _salvar(db, chamado)


@rota_chamados.get("/{chamado_id}/resolucao", response_model=ResolucaoLeitura)
def consultar_resolucao(
    chamado_id: ChamadoId, db: SessaoDb, usuario: UsuarioAtual
) -> dict:
    _buscar(db, chamado_id, usuario)
    registro = db.scalar(
        select(HistoricoChamado)
        .where(
            HistoricoChamado.id_chamado == chamado_id,
            HistoricoChamado.tipo == "resolucao",
        )
        .order_by(HistoricoChamado.id.desc())
    )
    if registro is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "Resolução não encontrada."
        )
    return {"resolucao": registro.novo, "criado_em": registro.criado_em}


@rota_chamados.post("/{chamado_id}/fechar", response_model=ChamadoLeitura)
def fechar_chamado(
    chamado_id: ChamadoId, db: SessaoDb, usuario: UsuarioAtual
) -> Chamados:
    chamado = _buscar(db, chamado_id, usuario, bloquear=True)
    _exigir_solicitante(chamado, usuario)
    _exigir_status(chamado, StatusChamado.RESOLVIDO)
    chamado.status = StatusChamado.FECHADO
    chamado.concluido_em = agora_utc()
    _registrar(
        db,
        chamado,
        usuario,
        "status",
        StatusChamado.RESOLVIDO.value,
        chamado.status.value,
    )
    _registrar(db, chamado, usuario, "fechamento")
    return _salvar(db, chamado)


@rota_chamados.post("/{chamado_id}/devolver", response_model=ChamadoLeitura)
def devolver_chamado(
    chamado_id: ChamadoId,
    dados: DevolucaoChamado,
    db: SessaoDb,
    usuario: UsuarioAtual,
) -> Chamados:
    chamado = _buscar(db, chamado_id, usuario, bloquear=True)
    _exigir_solicitante(chamado, usuario)
    _exigir_status(chamado, StatusChamado.RESOLVIDO)
    chamado.status = StatusChamado.EM_ANDAMENTO
    _registrar(
        db,
        chamado,
        usuario,
        "status",
        StatusChamado.RESOLVIDO.value,
        chamado.status.value,
    )
    _registrar(db, chamado, usuario, "devolucao", novo=dados.motivo)
    return _salvar(db, chamado)


@rota_chamados.put("/{chamado_id}/responsavel", response_model=ChamadoLeitura)
def redistribuir_chamado(
    chamado_id: ChamadoId,
    dados: RedistribuicaoChamado,
    db: SessaoDb,
    usuario: UsuarioAtual,
) -> Chamados:
    _exigir_perfil(usuario, PerfilUsuario.ADMINISTRADOR)
    chamado = _buscar(db, chamado_id, usuario, bloquear=True)
    if chamado.id_tecnico is None or chamado.status == StatusChamado.FECHADO:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Chamado não pode ser redistribuído."
        )
    tecnico = db.scalar(
        select(Usuario).where(Usuario.id == dados.id_tecnico).with_for_update()
    )
    if (
        tecnico is None
        or not tecnico.ativo
        or tecnico.tipo != PerfilUsuario.TECNICO
    ):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Técnico inexistente ou inativo.",
        )
    if chamado.id_tecnico != tecnico.id:
        _registrar(
            db,
            chamado,
            usuario,
            "redistribuicao",
            str(chamado.id_tecnico),
            str(tecnico.id),
        )
        chamado.id_tecnico = tecnico.id
    return _salvar(db, chamado)


@rota_chamados.post(
    "/{chamado_id}/comentarios",
    response_model=ComentarioLeitura,
    status_code=status.HTTP_201_CREATED,
)
def criar_comentario(
    chamado_id: ChamadoId,
    dados: ComentarioCriacao,
    db: SessaoDb,
    usuario: UsuarioAtual,
) -> ComentarioInterno:
    _exigir_perfil(usuario, PerfilUsuario.TECNICO)
    chamado = _buscar(db, chamado_id, usuario, bloquear=True)
    comentario = ComentarioInterno(
        id_chamado=chamado.id, id_usuario=usuario.id, conteudo=dados.conteudo
    )
    db.add(comentario)
    db.commit()
    db.refresh(comentario)
    return comentario


@rota_chamados.get(
    "/{chamado_id}/comentarios", response_model=list[ComentarioLeitura]
)
def listar_comentarios(
    chamado_id: ChamadoId, db: SessaoDb, usuario: UsuarioAtual
) -> list[ComentarioInterno]:
    _exigir_perfil(usuario, PerfilUsuario.TECNICO, PerfilUsuario.ADMINISTRADOR)
    _buscar(db, chamado_id, usuario)
    return list(
        db.scalars(
            select(ComentarioInterno)
            .where(ComentarioInterno.id_chamado == chamado_id)
            .order_by(ComentarioInterno.id)
        )
    )


@rota_chamados.get(
    "/{chamado_id}/historico", response_model=list[HistoricoLeitura]
)
def consultar_historico(
    chamado_id: ChamadoId, db: SessaoDb, usuario: UsuarioAtual
) -> list[HistoricoChamado]:
    _exigir_perfil(usuario, PerfilUsuario.ADMINISTRADOR)
    _buscar(db, chamado_id, usuario)
    return list(
        db.scalars(
            select(HistoricoChamado)
            .where(HistoricoChamado.id_chamado == chamado_id)
            .order_by(HistoricoChamado.id)
        )
    )
