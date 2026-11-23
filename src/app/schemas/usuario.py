from typing import Annotated, Self

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    SecretStr,
    StrictBool,
    StringConstraints,
    model_validator,
)
from pydantic.json_schema import SkipJsonSchema

from ..dados.perfis import PerfilUsuario

NomeUsuario = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=150)
]
EmailUsuario = Annotated[EmailStr, Field(max_length=254)]


def validar_senha(senha: SecretStr) -> SecretStr:
    if not senha.get_secret_value().strip():
        raise ValueError("A senha não pode conter apenas espaços em branco.")
    return senha


SenhaUsuario = Annotated[
    SecretStr, Field(min_length=8, max_length=128), AfterValidator(validar_senha)
]
Omitido = SkipJsonSchema[None]


class UsuarioBase(BaseModel):
    nome: NomeUsuario
    email: EmailUsuario


class UsuarioCriacao(UsuarioBase):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)

    senha: SenhaUsuario


class AtualizacaoParcial(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)

    @model_validator(mode="after")
    def validar_campos_enviados(self) -> Self:
        if not self.model_fields_set:
            raise ValueError("Envie ao menos um campo para atualizar.")
        if any(getattr(self, campo) is None for campo in self.model_fields_set):
            raise ValueError("Os campos enviados não podem ser nulos.")
        return self


class UsuarioAtualizacao(AtualizacaoParcial):
    nome: NomeUsuario | Omitido = None
    email: EmailUsuario | Omitido = None
    senha: SenhaUsuario | Omitido = None


class UsuarioAtualizacaoAdmin(AtualizacaoParcial):

    tipo: PerfilUsuario | Omitido = None
    ativo: StrictBool | Omitido = None


class UsuarioLeitura(UsuarioBase):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(gt=0)
    tipo: PerfilUsuario
    ativo: bool
