from __future__ import annotations

from zeroconf import ServiceInfo
from zeroconf.asyncio import AsyncZeroconf


class MDNSAdvertiser:
    def __init__(self, hostname: str, port: int) -> None:
        self.hostname = hostname
        self.port = port
        self.zeroconf: AsyncZeroconf | None = None
        self.info: ServiceInfo | None = None
        self.started = False

    async def start(self) -> None:
        self.started = False
        self.zeroconf = AsyncZeroconf()
        self.info = ServiceInfo(
            type_="_freetopify._tcp.local.",
            name=f"{self.hostname}._freetopify._tcp.local.",
            addresses=[b"\x7f\x00\x00\x01"],
            port=self.port,
            properties={"path": "/api/v1/system/health"},
            server=f"{self.hostname}.local.",
        )
        try:
            await self.zeroconf.async_register_service(self.info)
            self.started = True
        except Exception:
            # Clean up partially initialized zeroconf state and re-raise.
            try:
                await self.zeroconf.async_close()
            except Exception:
                pass
            self.zeroconf = None
            self.info = None
            raise

    async def stop(self) -> None:
        if not self.zeroconf:
            return

        try:
            if self.started and self.info:
                await self.zeroconf.async_unregister_service(self.info)
        finally:
            await self.zeroconf.async_close()
            self.started = False
            self.zeroconf = None
            self.info = None
