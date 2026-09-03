# -*- coding: utf-8 -*-
"""Web dashboard for exploring the kg-diabet Neo4j knowledge graph.

Run with::

    python app.py

The app prefers the live Neo4j database.  If Neo4j is unavailable, read-only
queries transparently fall back to the processed JSON snapshot so the UI stays
useful (and clearly reports that it is showing snapshot data).
"""

from __future__ import annotations

import hashlib
import json
import os
import socket
import time
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

from flask import Flask, jsonify, request
from neo4j import GraphDatabase

import config


BASE_DIR = Path(__file__).resolve().parent
WEB_DIR = BASE_DIR / "web"

NODE_TYPES = {
    "Disease": {"name": "Bệnh", "plural": "Bệnh lý", "color": "#0D9488"},
    "Drug": {"name": "Thuốc", "plural": "Thuốc", "color": "#2563EB"},
    "Symptom": {"name": "Triệu chứng", "plural": "Triệu chứng", "color": "#F59E0B"},
    "LabTest": {"name": "Xét nghiệm", "plural": "Xét nghiệm", "color": "#8B5CF6"},
    "Complication": {"name": "Biến chứng", "plural": "Biến chứng", "color": "#EF4444"},
    "RiskFactor": {"name": "Yếu tố nguy cơ", "plural": "Yếu tố nguy cơ", "color": "#F97316"},
    "SideEffect": {"name": "Tác dụng phụ", "plural": "Tác dụng phụ", "color": "#EC4899"},
    "DrugCategory": {"name": "Nhóm thuốc", "plural": "Nhóm thuốc", "color": "#14B8A6"},
}

RELATION_NAMES = {
    "HAS_SYMPTOM": "có triệu chứng",
    "TREATED_BY": "điều trị bằng",
    "DIAGNOSED_BY": "chẩn đoán bằng",
    "INCREASES_RISK_OF": "làm tăng nguy cơ",
    "HAS_SIDE_EFFECT": "có tác dụng phụ",
    "BELONGS_TO": "thuộc nhóm",
    "CONTRAINDICATED_WITH": "cảnh báo phối hợp",
    "CAUSES": "gây biến chứng",
    "DETECTED_BY": "phát hiện bằng",
}

ENTITY_GROUPS = {
    "diseases": "Disease",
    "drugs": "Drug",
    "symptoms": "Symptom",
    "lab_tests": "LabTest",
    "complications": "Complication",
    "risk_factors": "RiskFactor",
    "side_effects": "SideEffect",
    "drug_categories": "DrugCategory",
}


