from enum import Enum


class PerfilUsuario(str, Enum):
    FUNCIONARIO = "funcionario"
    TECNICO = "tecnico"
    ADMINISTRADOR = "administrador"
