"""Trust X-Forwarded-Proto only from the web server container (Caddy).

The backend is reachable only inside the Compose network, but any container
there could send the header. The request's scheme is changed to https only
when the direct peer is one of the trusted proxy hosts.
"""

import socket
from collections.abc import Awaitable, Callable, MutableMapping
from typing import Any

from ailms.platform import clock

Scope = MutableMapping[str, Any]
ASGIApp = Callable[[Scope, Callable[..., Awaitable[Any]], Callable[..., Awaitable[Any]]], Awaitable[None]]

_RESOLVE_SECONDS = 30


class TrustedProxyMiddleware:
    def __init__(self, app: ASGIApp, trusted_hosts: list[str]) -> None:
        self.app = app
        self.trusted_hosts = trusted_hosts
        self._addresses: set[str] = set()
        self._resolved_at: float | None = None

    def _trusted_addresses(self) -> set[str]:
        # Container addresses can change on restart, so look them up again now and then.
        now = clock.now().timestamp()
        if self._resolved_at is None or now - self._resolved_at > _RESOLVE_SECONDS:
            addresses = set(self.trusted_hosts)
            for host in self.trusted_hosts:
                try:
                    addresses.update(info[4][0] for info in socket.getaddrinfo(host, None))
                except OSError:
                    pass
            self._addresses = addresses
            self._resolved_at = now
        return self._addresses

    async def __call__(self, scope: Scope, receive: Any, send: Any) -> None:
        if scope["type"] in ("http", "websocket"):
            client = scope.get("client")
            if client and client[0] in self._trusted_addresses():
                for name, value in scope.get("headers", []):
                    if name == b"x-forwarded-proto":
                        proto = value.decode("latin-1").split(",")[0].strip().lower()
                        if proto in ("http", "https"):
                            scope = dict(scope)
                            scope["scheme"] = proto if scope["type"] == "http" else (
                                "wss" if proto == "https" else "ws"
                            )
                        break
        await self.app(scope, receive, send)
