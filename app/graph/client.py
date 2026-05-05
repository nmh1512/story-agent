"""FalkorDB raw client wrapper."""

from __future__ import annotations

import logging
from typing import Any

import falkordb

from app.core.config import settings

logger = logging.getLogger(__name__)


class GraphClient:
    """Manages a persistent connection to FalkorDB."""

    def __init__(
        self,
        host: str = settings.FALKORDB_HOST,
        port: int = settings.FALKORDB_PORT,
        graph_name: str = settings.FALKORDB_GRAPH,
    ) -> None:
        self._host = host
        self._port = port
        self._graph_name = graph_name
        self._db: falkordb.FalkorDB | None = None
        self._graph: Any = None

    def connect(self) -> None:
        """Open connection to FalkorDB."""
        self._db = falkordb.FalkorDB(host=self._host, port=self._port)
        self._graph = self._db.select_graph(self._graph_name)
        logger.info("Connected to FalkorDB graph=%s", self._graph_name)

    def query(self, cypher: str, params: dict | None = None) -> Any:
        """Execute a Cypher query and return the result set."""
        if self._graph is None:
            self.connect()
        params = params or {}
        logger.debug("FalkorDB query: %s | params=%s", cypher, params)
        return self._graph.query(cypher, params)

    def close(self) -> None:
        if self._db:
            self._db.connection.close()
            logger.info("FalkorDB connection closed")


_client: GraphClient | None = None


def get_graph_client() -> GraphClient:
    global _client
    if _client is None:
        _client = GraphClient()
        _client.connect()
    return _client
