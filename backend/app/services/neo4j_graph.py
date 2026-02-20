"""Neo4j graph service for part data and substitution queries."""

from __future__ import annotations

import random
import re
import time
from collections import defaultdict
from typing import Any

from neo4j import GraphDatabase

from app.models import BomItem, SubstituteCandidate
from app.state import runtime_state
from app.tracing import tracer

CHAOS_QUERY_DELAY_SECONDS = 1.5


class Neo4jGraph:
    """Wrapper around the Neo4j driver for graph operations."""

    def __init__(self, uri: str, username: str, password: str) -> None:
        self._driver = GraphDatabase.driver(uri, auth=(username, password))

    def close(self) -> None:
        self._driver.close()

    @staticmethod
    def normalize_value(value: str | None) -> str:
        if not value:
            return ""

        normalized = value.strip().lower()
        normalized = normalized.replace("ohms", "ohm")
        normalized = re.sub(r"[\s_-]+", "", normalized)
        return normalized

    @staticmethod
    def normalize_package(package: str | None) -> str:
        if not package:
            return ""
        return re.sub(r"[\s_-]+", "", package.strip().upper())

    @staticmethod
    def _normalize_type(part_type: str | None) -> str:
        if not part_type:
            return ""
        return part_type.strip().lower()

    def _build_seed_parts(self) -> list[dict[str, Any]]:
        rng = random.Random(42)
        manufacturers = [
            "Texas Instruments",
            "Analog Devices",
            "STMicroelectronics",
            "NXP",
            "Murata",
            "Yageo",
            "Samsung Electro-Mechanics",
            "ON Semiconductor",
            "ROHM",
            "Infineon",
        ]

        resistor_values = ["1k", "2.2k", "4.7k", "10k", "22k", "47k", "100k", "1M"]
        capacitor_values = ["10nF", "47nF", "100nF", "1uF", "4.7uF", "10uF", "22uF"]
        regulator_values = ["1.8V", "3.3V", "5V", "12V"]

        parts: list[dict[str, Any]] = []
        sequence = 1

        type_specs: list[tuple[str, int]] = [
            ("resistor", 48),
            ("capacitor", 36),
            ("regulator", 24),
        ]

        for part_type, count in type_specs:
            for _ in range(count):
                if part_type == "resistor":
                    value = rng.choice(resistor_values)
                    package = rng.choice(["0402", "0603", "0805", "1206"])
                    voltage = None
                    tolerance = rng.choice(["0.5%", "1%", "2%", "5%"])
                    prefix = "RES"
                elif part_type == "capacitor":
                    value = rng.choice(capacitor_values)
                    package = rng.choice(["0402", "0603", "0805", "1206"])
                    voltage = rng.choice(["6.3V", "10V", "16V", "25V", "50V"])
                    tolerance = rng.choice(["5%", "10%", "20%"])
                    prefix = "CAP"
                else:
                    value = rng.choice(regulator_values)
                    package = rng.choice(["SOT-23", "SOT-223", "TO-252"])
                    voltage = value
                    tolerance = None
                    prefix = "REG"

                mpn = f"DEMO-{prefix}-{sequence:04d}"
                sequence += 1

                parts.append(
                    {
                        "mpn": mpn,
                        "manufacturer": rng.choice(manufacturers),
                        "type": part_type,
                        "value": value,
                        "package": package,
                        "norm_value": self.normalize_value(value),
                        "norm_package": self.normalize_package(package),
                        "voltage": voltage,
                        "tolerance": tolerance,
                    }
                )

        return parts

    def _build_seed_relationships(
        self, parts: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        rng = random.Random(99)
        reasons = [
            "Equivalent electrical behavior",
            "Pin-compatible alternative",
            "Qualified alternate vendor",
            "Stock balancing substitute",
        ]

        by_signature: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
        for part in parts:
            key = (part["type"], part["norm_package"], part["norm_value"])
            by_signature[key].append(part)

        relationships: list[dict[str, Any]] = []
        for group_parts in by_signature.values():
            if len(group_parts) < 2:
                continue

            ordered = sorted(group_parts, key=lambda p: p["mpn"])
            for index, source in enumerate(ordered):
                primary_target = ordered[(index + 1) % len(ordered)]
                if source["mpn"] != primary_target["mpn"]:
                    relationships.append(
                        {
                            "from_mpn": source["mpn"],
                            "to_mpn": primary_target["mpn"],
                            "reason": rng.choice(reasons),
                            "confidence": round(rng.uniform(0.7, 0.98), 2),
                        }
                    )

                if len(ordered) > 3:
                    secondary_target = ordered[(index + 2) % len(ordered)]
                    if source["mpn"] != secondary_target["mpn"]:
                        relationships.append(
                            {
                                "from_mpn": source["mpn"],
                                "to_mpn": secondary_target["mpn"],
                                "reason": rng.choice(reasons),
                                "confidence": round(rng.uniform(0.6, 0.9), 2),
                            }
                        )

        return relationships

    def seed_demo_data(self) -> dict[str, int]:
        constraints = [
            "CREATE CONSTRAINT part_mpn_unique IF NOT EXISTS FOR (p:Part) REQUIRE p.mpn IS UNIQUE",
            "CREATE INDEX part_type_idx IF NOT EXISTS FOR (p:Part) ON (p.type)",
            "CREATE INDEX part_package_idx IF NOT EXISTS FOR (p:Part) ON (p.package)",
            "CREATE INDEX part_value_idx IF NOT EXISTS FOR (p:Part) ON (p.value)",
            "CREATE INDEX part_norm_lookup_idx IF NOT EXISTS FOR (p:Part) ON (p.type, p.norm_package, p.norm_value)",
        ]

        parts = self._build_seed_parts()
        relationships = self._build_seed_relationships(parts)

        with self._driver.session() as session:
            for statement in constraints:
                session.run(statement).consume()

            session.run(
                "MATCH (p:Part) WHERE p.mpn STARTS WITH 'DEMO-' DETACH DELETE p"
            ).consume()

            session.run(
                """
                UNWIND $parts AS part
                MERGE (p:Part {mpn: part.mpn})
                SET p.manufacturer = part.manufacturer,
                    p.type = part.type,
                    p.value = part.value,
                    p.package = part.package,
                    p.norm_value = part.norm_value,
                    p.norm_package = part.norm_package,
                    p.voltage = part.voltage,
                    p.tolerance = part.tolerance
                """,
                parts=parts,
            ).consume()

            session.run(
                """
                UNWIND $relationships AS rel
                MATCH (source:Part {mpn: rel.from_mpn})
                MATCH (target:Part {mpn: rel.to_mpn})
                MERGE (source)-[r:SUBSTITUTES_FOR]->(target)
                SET r.reason = rel.reason,
                    r.confidence = rel.confidence
                """,
                relationships=relationships,
            ).consume()

            parts_total = session.run("MATCH (p:Part) RETURN count(p) AS count").single()
            rel_total = session.run(
                "MATCH (:Part)-[r:SUBSTITUTES_FOR]->(:Part) RETURN count(r) AS count"
            ).single()

        return {
            "parts_seeded": len(parts),
            "relationships_seeded": len(relationships),
            "parts_total": int(parts_total["count"]) if parts_total else 0,
            "relationships_total": int(rel_total["count"]) if rel_total else 0,
        }

    def _score_candidate(
        self,
        item: BomItem,
        candidate_type: str | None,
        candidate_package: str | None,
        candidate_value: str | None,
        relationship_confidence: float | None,
    ) -> tuple[int, list[str]]:
        score = 0
        score_reasons: list[str] = []

        if self._normalize_type(candidate_type) == self._normalize_type(item.type):
            score += 40
            score_reasons.append("same type")

        if self.normalize_package(candidate_package) == self.normalize_package(item.package):
            score += 30
            score_reasons.append("same package")

        if self.normalize_value(candidate_value) == self.normalize_value(item.value):
            score += 20
            score_reasons.append("same normalized value")

        if relationship_confidence is not None and relationship_confidence > 0.8:
            score += 10
            score_reasons.append("high relationship confidence")

        return min(score, 100), score_reasons

    def _candidate_from_record(
        self,
        item: BomItem,
        record: dict[str, Any],
        fallback_reason: str,
    ) -> SubstituteCandidate:
        relationship_confidence = record.get("rel_confidence")
        score, score_reasons = self._score_candidate(
            item=item,
            candidate_type=record.get("type"),
            candidate_package=record.get("package"),
            candidate_value=record.get("value"),
            relationship_confidence=relationship_confidence,
        )

        reason_parts: list[str] = []
        if record.get("rel_reason"):
            reason_parts.append(str(record["rel_reason"]))
        if score_reasons:
            reason_parts.append(", ".join(score_reasons))

        reason = "; ".join(reason_parts) if reason_parts else fallback_reason

        return SubstituteCandidate(
            mpn=str(record["mpn"]),
            manufacturer=record.get("manufacturer"),
            value=str(record.get("value") or ""),
            package=str(record.get("package") or "unknown"),
            score=score,
            reason=reason,
        )

    def find_substitutes(self, item: BomItem, limit: int = 5) -> list[SubstituteCandidate]:
        chaos_mode = runtime_state.is_chaos_mode()

        with tracer.trace("neo4j.find_substitutes") as span:
            span.set_tag("item.type", item.type)
            span.set_tag("item.package", item.package or "")
            span.set_tag("chaos_mode", chaos_mode)

            if chaos_mode:
                time.sleep(CHAOS_QUERY_DELAY_SECONDS)

            normalized_type = self._normalize_type(item.type)
            normalized_value = self.normalize_value(item.value)
            normalized_package = self.normalize_package(item.package)

            query_args = {
                "type": normalized_type,
                "norm_value": normalized_value,
                "norm_package": normalized_package,
                "limit": limit,
            }

            direct_query = """
            MATCH (candidate:Part)-[rel:SUBSTITUTES_FOR]->(target:Part)
            WHERE toLower(target.type) = $type
              AND ($norm_value = '' OR target.norm_value = $norm_value)
              AND ($norm_package = '' OR target.norm_package = $norm_package)
            RETURN candidate.mpn AS mpn,
                   candidate.manufacturer AS manufacturer,
                   candidate.type AS type,
                   candidate.value AS value,
                   candidate.package AS package,
                   rel.reason AS rel_reason,
                   rel.confidence AS rel_confidence
            ORDER BY rel.confidence DESC, candidate.mpn
            LIMIT $limit
            """

            fallback_query = """
            MATCH (candidate:Part)
            WHERE toLower(candidate.type) = $type
              AND ($norm_value = '' OR candidate.norm_value = $norm_value)
              AND ($norm_package = '' OR candidate.norm_package = $norm_package)
            RETURN candidate.mpn AS mpn,
                   candidate.manufacturer AS manufacturer,
                   candidate.type AS type,
                   candidate.value AS value,
                   candidate.package AS package,
                   null AS rel_reason,
                   null AS rel_confidence
            ORDER BY candidate.mpn
            LIMIT $limit
            """

            candidates: list[SubstituteCandidate]
            with self._driver.session() as session:
                direct_records = [
                    dict(record) for record in session.run(direct_query, **query_args)
                ]
                if direct_records:
                    candidates = [
                        self._candidate_from_record(
                            item=item,
                            record=record,
                            fallback_reason="Direct substitute match",
                        )
                        for record in direct_records
                    ]
                else:
                    fallback_records = [
                        dict(record) for record in session.run(fallback_query, **query_args)
                    ]
                    candidates = [
                        self._candidate_from_record(
                            item=item,
                            record=record,
                            fallback_reason="Matched by type, package, and value",
                        )
                        for record in fallback_records
                    ]

            span.set_tag("candidates_count", len(candidates))
            return candidates
