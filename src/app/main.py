from fastapi import FastAPI

from app.rotas.rota_auth import rota_auth
from app.rotas.rota_usuario import rota_usuario

app = FastAPI()
app.include_router(rota_usuario)
app.include_router(rota_auth)


@app.get("/")
def teste():
    return {"message": "Hello World"}
