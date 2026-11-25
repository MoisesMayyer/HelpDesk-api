from datetime import datetime
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, StringConstraints

from app.dados.models.chamados import PrioridadeChamado, StatusChamado

TituloChamado = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=150)
]
def validar_texto_mysql(valor: str) -> str:
    try:
        tamanho = len(valor.encode("utf-8"))
    except UnicodeEncodeError:
        raise ValueError("O texto contém caracteres inválidos.") from None
    if tamanho > 65535:
        raise ValueError("O texto excede o limite de 65535 bytes.")
    return valor


DescricaoChamado = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1),
    AfterValidator(validar_texto_mysql),
]
Identificador = Annotated[int, Field(strict=True, gt=0, le=2**31 - 1)]


class ChamadoCriacao(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)

    titulo: TituloChamado
    descricao: DescricaoChamado
    id_categoria: Identificador


class PrioridadeAtualizacao(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)

    prioridade: PrioridadeChamado


class CategoriaChamadoAtualizacao(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)

    id_categoria: Identificador


class RedistribuicaoChamado(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)

    id_tecnico: Identificador


class ResolucaoChamado(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)

    resolucao: DescricaoChamado


class DevolucaoChamado(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)

    motivo: DescricaoChamado


class ResolucaoLeitura(BaseModel):
    resolucao: str
    criado_em: datetime


class ChamadoLeitura(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: Identificador
    id_usuario: Identificador
    id_tecnico: Identificador | None
    id_categoria: Identificador
    titulo: TituloChamado
    descricao: DescricaoChamado
    aberto_em: datetime
    concluido_em: datetime | None
    status: StatusChamado
    prioridade: PrioridadeChamado
