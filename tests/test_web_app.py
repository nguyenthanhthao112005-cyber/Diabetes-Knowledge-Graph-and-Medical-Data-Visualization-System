# -*- coding: utf-8 -*-
"""Smoke tests for the web API and JSON fallback."""

import time
import unittest

import app as web_app


class WebAppTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = web_app.app.test_client()
        # Tests must be deterministic and must not require a local Neo4j server.
        cls.previous_offline_until = web_app.neo4j_store.offline_until
        web_app.neo4j_store.offline_until = time.monotonic() + 3600

    @classmethod
    def tearDownClass(cls):
        web_app.neo4j_store.offline_until = cls.previous_offline_until

    def test_home_and_configuration(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"GlucoGraph", response.data)
        response.close()

        config_response = self.client.get("/api/config")
        self.assertEqual(config_response.status_code, 200)
        self.assertIn("Drug", config_response.get_json()["node_types"])

    def test_stats_uses_snapshot(self):
        data = self.client.get("/api/stats").get_json()
        self.assertEqual(data["meta"]["source"], "snapshot")
        self.assertGreater(data["totals"]["nodes"], 100)
        self.assertGreater(data["totals"]["relationships"], 1000)
        self.assertTrue(any(row["label"] == "Drug" for row in data["labels"]))

    def test_search_is_accent_insensitive(self):
        data = self.client.get("/api/search?label=Symptom&q=khat%20nuoc").get_json()
        self.assertGreater(data["total"], 0)
        self.assertTrue(all(item["label"] == "Symptom" for item in data["items"]))

    def test_graph_and_node_detail(self):
        graph = self.client.get("/api/graph?label=LabTest&limit=30&edge_limit=100").get_json()
        self.assertTrue(graph["nodes"])
        self.assertTrue(graph["edges"])
        self.assertTrue(any(node["label"] == "LabTest" for node in graph["nodes"]))

        node_id = graph["nodes"][0]["id"]
        detail = self.client.get(f"/api/nodes/{node_id}")
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.get_json()["node"]["id"], node_id)


if __name__ == "__main__":
    unittest.main()
