from datetime import UTC, datetime
from enum import Enum

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.dados.database import Base


def agora_utc() -> datetime:
    # MySQL DATETIME não armazena fuso; as datas são gravadas em UTC.
    return datetime.now(UTC).replace(tzinfo=None)


class StatusChamado(str, Enum):
    ABERTO = "aberto"
    EM_ANDAMENTO = "em_andamento"
    AGUARDANDO_RESPOSTA = "aguardando_resposta"
    RESOLVIDO = "resolvido"
    FECHADO = "fechado"


class PrioridadeChamado(str, Enum):
    NAO_CLASSIFICADA = "nao_classificada"
    BAIXA = "baixa"
    MEDIA = "media"
    ALTA = "alta"
    CRITICA = "critica"


class Chamados(Base):
    __tablename__ = "chamados"

    id = Column(Integer, primary_key=True, autoincrement=True)
    id_usuario = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    id_tecnico: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("usuarios.id"), nullable=True
    )
    id_categoria = Column(Integer, ForeignKey("categorias.id"), nullable=False)
    titulo = Column(String(150), nullable=False)
    descricao = Column(Text, nullable=False)
    aberto_em = Column(DateTime, nullable=False, default=agora_utc)
    concluido_em = Column(DateTime, nullable=True)
    status = Column(
        SQLEnum(
            StatusChamado,
            values_callable=lambda status_list: [
                status.value for status in status_list
            ],
        ),
        nullable=False,
        default=StatusChamado.ABERTO,
    )
    prioridade = Column(
        SQLEnum(
            PrioridadeChamado,
            values_callable=lambda prioridades: [
                prioridade.value for prioridade in prioridades
            ],
        ),
        nullable=False,
        default=PrioridadeChamado.NAO_CLASSIFICADA,
    )
