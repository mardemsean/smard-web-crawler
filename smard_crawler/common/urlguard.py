"""Validates externally supplied URLs (API/MCP boundary): http(s) only, no private/internal targets."""

from __future__ import annotations

import asyncio
import ipaddress
import os
import socket
from urllib.parse import urlsplit


class UnsafeURL(ValueError):
    pass


def _allow_private() -> bool:
    return os.getenv("SMARD_ALLOW_PRIVATE", "false").lower() == "true"


def _is_public(ip: str) -> bool:
    addr = ipaddress.ip_address(ip)
    if isinstance(addr, ipaddress.IPv6Address) and addr.ipv4_mapped:
        addr = addr.ipv4_mapped
    return addr.is_global and not addr.is_multicast


async def validate_url(url: str) -> str:
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https"):
        raise UnsafeURL(f"only http(s) URLs are allowed: {url}")
    if not parts.hostname:
        raise UnsafeURL(f"URL has no host: {url}")
    if _allow_private():
        return url
    try:
        infos = await asyncio.get_running_loop().getaddrinfo(parts.hostname, parts.port or 443, type=socket.SOCK_STREAM)
    except socket.gaierror as e:
        raise UnsafeURL(f"cannot resolve {parts.hostname}: {e}") from e
    for info in infos:
        ip = info[4][0]
        if not _is_public(ip):
            raise UnsafeURL(f"{parts.hostname} resolves to non-public address {ip} (set SMARD_ALLOW_PRIVATE=true to allow)")
    return url
