from fastapi import FastAPI
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.dados.rate_limit import limiter
from app.rotas.rota_auth import rota_auth
from app.rotas.rota_categoria import rota_categoria
from app.rotas.rota_chamados import rota_chamados
from app.rotas.rota_usuario import rota_usuario

app = FastAPI()
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)
app.include_router(rota_usuario)
app.include_router(rota_auth)
app.include_router(rota_categoria)
app.include_router(rota_chamados)


@app.get("/")
def teste():
    return {"message": "Hello World"}
