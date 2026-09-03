# -*- coding: utf-8 -*-
"""
BƯỚC 3 — Import entities + relations vào Neo4j database `kg-diabet`.

- Dùng MERGE cho mọi node/relationship => chạy lại nhiều lần vẫn không nhân bản.
- Ghi theo batch bằng UNWIND để nhanh hơn nhiều so với chạy từng câu lệnh.
- Tạo index sau khi import và in thống kê tổng quan.

Chạy:  python 03_import_neo4j.py          (giữ nguyên dữ liệu cũ, MERGE thêm)
       python 03_import_neo4j.py --reset  (xoá sạch database trước khi import)
"""

import json
import sys

from neo4j import GraphDatabase

import config

# entities.json key  ->  nhãn node + các thuộc tính được phép ghi
NODE_SPEC = [
    ("diseases",        "Disease",      ["description", "icd_code", "source_url"]),
    ("symptoms",        "Symptom",      ["description", "source_url"]),
    ("drugs",           "Drug",         ["generic_name", "dosage_form", "concentration",
                                         "manufacturer", "price", "specification",
                                         "prescription", "sku", "source_url"]),
    ("lab_tests",       "LabTest",      ["normal_range", "unit", "source_url"]),
    ("risk_factors",    "RiskFactor",   ["description", "source_url"]),
    ("complications",   "Complication", ["description", "source_url"]),
    ("side_effects",    "SideEffect",   ["severity"]),
    ("drug_categories", "DrugCategory", []),
]

INDEX_STATEMENTS = [
    "CREATE INDEX disease_name IF NOT EXISTS FOR (d:Disease) ON (d.name)",
    "CREATE INDEX symptom_name IF NOT EXISTS FOR (s:Symptom) ON (s.name)",
    "CREATE INDEX drug_name IF NOT EXISTS FOR (dr:Drug) ON (dr.name)",
    "CREATE INDEX labtest_name IF NOT EXISTS FOR (l:LabTest) ON (l.name)",
    "CREATE INDEX riskfactor_name IF NOT EXISTS FOR (r:RiskFactor) ON (r.name)",
    "CREATE INDEX complication_name IF NOT EXISTS FOR (c:Complication) ON (c.name)",
    "CREATE INDEX sideeffect_name IF NOT EXISTS FOR (se:SideEffect) ON (se.name)",
    "CREATE INDEX drugcategory_name IF NOT EXISTS FOR (dc:DrugCategory) ON (dc.name)",
]

# Quan hệ hợp lệ theo schema: relation -> (nhãn nguồn, nhãn đích)
ALLOWED_RELATIONS = {
    "HAS_SYMPTOM":          ("Disease", "Symptom"),
    "TREATED_BY":           ("Disease", "Drug"),
    "DIAGNOSED_BY":         ("Disease", "LabTest"),
    "INCREASES_RISK_OF":    ("RiskFactor", "Disease"),
    "HAS_SIDE_EFFECT":      ("Drug", "SideEffect"),
    "BELONGS_TO":           ("Drug", "DrugCategory"),
    "CONTRAINDICATED_WITH": ("Drug", "Drug"),
    "CAUSES":               ("Disease", "Complication"),
    "DETECTED_BY":          ("Complication", "LabTest"),
}


def load_json(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except FileNotFoundError:
        print("[loi] Khong tim thay %s - hay chay 02_nlp_extraction.py truoc." % path)
        sys.exit(1)


def chunked(items, size=500):
    for i in range(0, len(items), size):
        yield items[i:i + size]


def import_nodes(session, entities):
    total = 0
    for key, label, prop_names in NODE_SPEC:
        rows = []
        for node in entities.get(key, []):
            props = {p: node.get(p) for p in prop_names if node.get(p) not in (None, "")}
            rows.append({"name": node["name"], "props": props})
        if not rows:
            print("  %-14s 0" % label)
            continue
        query = (
            "UNWIND $rows AS row "
            "MERGE (n:%s {name: row.name}) "
            "SET n += row.props" % label
        )
        for batch in chunked(rows):
            session.run(query, rows=batch)
        total += len(rows)
        print("  %-14s %d node" % (label, len(rows)))
    return total


def import_relations(session, relations):
    grouped = {}
    skipped = 0
    for rel in relations:
        rtype = rel["relation"]
        spec = ALLOWED_RELATIONS.get(rtype)
        if not spec or (rel["from_type"], rel["to_type"]) != spec:
            skipped += 1
            continue
        props = dict(rel.get("properties") or {})
        if rel.get("source_url"):
            props["source_url"] = rel["source_url"]
        grouped.setdefault(rtype, []).append(
            {"from": rel["from_name"], "to": rel["to_name"], "props": props}
        )

    total = 0
    for rtype, rows in sorted(grouped.items()):
        from_label, to_label = ALLOWED_RELATIONS[rtype]
        query = (
            "UNWIND $rows AS row "
            "MATCH (a:%s {name: row.from}) "
            "MATCH (b:%s {name: row.to}) "
            "MERGE (a)-[r:%s]->(b) "
            "SET r += row.props" % (from_label, to_label, rtype)
        )
        for batch in chunked(rows):
            session.run(query, rows=batch)
        total += len(rows)
        print("  %-22s %d quan he" % (rtype, len(rows)))
    if skipped:
        print("  (bo qua %d quan he khong khop schema)" % skipped)
    return total


def create_indexes(session):
    for stmt in INDEX_STATEMENTS:
        session.run(stmt)
    print("  da tao/kiem tra %d index" % len(INDEX_STATEMENTS))


def print_stats(session):
    print("\nThong ke node:")
    rows = session.run(
        "MATCH (n) RETURN labels(n)[0] AS label, count(n) AS count "
        "ORDER BY count DESC"
    )
    total_nodes = 0
    for row in rows:
        print("  %-16s %d" % (row["label"], row["count"]))
        total_nodes += row["count"]

    print("\nThong ke quan he:")
    rows = session.run(
        "MATCH ()-[r]->() RETURN type(r) AS rel_type, count(r) AS count "
        "ORDER BY count DESC"
    )
    total_rels = 0
    for row in rows:
        print("  %-22s %d" % (row["rel_type"], row["count"]))
        total_rels += row["count"]

    print("\nTONG: %d node, %d quan he" % (total_nodes, total_rels))


def main():
    reset = "--reset" in sys.argv

    print("=" * 70)
    print("BUOC 3 - IMPORT VAO NEO4J (database: %s)" % config.NEO4J_DATABASE)
    print("=" * 70)

    entities = load_json(config.ENTITIES_JSON)
    relations = load_json(config.RELATIONS_JSON)

    driver = GraphDatabase.driver(
        config.NEO4J_URI, auth=(config.NEO4J_USER, config.NEO4J_PASSWORD)
    )
    try:
        driver.verify_connectivity()
    except Exception as exc:
        print("[loi] Khong ket noi duoc Neo4j: %s" % exc)
        print("      Kiem tra Neo4j Desktop da Start instance chua.")
        sys.exit(1)

    try:
        with driver.session(database=config.NEO4J_DATABASE) as session:
            if reset:
                print("\n--reset: xoa toan bo du lieu cu...")
                session.run("MATCH (n) DETACH DELETE n")

            print("\nImport nodes:")
            import_nodes(session, entities)

            print("\nImport relationships:")
            import_relations(session, relations)

            print("\nTao index:")
            create_indexes(session)

            print_stats(session)
    finally:
        driver.close()

    print("\nHoan tat Buoc 3.")


if __name__ == "__main__":
    main()
