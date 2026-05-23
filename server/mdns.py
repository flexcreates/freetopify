from __future__ import annotations

from zeroconf import ServiceInfo, Zeroconf


class MDNSAdvertiser:
    def __init__(self, hostname: str, port: int) -> None:
        self.hostname = hostname
        self.port = port
        self.zeroconf: Zeroconf | None = None
        self.info: ServiceInfo | None = None

    def start(self) -> None:
        self.zeroconf = Zeroconf()
        self.info = ServiceInfo(
            type_="_freetopify._tcp.local.",
            name=f"{self.hostname}._freetopify._tcp.local.",
            addresses=[b"\x7f\x00\x00\x01"],
            port=self.port,
            properties={"path": "/api/v1/system/health"},
            server=f"{self.hostname}.local.",
        )
        self.zeroconf.register_service(self.info)

    def stop(self) -> None:
        if self.zeroconf and self.info:
            self.zeroconf.unregister_service(self.info)
            self.zeroconf.close()
