from sqlalchemy import Column, DateTime, ForeignKey, Integer, Text

from app.dados.database import Base
from app.dados.models.chamados import agora_utc


class ComentarioInterno(Base):
    __tablename__ = "comentarios_internos"

    id = Column(Integer, primary_key=True, autoincrement=True)
    id_chamado = Column(Integer, ForeignKey("chamados.id"), nullable=False)
    id_usuario = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    conteudo = Column(Text, nullable=False)
    criado_em = Column(DateTime, nullable=False, default=agora_utc)
