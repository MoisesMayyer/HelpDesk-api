from datetime import datetime
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, StringConstraints

from app.schemas.chamados import validar_texto_mysql

ConteudoComentario = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1),
    AfterValidator(validar_texto_mysql),
]


class ComentarioCriacao(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)

    conteudo: ConteudoComentario


class ComentarioLeitura(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(gt=0)
    id_chamado: int = Field(gt=0)
    id_usuario: int = Field(gt=0)
    conteudo: str
    criado_em: datetime
