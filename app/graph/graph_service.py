"""FalkorDB graph service — node and edge upsert + queries."""

from __future__ import annotations

import logging
from typing import Any

from app.graph.client import get_graph_client

logger = logging.getLogger(__name__)


class GraphService:
    """High-level service that maps domain objects to Cypher operations."""

    def __init__(self) -> None:
        self._client = get_graph_client()

    # ──────────────────────────────────────────────────────────
    # Initialization
    # ──────────────────────────────────────────────────────────
    def init_schema(self) -> None:
        """Create indexes on Character and Story nodes."""
        queries = [
            "CREATE INDEX FOR (c:Character) ON (c.character_id)",
            "CREATE INDEX FOR (s:Story) ON (s.story_id)",
        ]
        for q in queries:
            try:
                self._client.query(q)
            except Exception as exc:
                # Indexes may already exist
                logger.debug("Index creation skipped: %s", exc)

    # ──────────────────────────────────────────────────────────
    # Story node
    # ──────────────────────────────────────────────────────────
    def upsert_story(self, story_id: int, code: str, title: str, genre: str) -> None:
        """Merge a Story node."""
        cypher = (
            "MERGE (s:Story {story_id: $story_id}) "
            "SET s.code = $code, s.title = $title, s.genre = $genre"
        )
        self._client.query(
            cypher,
            {"story_id": story_id, "code": code, "title": title, "genre": genre},
        )
        logger.debug("Upserted Story node story_id=%d", story_id)

    # ──────────────────────────────────────────────────────────
    # Character node
    # ──────────────────────────────────────────────────────────
    def upsert_character(
        self,
        character_id: int,
        story_id: int,
        code: str,
        name: str,
        role: str,
        realm: str = "",
        status: str = "alive",
        location: str = "",
    ) -> None:
        """Merge a Character node and link it to its Story."""
        cypher = (
            "MERGE (c:Character {character_id: $character_id}) "
            "SET c.story_id = $story_id, c.code = $code, c.name = $name, "
            "    c.role = $role, c.realm = $realm, c.status = $status, c.location = $location "
            "WITH c "
            "MATCH (s:Story {story_id: $story_id}) "
            "MERGE (c)-[:BELONGS_TO]->(s)"
        )
        self._client.query(
            cypher,
            {
                "character_id": character_id,
                "story_id": story_id,
                "code": code,
                "name": name,
                "role": role,
                "realm": realm,
                "status": status,
                "location": location,
            },
        )
        logger.debug("Upserted Character node character_id=%d", character_id)

    # ──────────────────────────────────────────────────────────
    # Relationship edge
    # ──────────────────────────────────────────────────────────
    def upsert_relation(
        self,
        from_character_id: int,
        to_character_id: int,
        relation_type: str,
        trust_score: float = 0.0,
        affection_score: float = 0.0,
        hostility_score: float = 0.0,
        note: str = "",
        updated_in_chapter: int = 0,
    ) -> None:
        """Merge a RELATES_TO edge between two characters with rich properties."""
        cypher = (
            "MATCH (a:Character {character_id: $from_id}), "
            "      (b:Character {character_id: $to_id}) "
            "MERGE (a)-[r:RELATES_TO]->(b) "
            "SET r.relation_type = $relation_type, "
            "    r.trust_score = $trust_score, "
            "    r.affection_score = $affection_score, "
            "    r.hostility_score = $hostility_score, "
            "    r.note = $note, "
            "    r.updated_in_chapter = $updated_in_chapter, "
            "    r.updated_at = timestamp()"
        )
        self._client.query(
            cypher,
            {
                "from_id": from_character_id,
                "to_id": to_character_id,
                "relation_type": relation_type,
                "trust_score": trust_score,
                "affection_score": affection_score,
                "hostility_score": hostility_score,
                "note": note,
                "updated_in_chapter": updated_in_chapter,
            },
        )

    # ──────────────────────────────────────────────────────────
    # Queries
    # ──────────────────────────────────────────────────────────
    def get_relation_snapshot(self, story_id: int) -> list[dict[str, Any]]:
        """Return all RELATES_TO edges for characters in a given story."""
        cypher = (
            "MATCH (a:Character {story_id: $story_id})-[r:RELATES_TO]->(b:Character) "
            "RETURN a.character_id AS from_id, a.name AS from_name, "
            "       b.character_id AS to_id, b.name AS to_name, "
            "       r.relation_type AS relation_type, r.trust_score AS trust_score, "
            "       r.affection_score AS affection_score, r.hostility_score AS hostility_score, "
            "       r.note AS note, r.updated_in_chapter AS updated_in_chapter"
        )
        result = self._client.query(cypher, {"story_id": story_id})
        header = [h[1] if isinstance(h, list) else h for h in result.header]
        return [dict(zip(header, row)) for row in result.result_set]

    def get_character_relations(self, character_id: int) -> list[dict[str, Any]]:
        """Return all direct relationships for a character."""
        cypher = (
            "MATCH (a:Character {character_id: $character_id})-[r:RELATES_TO]->(b:Character) "
            "RETURN b.character_id AS to_id, b.name AS to_name, "
            "       r.relation_type, r.trust_score, r.affection_score, r.hostility_score, r.note"
        )
        result = self._client.query(cypher, {"character_id": character_id})
        header = [h[1] if isinstance(h, list) else h for h in result.header]
        return [dict(zip(header, row)) for row in result.result_set]

    def get_high_hostility_relations(
        self, story_id: int, threshold: float = 7.0
    ) -> list[dict[str, Any]]:
        """Return character pairs with high hostility."""
        cypher = (
            "MATCH (a:Character {story_id: $story_id})-[r:RELATES_TO]->(b:Character) "
            "WHERE r.hostility_score >= $threshold "
            "RETURN a.name, b.name, r.hostility_score, r.note"
        )
        result = self._client.query(
            cypher, {"story_id": story_id, "threshold": threshold}
        )
        header = [h[1] if isinstance(h, list) else h for h in result.header]
        return [dict(zip(header, row)) for row in result.result_set]

    def sync_relation_updates(
        self, relation_updates: list[dict], chapter_no: int
    ) -> None:
        """Bulk-upsert relation changes from a memory update."""
        for upd in relation_updates:
            self.upsert_relation(
                from_character_id=upd["from_character_id"],
                to_character_id=upd["to_character_id"],
                relation_type=upd.get("relation_type", "RELATES_TO"),
                trust_score=upd.get("trust_score", 0.0),
                affection_score=upd.get("affection_score", 0.0),
                hostility_score=upd.get("hostility_score", 0.0),
                note=upd.get("note", ""),
                updated_in_chapter=chapter_no,
            )
        logger.info("Synced %d relation updates to FalkorDB", len(relation_updates))
