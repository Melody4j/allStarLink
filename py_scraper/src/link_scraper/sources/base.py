"""
Base protocols for pluggable data sources.
"""

from typing import Any, Dict, List, Optional, Protocol

from ..domain.models import CanonicalNodeBundle
from ..models.connection import Connection
from ..models.node import Node


class SourceClient(Protocol):
    async def fetch_node_list(self) -> Optional[Dict[str, Any]]:
        """Fetch the online node list payload."""

    async def fetch_node_detail(self, node_id: int) -> Optional[Dict[str, Any]]:
        """Fetch a single node detail payload."""

    async def close(self) -> None:
        """Release any network resources held by the client."""


class SourceParser(Protocol):
    def parse_node(self, data: Dict[str, Any]) -> Optional[Node]:
        """Parse a primary node from a detail payload."""

    def parse_linked_node(self, linked_node: Dict[str, Any]) -> Optional[Node]:
        """Parse a linked node from a detail payload."""

    def parse_connections(
        self,
        node_id: int,
        connection_modes: str,
        linked_nodes: List[Dict[str, Any]],
        batch_no: Optional[str] = None,
    ) -> List[Connection]:
        """Parse topology relationships from a detail payload."""


class SourceMapper(Protocol):
    def map_node_list(self, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Map a raw node list payload into queue-ready items."""

    def map_node_detail(
        self,
        payload: Dict[str, Any],
        batch_no: Optional[str] = None,
    ) -> Optional[CanonicalNodeBundle]:
        """Map a raw detail payload into a canonical aggregate."""
