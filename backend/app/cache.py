"""Cache pras leituras públicas de app publicado (sem auth, alto tráfego:
dados do app, config dos módulos, itens e categorias do catálogo/cardápio).

Usa Redis se REDIS_URL estiver configurada; sem isso, cai automaticamente pra
um cache em memória do próprio processo. Essa segunda opção já é correta pra
esta implantação -- o Render roda o backend com WEB_CONCURRENCY=1 (um único
processo), então cache em memória se comporta igual a um cache compartilhado
de verdade. Mesmo padrão de "degrada sem credencial" já usado nesta sessão
pra Sentry/SMTP/VAPID: o recurso funciona de verdade assim que a credencial
existir, sem exigir nenhuma mudança de código."""
import json
import time
from typing import Any, Optional, Protocol

from app.config import settings

PUBLIC_CACHE_TTL = 60  # segundos -- rede de segurança além da invalidação explícita nas rotas de escrita


class _CacheBackend(Protocol):
    def get(self, key: str) -> Optional[str]: ...
    def set(self, key: str, value: str, ttl: int) -> None: ...
    def delete_prefix(self, prefix: str) -> None: ...


class _MemoryCache:
    def __init__(self) -> None:
        self._store: dict[str, tuple[float, str]] = {}

    def get(self, key: str) -> Optional[str]:
        entry = self._store.get(key)
        if entry is None:
            return None
        expires_at, value = entry
        if expires_at < time.time():
            del self._store[key]
            return None
        return value

    def set(self, key: str, value: str, ttl: int) -> None:
        self._store[key] = (time.time() + ttl, value)

    def delete_prefix(self, prefix: str) -> None:
        for key in list(self._store.keys()):
            if key.startswith(prefix):
                del self._store[key]


class _RedisCache:
    def __init__(self, url: str) -> None:
        import redis

        self._client = redis.from_url(url, decode_responses=True)

    def get(self, key: str) -> Optional[str]:
        return self._client.get(key)

    def set(self, key: str, value: str, ttl: int) -> None:
        self._client.set(key, value, ex=ttl)

    def delete_prefix(self, prefix: str) -> None:
        for key in self._client.scan_iter(f"{prefix}*"):
            self._client.delete(key)


_backend: _CacheBackend = _RedisCache(settings.redis_url) if settings.redis_url else _MemoryCache()


def cache_get_json(key: str) -> Optional[Any]:
    raw = _backend.get(key)
    return json.loads(raw) if raw is not None else None


def cache_set_json(key: str, value: Any, ttl: int = PUBLIC_CACHE_TTL) -> None:
    _backend.set(key, json.dumps(value), ttl)


def invalidate_public_cache(app_id: int) -> None:
    """Invalida todo o cache público de um app -- chamada pelas rotas de
    escrita do dono depois de qualquer mudança que afete o que o visitante
    do app publicado vê (config, módulos, itens, categorias)."""
    _backend.delete_prefix(f"public:{app_id}:")
