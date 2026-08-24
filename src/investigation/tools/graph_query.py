"""
Graph Query Tool for Investigation Agent
Provides methods to query the Neo4j-like graph structure for investigation purposes
"""
import pandas as pd
import numpy as np
import networkx as nx
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path

class GraphQueryTool:
    """
    Tool for querying graph-based relationships to support fraud investigations.
    Works with the processed network edges data to provide contextual information
    about entities involved in suspicious transactions.
    """

    def __init__(self, data_dir: str = "data/processed/fraud_1m_processed"):
        """
        Initialize the Graph Query Tool.

        Args:
            data_dir: Directory containing processed graph data
        """
        self.data_dir = Path(data_dir)
        self.edges_df = None
        self.accounts_df = None
        self.graph = None
        self._load_data()

    def _load_data(self):
        """Load graph data from processed parquet files"""
        try:
            self.edges_df = pd.read_parquet(self.data_dir / "network_edges_clean.parquet")
            self.accounts_df = pd.read_parquet(self.data_dir / "account_profiles_clean.parquet")
            self._build_graph()
            print(f"Loaded graph data: {len(self.edges_df)} edges, {len(self.accounts_df)} accounts")
        except Exception as e:
            print(f"Warning: Could not load graph data: {e}")
            # Create empty dataframes to prevent crashes
            self.edges_df = pd.DataFrame(columns=['account_a', 'account_b', 'shared_type',
                                                 'connection_count', 'ring_id', 'both_fraud'])
            self.accounts_df = pd.DataFrame(columns=['account_id'])
            self.graph = nx.Graph()

    def _build_graph(self):
        """Build NetworkX graph from edges data"""
        self.graph = nx.Graph()

        # Add edges with attributes
        for _, row in self.edges_df.iterrows():
            self.graph.add_edge(
                row['account_a'],
                row['account_b'],
                shared_type=row['shared_type'] if 'shared_type' in row else None,
                connection_count=row['connection_count'] if 'connection_count' in row else 1,
                ring_id=row['ring_id'] if 'ring_id' in row and pd.notna(row['ring_id']) else None,
                both_fraud=row['both_fraud'] if 'both_fraud' in row else 0.0
            )

    def get_entity_neighbors(self, entity_id: str, max_depth: int = 2) -> Dict[str, Any]:
        """
        Get neighbors of an entity up to a specified depth.

        Args:
            entity_id: ID of the entity to query
            max_depth: Maximum depth to traverse (1 = direct connections, 2 = friends of friends)

        Returns:
            Dictionary containing neighbor information at each depth level
        """
        if entity_id not in self.graph:
            return {"error": f"Entity {entity_id} not found in graph"}

        neighbors = {0: [entity_id]}  # Depth 0 is the entity itself
        visited = {entity_id}
        current_level = {entity_id}

        for depth in range(1, max_depth + 1):
            next_level = set()
            for node in current_level:
                for neighbor in self.graph.neighbors(node):
                    if neighbor not in visited:
                        visited.add(neighbor)
                        next_level.add(neighbor)

            neighbors[depth] = list(next_level)
            current_level = next_level

            if not next_level:  # No more nodes to explore
                break

        # Get edge details for connections
        edge_details = {}
        for depth in range(1, max_depth + 1):
            if depth in neighbors and neighbors[depth]:
                depth_edges = []
                for node in neighbors[depth]:
                    # Find edges connecting this node to nodes at previous depth
                    for prev_node in neighbors.get(depth-1, []):
                        if self.graph.has_edge(node, prev_node):
                            edge_data = self.graph.get_edge_data(node, prev_node)
                            depth_edges.append({
                                'from': prev_node,
                                'to': node,
                                'shared_type': edge_data.get('shared_type'),
                                'connection_count': edge_data.get('connection_count', 1),
                                'ring_id': edge_data.get('ring_id'),
                                'both_fraud': edge_data.get('both_fraud', 0.0)
                            })
                if depth_edges:
                    edge_details[f"depth_{depth}"] = depth_edges

        return {
            "entity_id": entity_id,
            "max_depth": max_depth,
            "neighbors_by_depth": neighbors,
            "total_neighbors": sum(len(nodes) for depth, nodes in neighbors.items() if depth > 0),
            "edge_details": edge_details
        }

    def get_fraud_ring_info(self, entity_id: str) -> Dict[str, Any]:
        """
        Get information about fraud ring membership for an entity.

        Args:
            entity_id: ID of the entity to check

        Returns:
            Dictionary containing fraud ring information
        """
        if entity_id not in self.graph:
            return {"error": f"Entity {entity_id} not found in graph"}

        # Find edges with ring_id not null
        ring_edges = self.edges_df[self.edges_df['ring_id'].notna()] if 'ring_id' in self.edges_df.columns else pd.DataFrame()

        if ring_edges.empty:
            return {
                "entity_id": entity_id,
                "in_fraud_ring": False,
                "fraud_rings": [],
                "ring_details": {}
            }

        # Find which rings this entity belongs to
        entity_rings = set()
        for _, row in ring_edges.iterrows():
            if row['account_a'] == entity_id or row['account_b'] == entity_id:
                entity_rings.add(row['ring_id'])

        # Get details for each ring
        ring_details = {}
        for ring_id in entity_rings:
            ring_edges_subset = ring_edges[ring_edges['ring_id'] == ring_id]
            ring_accounts = set()
            for _, row in ring_edges_subset.iterrows():
                ring_accounts.add(row['account_a'])
                ring_accounts.add(row['account_b'])

            # Count known fraudsters in the ring
            fraudster_count = 0
            for account in ring_accounts:
                # Check if account is marked as fraudster in accounts data
                if not self.accounts_df.empty and 'is_fraudster' in self.accounts_df.columns:
                    account_info = self.accounts_df[self.accounts_df['account_id'] == account]
                    if not account_info.empty and account_info.iloc[0].get('is_fraudster', 0) == 1:
                        fraudster_count += 1

            ring_details[ring_id] = {
                "account_count": len(ring_accounts),
                "known_fraudster_count": fraudster_count,
                "fraudster_ratio": fraudster_count / len(ring_accounts) if ring_accounts else 0,
                "edges": ring_edges_subset.to_dict('records')
            }

        return {
            "entity_id": entity_id,
            "in_fraud_ring": len(entity_rings) > 0,
            "fraud_rings": list(entity_rings),
            "ring_details": ring_details
        }

    def get_centrality_measures(self, entity_ids: List[str]) -> Dict[str, Dict[str, float]]:
        """
        Calculate centrality measures for specified entities.

        Args:
            entity_ids: List of entity IDs to analyze

        Returns:
            Dictionary mapping entity ID to its centrality measures
        """
        if not self.graph.nodes():
            return {entity_id: {"error": "Graph is empty"} for entity_id in entity_ids}

        # Calculate centrality measures for the largest connected component
        try:
            largest_cc = max(nx.connected_components(self.graph), key=len)
            subgraph = self.graph.subgraph(largest_cc).copy()

            # Calculate various centrality measures
            degree_centrality = nx.degree_centrality(subgraph)
            try:
                betweenness_centrality = nx.betweenness_centrality(subgraph, k=min(100, len(subgraph)))
            except:
                betweenness_centrality = {node: 0.0 for node in subgraph.nodes()}
            try:
                closeness_centrality = nx.closeness_centrality(subgraph)
            except:
                closeness_centrality = {node: 0.0 for node in subgraph.nodes()}

            # Prepare results for requested entities
            results = {}
            for entity_id in entity_ids:
                if entity_id in degree_centrality:
                    results[entity_id] = {
                        "degree_centrality": degree_centrality.get(entity_id, 0.0),
                        "betweenness_centrality": betweenness_centrality.get(entity_id, 0.0),
                        "closeness_centrality": closeness_centrality.get(entity_id, 0.0),
                        "in_largest_component": entity_id in largest_cc
                    }
                else:
                    results[entity_id] = {
                        "degree_centrality": 0.0,
                        "betweenness_centrality": 0.0,
                        "closeness_centrality": 0.0,
                        "in_largest_component": False
                    }

            return results

        except Exception as e:
            return {entity_id: {"error": f"Error calculating centrality: {str(e)}"} for entity_id in entity_ids}

    def get_community_info(self, entity_id: str) -> Dict[str, Any]:
        """
        Get community/clustering information for an entity.

        Args:
            entity_id: ID of the entity to analyze

        Returns:
            Dictionary containing community information
        """
        if entity_id not in self.graph:
            return {"error": f"Entity {entity_id} not found in graph"}

        try:
            # Get connected component
            component = None
            for comp in nx.connected_components(self.graph):
                if entity_id in comp:
                    component = comp
                    break

            if component is None:
                return {"error": f"Could not find component for entity {entity_id}"}

            # Calculate clustering coefficient for the entity
            try:
                clustering_coeff = nx.clustering(self.graph, entity_id)
            except:
                clustering_coeff = 0.0

            # Calculate fraud ratio in the component
            fraud_count = 0
            total_count = len(component)

            for node in component:
                # Check if node is connected to any known fraudster
                is_fraudster = False
                for neighbor in self.graph.neighbors(node):
                    edge_data = self.graph.get_edge_data(node, neighbor)
                    if edge_data and edge_data.get('both_fraud', 0) == 1.0:
                        is_fraudster = True
                        break
                if is_fraudster:
                    fraud_count += 1

            fraud_ratio = fraud_count / total_count if total_count > 0 else 0.0

            # Get component size and density
            subgraph = self.graph.subgraph(component)
            density = nx.density(subgraph) if len(subgraph) > 1 else 0.0

            return {
                "entity_id": entity_id,
                "component_size": len(component),
                "clustering_coefficient": clustering_coeff,
                "component_fraud_ratio": fraud_ratio,
                "known_fraudsters_in_component": fraud_count,
                "component_density": density,
                "is_large_component": len(component) > len(self.graph.nodes()) * 0.1  # >10% of graph
            }

        except Exception as e:
            return {"error": f"Error analyzing community: {str(e)}"}

    def investigate_entity(self, entity_id: str) -> Dict[str, Any]:
        """
        Perform a comprehensive investigation of an entity using all available graph methods.

        Args:
            entity_id: ID of the entity to investigate

        Returns:
            Dictionary containing all investigation results
        """
        if entity_id not in self.graph:
            return {"error": f"Entity {entity_id} not found in graph"}

        results = {
            "entity_id": entity_id,
            "neighbors": self.get_entity_neighbors(entity_id, max_depth=2),
            "fraud_ring": self.get_fraud_ring_info(entity_id),
            "centrality": self.get_centrality_measures([entity_id]).get(entity_id, {}),
            "community": self.get_community_info(entity_id)
        }

        return results