from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text

from app.dados.database import Base
from app.dados.models.chamados import agora_utc


class HistoricoChamado(Base):
    __tablename__ = "historico_chamados"

    id = Column(Integer, primary_key=True, autoincrement=True)
    id_chamado = Column(Integer, ForeignKey("chamados.id"), nullable=False)
    id_usuario = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    tipo = Column(String(100), nullable=False)
    anterior = Column(Text, nullable=True)
    novo = Column(Text, nullable=True)
    criado_em = Column(DateTime, nullable=False, default=agora_utc)
