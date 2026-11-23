from collections.abc import Callable, Coroutine
from typing import Any

from fastapi import Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.routing import APIRoute


class RotaComValidacaoProtegida(APIRoute):
    def get_route_handler(self) -> Callable[[Request], Coroutine[Any, Any, Response]]:
        handler = super().get_route_handler()

        async def tratar_requisicao(request: Request) -> Response:
            try:
                return await handler(request)
            except RequestValidationError as erro:
                # Não propaga a entrada rejeitada nem o corpo bruto.
                raise RequestValidationError(
                    [
                        {
                            "loc": detalhe["loc"][:-1]
                            if detalhe["type"] == "extra_forbidden"
                            else detalhe["loc"],
                            "msg": detalhe["msg"],
                            "type": detalhe["type"],
                        }
                        for detalhe in erro.errors()
                    ]
                ) from None

        return tratar_requisicao
