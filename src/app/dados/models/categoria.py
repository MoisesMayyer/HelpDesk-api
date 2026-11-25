from sqlalchemy import Boolean, Column, Integer, String

from app.dados.database import Base


class Categoria(Base):
    __tablename__ = "categorias"

    id = Column(Integer, primary_key=True, autoincrement=True)
    nome = Column(String(150), nullable=False)
    ativo = Column(Boolean, nullable=False, default=True, server_default="1")
