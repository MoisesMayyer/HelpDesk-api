from slowapi import Limiter
from slowapi.util import get_remote_address

LIMITE_PADRAO = "120/minute"
LIMITE_LOGIN = "10/minute"
LIMITE_LISTAGEM_CHAMADOS = "240/minute"

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[LIMITE_PADRAO],
    storage_uri="memory://",
    key_style="endpoint",
    headers_enabled=True,
)
