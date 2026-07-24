from slowapi import Limiter
from slowapi.util import get_remote_address

# Limitador em memória (um processo) — suficiente pra uma instância única.
# Se um dia rodar múltiplas instâncias, precisa de um storage compartilhado
# (Redis) pra slowapi contar certo entre processos.
limiter = Limiter(key_func=get_remote_address)
