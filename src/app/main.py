from fastapi import FastAPI

from app.rotas.rota_auth import rota_auth
from app.rotas.rota_categoria import rota_categoria
from app.rotas.rota_chamados import rota_chamados
from app.rotas.rota_usuario import rota_usuario

app = FastAPI()
app.include_router(rota_usuario)
app.include_router(rota_auth)
app.include_router(rota_categoria)
app.include_router(rota_chamados)


@app.get("/")
def teste():
    return {"message": "Hello World"}
