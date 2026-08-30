"""Convert graph-tool output into explicit, non-scoring investigation evidence."""

from __future__ import annotations

from typing import Any


class GraphEvidenceExtractor:
    """Extract compact graph evidence without creating a graph score."""

    def extract(self, graph_analysis: dict[str, Any]) -> dict[str, Any]:
        """Return structural and label-derived evidence with clear provenance."""
        if not graph_analysis or graph_analysis.get("error"):
            return {
                "available": False,
                "reason": graph_analysis.get("error", "Graph evidence was not available."),
                "used_for_risk_score": False,
            }

        ring = graph_analysis.get("fraud_ring", {})
        centrality = graph_analysis.get("centrality", {})
        community = graph_analysis.get("community", {})
        neighbors = graph_analysis.get("neighbors", {})
        ring_details = ring.get("ring_details", {})
        ring_summaries = [
            {
                "ring_id": str(ring_id),
                "account_count": details.get("account_count", 0),
                "known_fraudster_count": details.get("known_fraudster_count", 0),
                "fraudster_ratio": details.get("fraudster_ratio", 0.0),
            }
            for ring_id, details in ring_details.items()
        ]

        return {
            "available": True,
            "used_for_risk_score": False,
            "structural_evidence": {
                "total_neighbors_within_two_hops": neighbors.get("total_neighbors", 0),
                "degree_centrality": centrality.get("degree_centrality", 0.0),
                "betweenness_centrality": centrality.get("betweenness_centrality", 0.0),
                "component_size": community.get("component_size", 0),
                "component_density": community.get("component_density", 0.0),
            },
            "historical_label_evidence": {
                "in_known_fraud_ring": bool(ring.get("in_fraud_ring", False)),
                "rings": ring_summaries,
                "note": "Derived from historical labels; investigation/human-review evidence only.",
            },
            "limitations": [
                "Graph evidence does not create or adjust Risk Score, tier, or policy.",
                "Historical label-derived fields must not be used as online ML features.",
            ],
        }
