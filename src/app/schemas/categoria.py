from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StringConstraints

from app.schemas.usuario import AtualizacaoParcial, Omitido

NomeCategoria = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=150)]


class CategoriaCriacao(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)

    nome: NomeCategoria


class CategoriaAtualizacao(AtualizacaoParcial):
    nome: NomeCategoria | Omitido = None
    ativo: StrictBool | Omitido = None


class CategoriaLeitura(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(gt=0)
    nome: NomeCategoria
    ativo: bool
