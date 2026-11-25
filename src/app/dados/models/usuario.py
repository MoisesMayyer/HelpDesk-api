from sqlalchemy import Boolean, Column, Integer, String
from sqlalchemy import Enum as SQLEnum

from app.dados.database import Base
from app.dados.perfis import PerfilUsuario


class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    nome = Column(String(150), nullable=False)
    email = Column(String(254), nullable=False, unique=True)
    senha_hash = Column(String(255), nullable=False)
    versao_token = Column(Integer, nullable=False, default=0, server_default="0")
    tipo = Column(
        SQLEnum(
            PerfilUsuario,
            values_callable=lambda perfis: [perfil.value for perfil in perfis],
        ),
        nullable=False,
    )
    ativo = Column(Boolean, nullable=False, default=True)
