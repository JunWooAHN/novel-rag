from typing import Protocol

from toy_tune.domain.knowledge import Evidence, KnowledgeQuery, RetrievalPacket


class KnowledgeReader(Protocol):
    def query(self, request: KnowledgeQuery) -> tuple[Evidence, ...]: ...


class PacketReader(Protocol):
    def read_packet(self, packet_id: str) -> RetrievalPacket: ...
