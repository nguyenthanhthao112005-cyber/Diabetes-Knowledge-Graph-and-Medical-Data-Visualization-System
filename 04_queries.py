# -*- coding: utf-8 -*-
"""
BƯỚC 4 — Bộ Cypher query khai thác Knowledge Graph kg_diabet.

Chạy:
    python 04_queries.py           # chạy tất cả query
    python 04_queries.py 3 7       # chỉ chạy Q3 và Q7
"""

import sys

from neo4j import GraphDatabase

import config

QUERIES = [
    {
        "id": "Q1",
        "title": "Triệu chứng của từng thể đái tháo đường",
        "cypher": """
            MATCH (d:Disease)-[r:HAS_SYMPTOM]->(s:Symptom)
            RETURN d.name AS disease,
                   count(s) AS n_symptoms,
                   collect(DISTINCT s.name)[0..12] AS symptoms
            ORDER BY n_symptoms DESC
        """,
    },
    {
        "id": "Q2",
        # Ghi chú: toàn bộ thuốc trị ĐTĐ trên Long Châu là thuốc KÊ ĐƠN, và
        # trang web không công bố giá thuốc kê đơn -> drug.price thường rỗng.
        "title": "Thuốc điều trị đái tháo đường type 2 (giá chỉ có với thuốc không kê đơn)",
        "cypher": """
            MATCH (d:Disease)-[:TREATED_BY]->(drug:Drug)
            WHERE d.name CONTAINS "type 2"
            RETURN drug.name AS drug,
                   drug.dosage_form AS dosage_form,
                   drug.specification AS specification,
                   drug.manufacturer AS manufacturer,
                   drug.price AS price
            ORDER BY coalesce(price, 0) DESC, drug
            LIMIT 20
        """,
    },
    {
        "id": "Q3",
        "title": "Xét nghiệm dùng để chẩn đoán mỗi bệnh",
        "cypher": """
            MATCH (d:Disease)-[:DIAGNOSED_BY]->(t:LabTest)
            RETURN d.name AS disease, collect(DISTINCT t.name) AS lab_tests
            ORDER BY size(lab_tests) DESC
        """,
    },
    {
        "id": "Q4",
        "title": "Yếu tố nguy cơ làm tăng khả năng mắc bệnh",
        "cypher": """
            MATCH (r:RiskFactor)-[:INCREASES_RISK_OF]->(d:Disease)
            RETURN r.name AS risk_factor,
                   count(DISTINCT d) AS n_diseases,
                   collect(DISTINCT d.name) AS diseases
            ORDER BY n_diseases DESC, risk_factor
        """,
    },
    {
        "id": "Q5",
        "title": "Tác dụng phụ của các thuốc chứa Metformin",
        "cypher": """
            MATCH (drug:Drug)-[r:HAS_SIDE_EFFECT]->(se:SideEffect)
            WHERE toLower(drug.name) CONTAINS "metformin"
               OR toLower(coalesce(drug.generic_name, "")) CONTAINS "metformin"
            RETURN drug.name AS drug,
                   collect(DISTINCT se.name + " (" + r.frequency + ")") AS side_effects
            LIMIT 15
        """,
    },
    {
        "id": "Q6",
        "title": "Biến chứng của bệnh đái tháo đường",
        "cypher": """
            MATCH (d:Disease)-[:CAUSES]->(c:Complication)
            RETURN d.name AS disease,
                   count(DISTINCT c) AS n_complications,
                   collect(DISTINCT c.name) AS complications
            ORDER BY n_complications DESC
        """,
    },
    {
        "id": "Q7",
        "title": "Thuốc theo nhóm dược lý",
        "cypher": """
            MATCH (drug:Drug)-[:BELONGS_TO]->(cat:DrugCategory)
            RETURN cat.name AS category,
                   count(drug) AS n_drugs,
                   collect(drug.name)[0..8] AS drugs
            ORDER BY n_drugs DESC
            LIMIT 15
        """,
    },
    {
        "id": "Q8",
        "title": "Bệnh có triệu chứng 'Khát nước nhiều' được điều trị bằng thuốc nào?",
        "cypher": """
            MATCH (d:Disease)-[:HAS_SYMPTOM]->(:Symptom {name: "Khát nước nhiều"})
            MATCH (d)-[:TREATED_BY]->(drug:Drug)
            RETURN d.name AS disease,
                   collect(DISTINCT drug.name)[0..10] AS treatments
        """,
    },
    {
        "id": "Q9",
        "title": "Đường đi RiskFactor -> Disease -> Complication",
        "cypher": """
            MATCH (r:RiskFactor)-[:INCREASES_RISK_OF]->(d:Disease)-[:CAUSES]->(c:Complication)
            RETURN r.name AS risk_factor, d.name AS disease, c.name AS complication
            ORDER BY risk_factor, disease, complication
            LIMIT 25
        """,
    },
    {
        "id": "Q10",
        "title": "Thống kê tổng quan Knowledge Graph",
        "cypher": """
            MATCH (n)
            RETURN labels(n)[0] AS type, count(n) AS total
            ORDER BY total DESC
        """,
    },
    {
        "id": "Q11",
        "title": "Top tác dụng phụ nghiêm trọng và các thuốc liên quan",
        "cypher": """
            MATCH (drug:Drug)-[:HAS_SIDE_EFFECT]->(se:SideEffect)
            WHERE se.severity = "severe"
            RETURN se.name AS side_effect,
                   count(DISTINCT drug) AS n_drugs,
                   collect(DISTINCT drug.name)[0..5] AS drugs
            ORDER BY n_drugs DESC
        """,
    },
    {
        "id": "Q12",
        "title": "Cặp thuốc / hoạt chất có cảnh báo chống chỉ định",
        "cypher": """
            MATCH (a:Drug)-[:CONTRAINDICATED_WITH]->(b:Drug)
            RETURN a.name AS drug, collect(DISTINCT b.name) AS avoid_with
            ORDER BY size(avoid_with) DESC
            LIMIT 15
        """,
    },
    {
        "id": "Q13",
        "title": "Biến chứng được phát hiện bằng xét nghiệm nào",
        "cypher": """
            MATCH (c:Complication)-[:DETECTED_BY]->(t:LabTest)
            RETURN c.name AS complication, collect(DISTINCT t.name) AS detected_by
            ORDER BY complication
        """,
    },
    {
        "id": "Q14",
        "title": "Node trung tâm nhất của đồ thị (bậc cao nhất)",
        "cypher": """
            MATCH (n)
            WITH n, labels(n)[0] AS label, count { (n)--() } AS degree
            WHERE degree > 0
            RETURN label, n.name AS name, degree
            ORDER BY degree DESC
            LIMIT 15
        """,
    },
    {
        "id": "Q15",
        "title": "Triệu chứng dùng chung giữa các thể bệnh (chẩn đoán phân biệt)",
        "cypher": """
            MATCH (d1:Disease)-[:HAS_SYMPTOM]->(s:Symptom)<-[:HAS_SYMPTOM]-(d2:Disease)
            WHERE d1.name < d2.name
            RETURN d1.name AS disease_1, d2.name AS disease_2,
                   count(DISTINCT s) AS shared_symptoms,
                   collect(DISTINCT s.name)[0..8] AS symptoms
            ORDER BY shared_symptoms DESC
            LIMIT 10
        """,
    },
]