def _json_value(value: Any) -> Any:
    """Convert Neo4j temporal/scalar values into JSON-safe values."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(k): _json_value(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_value(v) for v in value]
    if hasattr(value, "iso_format"):
        return value.iso_format()
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _normalise(text: Any) -> str:
    value = unicodedata.normalize("NFD", str(text or "").lower())
    value = "".join(ch for ch in value if unicodedata.category(ch) != "Mn")
    return value.replace("đ", "d").strip()


def _clean_properties(properties: dict[str, Any]) -> dict[str, Any]:
    return {
        str(key): _json_value(value)
        for key, value in properties.items()
        if value not in (None, "", [], {})
    }


def _snapshot_id(label: str, name: str) -> str:
    digest = hashlib.sha1(f"{label}\0{name}".encode("utf-8")).hexdigest()[:14]
    return f"snapshot:{label}:{digest}"


class SnapshotStore:
    """In-memory, read-only view of ``data/processed/*.json``."""

    def __init__(self, entities_path: Path, relations_path: Path) -> None:
        self.entities_path = entities_path
        self.relations_path = relations_path
        self.nodes: list[dict[str, Any]] = []
        self.edges: list[dict[str, Any]] = []
        self.by_id: dict[str, dict[str, Any]] = {}
        self.by_key: dict[tuple[str, str], dict[str, Any]] = {}
        self.adjacency: dict[str, list[tuple[dict[str, Any], str]]] = defaultdict(list)
        self.loaded_at = 0.0
        self._mtimes = (0.0, 0.0)
        self.reload()

    def _ensure_current(self) -> None:
        mtimes = (
            self.entities_path.stat().st_mtime,
            self.relations_path.stat().st_mtime,
        )
        if mtimes != self._mtimes:
            self.reload()

    def reload(self) -> None:
        entities = json.loads(self.entities_path.read_text(encoding="utf-8"))
        relations = json.loads(self.relations_path.read_text(encoding="utf-8"))

        nodes: list[dict[str, Any]] = []
        by_key: dict[tuple[str, str], dict[str, Any]] = {}
        for group, label in ENTITY_GROUPS.items():
            for raw in entities.get(group, []):
                name = str(raw.get("name") or "Chưa đặt tên").strip()
                key = (label, name.casefold())
                if key in by_key:
                    by_key[key]["properties"].update(_clean_properties(raw))
                    continue
                node = {
                    "id": _snapshot_id(label, name),
                    "label": label,
                    "name": name,
                    "properties": _clean_properties(raw),
                    "degree": 0,
                }
                nodes.append(node)
                by_key[key] = node

        # Relations can introduce reference drugs that are not in entities.json.
        for raw in relations:
            for side in ("from", "to"):
                label = str(raw.get(f"{side}_type") or "Unknown")
                name = str(raw.get(f"{side}_name") or "Chưa đặt tên").strip()
                key = (label, name.casefold())
                if key not in by_key:
                    node = {
                        "id": _snapshot_id(label, name),
                        "label": label,
                        "name": name,
                        "properties": {"name": name},
                        "degree": 0,
                    }
                    nodes.append(node)
                    by_key[key] = node

        edges: list[dict[str, Any]] = []
        adjacency: dict[str, list[tuple[dict[str, Any], str]]] = defaultdict(list)
        for index, raw in enumerate(relations):
            source = by_key.get((str(raw.get("from_type")), str(raw.get("from_name", "")).casefold()))
            target = by_key.get((str(raw.get("to_type")), str(raw.get("to_name", "")).casefold()))
            if not source or not target:
                continue
            edge = {
                "id": f"snapshot-edge:{index}",
                "source": source["id"],
                "target": target["id"],
                "type": str(raw.get("relation") or "RELATED_TO"),
                "properties": _clean_properties(raw.get("properties") or {}),
            }
            if raw.get("source_url"):
                edge["properties"]["source_url"] = raw["source_url"]
            edges.append(edge)
            source["degree"] += 1
            target["degree"] += 1
            adjacency[source["id"]].append((edge, target["id"]))
            adjacency[target["id"]].append((edge, source["id"]))

        self.nodes = nodes
        self.edges = edges
        self.by_id = {node["id"]: node for node in nodes}
        self.by_key = by_key
        self.adjacency = adjacency
        self.loaded_at = time.time()
        self._mtimes = (
            self.entities_path.stat().st_mtime,
            self.relations_path.stat().st_mtime,
        )

    @staticmethod
    def _copy_node(node: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": node["id"],
            "label": node["label"],
            "name": node["name"],
            "properties": dict(node["properties"]),
            "degree": node["degree"],
        }

    def stats(self) -> dict[str, Any]:
        self._ensure_current()
        label_counts = Counter(node["label"] for node in self.nodes)
        relation_counts = Counter(edge["type"] for edge in self.edges)
        top_nodes = sorted(self.nodes, key=lambda node: (-node["degree"], node["name"]))[:8]
        return {
            "totals": {"nodes": len(self.nodes), "relationships": len(self.edges)},
            "labels": [
                {"label": label, "count": count}
                for label, count in sorted(label_counts.items(), key=lambda item: (-item[1], item[0]))
            ],
            "relationships": [
                {"type": rel_type, "count": count}
                for rel_type, count in sorted(relation_counts.items(), key=lambda item: (-item[1], item[0]))
            ],
            "top_nodes": [self._copy_node(node) for node in top_nodes],
        }

    def search(self, query: str, label: str, page: int, page_size: int) -> dict[str, Any]:
        self._ensure_current()
        needle = _normalise(query)
        matches = [
            node
            for node in self.nodes
            if (not label or node["label"] == label)
            and (
                not needle
                or needle in _normalise(node["name"])
                or any(needle in _normalise(value) for value in node["properties"].values())
            )
        ]
        matches.sort(
            key=lambda node: (
                0 if needle and _normalise(node["name"]).startswith(needle) else 1,
                -node["degree"],
                node["name"].casefold(),
            )
        )
        start = (page - 1) * page_size
        return {
            "items": [self._copy_node(node) for node in matches[start : start + page_size]],
            "total": len(matches),
            "page": page,
            "page_size": page_size,
        }

    def graph(self, query: str, label: str, limit: int, edge_limit: int) -> dict[str, Any]:
        self._ensure_current()
        needle = _normalise(query)
        candidates = [
            node
            for node in self.nodes
            if (not label or node["label"] == label)
            and (not needle or needle in _normalise(node["name"]))
        ]
        candidates.sort(key=lambda node: (-node["degree"], node["name"].casefold()))

        # Search/filter results are seeds; bring their neighbours into view so
        # the graph remains meaningful instead of showing isolated matches.
        selected: dict[str, dict[str, Any]] = {}
        seed_cap = min(len(candidates), limit if not (query or label) else max(1, limit // 3))
        for node in candidates[:seed_cap]:
            selected[node["id"]] = node
        if query or label:
            neighbours: list[dict[str, Any]] = []
            seen = set(selected)
            for node in candidates[:seed_cap]:
                for _, neighbour_id in self.adjacency.get(node["id"], []):
                    if neighbour_id not in seen:
                        seen.add(neighbour_id)
                        neighbours.append(self.by_id[neighbour_id])
            neighbours.sort(key=lambda node: (-node["degree"], node["name"].casefold()))
            for node in neighbours:
                if len(selected) >= limit:
                    break
                selected[node["id"]] = node
        else:
            for node in candidates[seed_cap:limit]:
                selected[node["id"]] = node

        selected_ids = set(selected)
        graph_edges = [
            dict(edge)
            for edge in self.edges
            if edge["source"] in selected_ids and edge["target"] in selected_ids
        ][:edge_limit]
        return {
            "nodes": [self._copy_node(node) for node in selected.values()],
            "edges": graph_edges,
            "truncated": len(candidates) > limit or len(graph_edges) >= edge_limit,
        }

    def node(self, node_id: str, neighbour_limit: int = 60) -> dict[str, Any] | None:
        self._ensure_current()
        node = self.by_id.get(node_id)
        if not node:
            return None
        connections = sorted(
            self.adjacency.get(node_id, []),
            key=lambda item: (-self.by_id[item[1]]["degree"], self.by_id[item[1]]["name"]),
        )[:neighbour_limit]
        related = []
        for edge, neighbour_id in connections:
            related.append(
                {
                    "edge": dict(edge),
                    "node": self._copy_node(self.by_id[neighbour_id]),
                    "direction": "out" if edge["source"] == node_id else "in",
                }
            )
        return {"node": self._copy_node(node), "related": related}


class Neo4jStore:
    """Small data-access layer with an offline circuit breaker."""

    def __init__(self) -> None:
        self.driver = None
        self.offline_until = 0.0
        self.last_error = ""

    def _get_driver(self):
        if time.monotonic() < self.offline_until:
            raise ConnectionError(self.last_error or "Neo4j đang ngoại tuyến")
        if self.driver is None:
            timeout = float(os.getenv("NEO4J_CONNECTION_TIMEOUT", "2"))
            self.driver = GraphDatabase.driver(
                config.NEO4J_URI,
                auth=(config.NEO4J_USER, config.NEO4J_PASSWORD),
                connection_timeout=timeout,
                connection_acquisition_timeout=timeout,
                max_transaction_retry_time=1,
            )
        return self.driver

    def _run(self, cypher: str, **parameters: Any) -> list[dict[str, Any]]:
        try:
            driver = self._get_driver()
            with driver.session(database=config.NEO4J_DATABASE) as session:
                records = [record.data() for record in session.run(cypher, **parameters)]
            self.last_error = ""
            return records
        except Exception as exc:
            self.last_error = f"{type(exc).__name__}: {exc}"
            self.offline_until = time.monotonic() + 8
            if self.driver is not None:
                try:
                    self.driver.close()
                except Exception:
                    pass
                self.driver = None
            raise ConnectionError(self.last_error) from exc

    def health(self) -> dict[str, Any]:
        self._run("RETURN 1 AS ok")
        return {"online": True, "database": config.NEO4J_DATABASE}

    @staticmethod
    def _node(record: dict[str, Any]) -> dict[str, Any]:
        props = _clean_properties(record.get("properties") or {})
        label = str(record.get("label") or "Unknown")
        return {
            "id": str(record["id"]),
            "label": label,
            "name": str(props.get("name") or "Chưa đặt tên"),
            "properties": props,
            "degree": int(record.get("degree") or 0),
        }

    def stats(self) -> dict[str, Any]:
        totals = self._run(
            "MATCH (n) WITH count(n) AS nodes "
            "OPTIONAL MATCH ()-[r]->() RETURN nodes, count(r) AS relationships"
        )[0]
        labels = self._run(
            "MATCH (n) UNWIND labels(n) AS label "
            "RETURN label, count(*) AS count ORDER BY count DESC, label"
        )
        relationships = self._run(
            "MATCH ()-[r]->() RETURN type(r) AS type, count(*) AS count "
            "ORDER BY count DESC, type"
        )
        top_rows = self._run(
            "MATCH (n) OPTIONAL MATCH (n)--(m) "
            "WITH n, count(m) AS degree ORDER BY degree DESC LIMIT 8 "
            "RETURN elementId(n) AS id, labels(n)[0] AS label, "
            "properties(n) AS properties, degree"
        )
        return {
            "totals": {"nodes": totals["nodes"], "relationships": totals["relationships"]},
            "labels": labels,
            "relationships": relationships,
            "top_nodes": [self._node(row) for row in top_rows],
        }

    def search(self, query: str, label: str, page: int, page_size: int) -> dict[str, Any]:
        # Normalise in Python so Vietnamese searches work both with and without
        # tone marks (Neo4j's built-in toLower is case-insensitive, not accent-
        # insensitive).  This KG is deliberately compact, so reading the label
        # slice is faster and simpler than requiring an APOC/full-text plugin.
        rows = self._run(
            "MATCH (n) WHERE ($label = '' OR $label IN labels(n)) OPTIONAL MATCH (n)--(m) "
            "WITH n, count(m) AS degree "
            "RETURN elementId(n) AS id, labels(n)[0] AS label, properties(n) AS properties, degree "
            "ORDER BY degree DESC, toLower(coalesce(n.name, '')) LIMIT 5000",
            label=label,
        )
        needle = _normalise(query)
        nodes = [self._node(row) for row in rows]
        matches = [
            node
            for node in nodes
            if not needle
            or needle in _normalise(node["name"])
            or any(needle in _normalise(value) for value in node["properties"].values())
        ]
        matches.sort(
            key=lambda node: (
                0 if needle and _normalise(node["name"]).startswith(needle) else 1,
                -node["degree"],
                node["name"].casefold(),
            )
        )
        start = (page - 1) * page_size
        return {
            "items": matches[start : start + page_size],
            "total": len(matches),
            "page": page,
            "page_size": page_size,
        }

    def graph(self, query: str, label: str, limit: int, edge_limit: int) -> dict[str, Any]:
        if query:
            candidate_rows = self._run(
                "MATCH (n) WHERE ($label = '' OR $label IN labels(n)) "
                "OPTIONAL MATCH (n)--(m) WITH n, count(m) AS degree "
                "RETURN elementId(n) AS id, labels(n)[0] AS label, "
                "properties(n) AS properties, degree ORDER BY degree DESC LIMIT 5000",
                label=label,
            )
            needle = _normalise(query)
            seed_ids = [
                str(row["id"])
                for row in candidate_rows
                if needle in _normalise((row.get("properties") or {}).get("name"))
            ][: max(1, limit // 3)]
            if not seed_ids:
                return {"nodes": [], "edges": [], "truncated": False}
            seed_match = "MATCH (n) WHERE elementId(n) IN $seed_ids"
            seed_parameters = {"seed_ids": seed_ids}
        else:
            seed_match = (
                "MATCH (n) WHERE ($label = '' OR $label IN labels(n)) "
                "OPTIONAL MATCH (n)--(matched) WITH n, count(matched) AS matched_degree "
                "ORDER BY matched_degree DESC LIMIT $seed_limit"
            )
            seed_parameters = {"label": label, "seed_limit": limit if not label else max(1, limit // 3)}

        rows = self._run(
            seed_match + " "
            "WITH collect(n) AS seeds UNWIND seeds AS seed "
            "OPTIONAL MATCH (seed)--(near) "
            "WITH seeds + collect(DISTINCT near) AS pool UNWIND pool AS n "
            "WITH DISTINCT n WHERE n IS NOT NULL "
            "OPTIONAL MATCH (n)--(m) WITH n, count(m) AS degree "
            "ORDER BY degree DESC LIMIT $limit "
            "RETURN elementId(n) AS id, labels(n)[0] AS label, properties(n) AS properties, degree",
            **seed_parameters,
            limit=limit,
        )
        nodes = [self._node(row) for row in rows]
        ids = [node["id"] for node in nodes]
        edge_rows = self._run(
            "MATCH (a)-[r]->(b) WHERE elementId(a) IN $ids AND elementId(b) IN $ids "
            "RETURN elementId(r) AS id, elementId(a) AS source, elementId(b) AS target, "
            "type(r) AS type, properties(r) AS properties LIMIT $limit",
            ids=ids,
            limit=edge_limit,
        ) if ids else []
        return {
            "nodes": nodes,
            "edges": [
                {
                    "id": str(row["id"]),
                    "source": str(row["source"]),
                    "target": str(row["target"]),
                    "type": str(row["type"]),
                    "properties": _clean_properties(row.get("properties") or {}),
                }
                for row in edge_rows
            ],
            "truncated": len(nodes) >= limit or len(edge_rows) >= edge_limit,
        }

    def node(self, node_id: str, neighbour_limit: int = 60) -> dict[str, Any] | None:
        rows = self._run(
            "MATCH (n) WHERE elementId(n) = $id "
            "OPTIONAL MATCH (n)-[r]-(m) "
            "WITH n, r, m, CASE WHEN startNode(r) = n THEN 'out' ELSE 'in' END AS direction "
            "LIMIT $limit "
            "RETURN elementId(n) AS id, labels(n)[0] AS label, properties(n) AS properties, "
            "r IS NOT NULL AS has_relation, elementId(r) AS edge_id, type(r) AS edge_type, "
            "properties(r) AS edge_properties, direction, elementId(m) AS neighbour_id, "
            "labels(m)[0] AS neighbour_label, properties(m) AS neighbour_properties",
            id=node_id,
            limit=neighbour_limit,
        )
        if not rows:
            return None
        first = rows[0]
        node = self._node(
            {
                "id": first["id"],
                "label": first["label"],
                "properties": first["properties"],
                "degree": sum(1 for row in rows if row["has_relation"]),
            }
        )
        related = []
        for row in rows:
            if not row["has_relation"]:
                continue
            neighbour = self._node(
                {
                    "id": row["neighbour_id"],
                    "label": row["neighbour_label"],
                    "properties": row["neighbour_properties"],
                }
            )
            edge = {
                "id": str(row["edge_id"]),
                "source": node_id if row["direction"] == "out" else neighbour["id"],
                "target": neighbour["id"] if row["direction"] == "out" else node_id,
                "type": str(row["edge_type"]),
                "properties": _clean_properties(row.get("edge_properties") or {}),
            }
            related.append({"edge": edge, "node": neighbour, "direction": row["direction"]})
        return {"node": node, "related": related}


snapshot_store = SnapshotStore(Path(config.ENTITIES_JSON), Path(config.RELATIONS_JSON))
neo4j_store = Neo4jStore()


def _with_source(method: str, *args: Any, **kwargs: Any) -> dict[str, Any] | None:
    if method == "node" and args and str(args[0]).startswith("snapshot:"):
        data = snapshot_store.node(str(args[0]))
        if data is not None:
            data["meta"] = {
                "source": "snapshot",
                "database_online": False,
                "message": "Đang xem thực thể từ snapshot JSON.",
            }
        return data
    try:
        data = getattr(neo4j_store, method)(*args, **kwargs)
        if data is not None:
            data["meta"] = {"source": "neo4j", "database_online": True}
        return data
    except ConnectionError:
        data = getattr(snapshot_store, method)(*args, **kwargs)
        if data is not None:
            data["meta"] = {
                "source": "snapshot",
                "database_online": False,
                "message": "Neo4j chưa kết nối — đang hiển thị snapshot JSON gần nhất.",
            }
        return data


app = Flask(__name__, static_folder=str(WEB_DIR), static_url_path="")
app.json.ensure_ascii = False
app.config["JSON_SORT_KEYS"] = False


@app.after_request
def add_security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    if request.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    return response


@app.get("/")
def index():
    return app.send_static_file("index.html")


@app.get("/api/config")
def api_config():
    return jsonify({"node_types": NODE_TYPES, "relation_names": RELATION_NAMES})


@app.get("/api/health")
def api_health():
    try:
        database = neo4j_store.health()
        database.update({"source": "neo4j", "message": "Đã kết nối Neo4j"})
    except ConnectionError:
        database = {
            "online": False,
            "database": config.NEO4J_DATABASE,
            "source": "snapshot",
            "message": "Neo4j chưa kết nối — snapshot JSON vẫn sẵn sàng.",
        }
    return jsonify({"status": "ok", "database": database})


@app.get("/api/stats")
def api_stats():
    return jsonify(_with_source("stats"))


def _bounded_int(value: str | None, default: int, minimum: int, maximum: int) -> int:
    try:
        return max(minimum, min(maximum, int(value or default)))
    except (TypeError, ValueError):
        return default


def _label_arg() -> str:
    label = request.args.get("label", "").strip()
    return label if label in NODE_TYPES else ""


def _query_arg() -> str:
    return request.args.get("q", "").strip()[:120]


@app.get("/api/search")
def api_search():
    page = _bounded_int(request.args.get("page"), 1, 1, 10000)
    page_size = _bounded_int(request.args.get("limit"), 18, 1, 60)
    return jsonify(_with_source("search", _query_arg(), _label_arg(), page, page_size))


@app.get("/api/graph")
def api_graph():
    limit = _bounded_int(request.args.get("limit"), 150, 20, 250)
    edge_limit = _bounded_int(request.args.get("edge_limit"), 700, 50, 1500)
    return jsonify(_with_source("graph", _query_arg(), _label_arg(), limit, edge_limit))


@app.get("/api/nodes/<path:node_id>")
def api_node(node_id: str):
    result = _with_source("node", node_id[:300])
    if result is None:
        return jsonify({"error": "Không tìm thấy thực thể."}), 404
    return jsonify(result)


@app.errorhandler(404)
def not_found(_error):
    if request.path.startswith("/api/"):
        return jsonify({"error": "Không tìm thấy tài nguyên."}), 404
    return app.send_static_file("index.html")


@app.errorhandler(500)
def internal_error(error):
    app.logger.exception("Unhandled request error: %s", error)
    return jsonify({"error": "Có lỗi khi xử lý dữ liệu. Vui lòng thử lại."}), 500


if __name__ == "__main__":
    host = os.getenv("APP_HOST", "0.0.0.0")
    port = int(os.getenv("APP_PORT", "5000"))
    debug = os.getenv("FLASK_DEBUG", "0") == "1"
    try:
        lan_ip = socket.gethostbyname(socket.gethostname())
    except OSError:
        lan_ip = "<IP-LAN-máy-tính>"
    print(f"\n  KG Diabet đang chạy: http://127.0.0.1:{port}")
    print(f"  Điện thoại cùng Wi-Fi: http://{lan_ip}:{port}\n")
    if debug:
        app.run(host=host, port=port, debug=True)
    else:
        try:
            from waitress import serve

            serve(app, host=host, port=port, threads=8)
        except ImportError:
            app.run(host=host, port=port, debug=False)
