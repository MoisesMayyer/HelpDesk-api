from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class HistoricoLeitura(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(gt=0)
    id_chamado: int = Field(gt=0)
    id_usuario: int = Field(gt=0)
    tipo: str
    anterior: str | None
    novo: str | None
    criado_em: datetime