def fmt(value, width=60):
    if isinstance(value, list):
        text = ", ".join(str(v) for v in value)
    elif value is None:
        text = "-"
    elif isinstance(value, float):
        text = ("%.0f" % value) if value == int(value) else str(value)
    else:
        text = str(value)
    text = " ".join(text.split())
    return text if len(text) <= width else text[: width - 3] + "..."


def run_query(session, spec, limit_rows=15):
    print("\n" + "-" * 78)
    print("%s. %s" % (spec["id"], spec["title"]))
    print("-" * 78)
    records = list(session.run(spec["cypher"]))
    if not records:
        print("  (khong co ket qua)")
        return 0

    keys = records[0].keys()
    widths = {k: max(14, min(46, max(len(fmt(r[k])) for r in records[:limit_rows]))) for k in keys}
    header = "  " + "  ".join(k.ljust(widths[k])[: widths[k]] for k in keys)
    print(header)
    print("  " + "  ".join("-" * widths[k] for k in keys))
    for record in records[:limit_rows]:
        print("  " + "  ".join(fmt(record[k], widths[k]).ljust(widths[k]) for k in keys))
    if len(records) > limit_rows:
        print("  ... (%d dong nua)" % (len(records) - limit_rows))
    return len(records)


def main():
    wanted = set()
    for arg in sys.argv[1:]:
        if arg.isdigit():
            wanted.add("Q" + arg)
        elif arg.upper().startswith("Q"):
            wanted.add(arg.upper())

    print("=" * 78)
    print("BUOC 4 - CYPHER QUERIES tren database %s" % config.NEO4J_DATABASE)
    print("=" * 78)

    driver = GraphDatabase.driver(
        config.NEO4J_URI, auth=(config.NEO4J_USER, config.NEO4J_PASSWORD)
    )
    try:
        driver.verify_connectivity()
    except Exception as exc:
        print("[loi] Khong ket noi duoc Neo4j: %s" % exc)
        sys.exit(1)

    try:
        with driver.session(database=config.NEO4J_DATABASE) as session:
            ran = 0
            for spec in QUERIES:
                if wanted and spec["id"] not in wanted:
                    continue
                run_query(session, spec)
                ran += 1
        print("\n" + "=" * 78)
        print("Da chay %d query." % ran)
    finally:
        driver.close()


if __name__ == "__main__":
    main()
