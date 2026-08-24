# -*- coding: utf-8 -*-
"""
Graph Engine for SentinelAI Fraud Detection System
Implements graph-based fraud detection features and combines them into a Graph Score.
"""

from typing import Dict, Any, Union, List, Optional
import numpy as np
import pandas as pd
import networkx as nx
from sklearn.preprocessing import MinMaxScaler


class GraphEngine:
    """
    Graph Engine that implements various graph-based fraud detection features.
    Each feature returns a score between 0-100 indicating the likelihood of fraud.
    Final Graph Score is a weighted combination of individual graph features.
    """

    def __init__(self,
                 proximity_weight: float = 0.30,
                 centrality_weight: float = 0.25,
                 community_weight: float = 0.25,
                 bridge_weight: float = 0.20):
        """
        Initialize Graph Engine with weights for different feature categories.

        Args:
            proximity_weight: Weight for proximity to known fraudsters features
            centrality_weight: Weight for centrality measures features
            community_weight: Weight for community/clustering features
            bridge_weight: Weight for bridge/bottleneck features
        """
        self.proximity_weight = proximity_weight
        self.centrality_weight = centrality_weight
        self.community_weight = community_weight
        self.bridge_weight = bridge_weight

        # Normalize weights to sum to 1.0
        total_weight = proximity_weight + centrality_weight + community_weight + bridge_weight
        if not np.isclose(total_weight, 1.0):
            self.proximity_weight /= total_weight
            self.centrality_weight /= total_weight
            self.community_weight /= total_weight
            self.bridge_weight /= total_weight

        # Initialize scaler for normalizing features
        self.scaler = MinMaxScaler()

    def build_graph(self, edges: pd.DataFrame) -> nx.Graph:
        """
        Build a NetworkX graph from edges DataFrame.

        Args:
            edges: DataFrame with columns ['account_a', 'account_b', 'shared_type',
                   'connection_count', 'ring_id', 'both_fraud']

        Returns:
            NetworkX graph with nodes as accounts and edges representing connections
        """
        G = nx.Graph()

        # Add edges with attributes
        for _, row in edges.iterrows():
            G.add_edge(
                row['account_a'],
                row['account_b'],
                shared_type=row['shared_type'],
                connection_count=row['connection_count'],
                ring_id=row['ring_id'] if pd.notna(row['ring_id']) else None,
                both_fraud=row['both_fraud']
            )

        return G

    def _proximity_features(self, G: nx.Graph, tx_accounts: List[str]) -> Dict[str, np.ndarray]:
        """
        Compute proximity-based features: distance to known fraudsters.

        Args:
            G: NetworkX graph
            tx_accounts: List of account IDs in the transaction batch

        Returns:
            Dictionary of proximity features
        """
        # Find known fraudster accounts (those with both_fraud=1.0 in any edge)
        fraudster_nodes = set()
        for u, v, data in G.edges(data=True):
            if data.get('both_fraud', 0) == 1.0:
                fraudster_nodes.add(u)
                fraudster_nodes.add(v)

        if not fraudster_nodes:
            # If no known fraudsters, return zero scores
            return {
                'min_distance_to_fraudster': np.zeros(len(tx_accounts)),
                'avg_distance_to_fraudster': np.zeros(len(tx_accounts))
            }

        # Compute shortest path distances to nearest fraudster for each account
        min_distances = []
        avg_distances = []

        for account in tx_accounts:
            if account not in G:
                # Account not in graph
                min_distances.append(100)  # Large distance
                avg_distances.append(100)
                continue

            # Compute distances to all fraudsters
            distances = []
            for fraudster in fraudster_nodes:
                if fraudster in G:
                    try:
                        distance = nx.shortest_path_length(G, source=account, target=fraudster)
                        distances.append(distance)
                    except nx.NetworkXNoPath:
                        # No path exists
                        distances.append(100)  # Large distance

            if distances:
                min_distances.append(min(distances))
                avg_distances.append(np.mean(distances))
            else:
                min_distances.append(100)
                avg_distances.append(100)

        # Convert to numpy arrays and normalize (closer = higher score)
        min_distances = np.array(min_distances)
        avg_distances = np.array(avg_distances)

        # Convert distance to similarity score (0-100, where closer to fraudster = higher score)
        # Use inverse distance with cap to avoid infinite scores
        max_distance = 100
        min_distance_score = np.maximum(0, (max_distance - min_distances) / max_distance * 100)
        avg_distance_score = np.maximum(0, (max_distance - avg_distances) / max_distance * 100)

        return {
            'min_distance_to_fraudster': min_distance_score,
            'avg_distance_to_fraudster': avg_distance_score
        }

    def _centrality_features(self, G: nx.Graph, tx_accounts: List[str]) -> Dict[str, np.ndarray]:
        """
        Compute centrality-based features.

        Args:
            G: NetworkX graph
            tx_accounts: List of account IDs in the transaction batch

        Returns:
            Dictionary of centrality features
        """
        if len(G.nodes()) == 0:
            return {
                'degree_centrality': np.zeros(len(tx_accounts)),
                'betweenness_centrality': np.zeros(len(tx_accounts)),
                'closeness_centrality': np.zeros(len(tx_accounts))
            }

        # Compute centrality measures (only for the largest connected component to avoid issues)
        try:
            # Get the largest connected component
            largest_cc = max(nx.connected_components(G), key=len)
            G_lcc = G.subgraph(largest_cc).copy()

            # Compute centralities
            degree_centrality = nx.degree_centrality(G_lcc)
            betweenness_centrality = nx.betweenness_centrality(G_lcc, normalized=True, k=min(100, len(G_lcc)))
            closeness_centrality = nx.closeness_centrality(G_lcc)
        except:
            # Fallback if centrality computation fails
            degree_centrality = {node: 0 for node in G.nodes()}
            betweenness_centrality = {node: 0 for node in G.nodes()}
            closeness_centrality = {node: 0 for node in G.nodes()}

        # Extract features for transaction accounts
        degree_scores = []
        betweenness_scores = []
        closeness_scores = []

        for account in tx_accounts:
            if account in degree_centrality:
                degree_scores.append(degree_centrality[account] * 100)  # Convert to 0-100 scale
                betweenness_scores.append(betweenness_centrality[account] * 100)
                closeness_scores.append(closeness_centrality[account] * 100)
            else:
                degree_scores.append(0.0)
                betweenness_scores.append(0.0)
                closeness_scores.append(0.0)

        return {
            'degree_centrality': np.array(degree_scores),
            'betweenness_centrality': np.array(betweenness_scores),
            'closeness_centrality': np.array(closeness_scores)
        }

    def _community_features(self, G: nx.Graph, tx_accounts: List[str]) -> Dict[str, np.ndarray]:
        """
        Compute community/clustering-based features.

        Args:
            G: NetworkX graph
            tx_accounts: List of account IDs in the transaction batch

        Returns:
            Dictionary of community features
        """
        if len(G.nodes()) == 0:
            return {
                'clustering_coefficient': np.zeros(len(tx_accounts)),
                'community_fraud_ratio': np.zeros(len(tx_accounts))
            }

        # Compute clustering coefficient for each node
        try:
            clustering_coeff = nx.clustering(G)
        except:
            clustering_coeff = {node: 0.0 for node in G.nodes()}

        # Compute fraud ratio in each connected component (community)
        # First, label each node with its component ID
        try:
            components = list(nx.connected_components(G))
            node_to_component = {}
            component_fraud_ratios = []

            for i, component in enumerate(components):
                # Count known fraudsters in this component
                fraud_count = 0
                total_count = len(component)
                for node in component:
                    # Check if node is connected to any known fraudster via edges with both_fraud=1
                    is_fraudster = False
                    for neighbor in G.neighbors(node):
                        edge_data = G.get_edge_data(node, neighbor)
                        if edge_data and edge_data.get('both_fraud', 0) == 1.0:
                            is_fraudster = True
                            break
                    if is_fraudster:
                        fraud_count += 1

                fraud_ratio = fraud_count / total_count if total_count > 0 else 0.0
                component_fraud_ratios.append(fraud_ratio)

                # Assign component ID and fraud ratio to each node
                for node in component:
                    node_to_component[node] = (i, fraud_ratio)
        except:
            # Fallback if community detection fails
            node_to_component = {node: (0, 0.0) for node in G.nodes()}

        # Extract features for transaction accounts
        clustering_scores = []
        community_fraud_scores = []

        for account in tx_accounts:
            if account in clustering_coeff:
                clustering_scores.append(clustering_coeff[account] * 100)  # Convert to 0-100 scale
            else:
                clustering_scores.append(0.0)

            if account in node_to_component:
                _, fraud_ratio = node_to_component[account]
                community_fraud_scores.append(fraud_ratio * 100)  # Convert to 0-100 scale
            else:
                community_fraud_scores.append(0.0)

        return {
            'clustering_coefficient': np.array(clustering_scores),
            'community_fraud_ratio': np.array(community_fraud_scores)
        }

    def _bridge_features(self, G: nx.Graph, tx_accounts: List[str]) -> Dict[str, np.ndarray]:
        """
        Compute bridge/bottleneck-based features.

        Args:
            G: NetworkX graph
            tx_accounts: List of account IDs in the transaction batch

        Returns:
            Dictionary of bridge features
        """
        if len(G.nodes()) == 0:
            return {
                'edge_betweenness': np.zeros(len(tx_accounts)),
                'local_bridge_score': np.zeros(len(tx_accounts))
            }

        # Compute edge betweenness to identify bridge edges
        try:
            # Limit computation for large graphs
            if len(G.edges()) > 10000:
                # Sample edges for efficiency
                edges_sample = list(G.edges())[:1000]
                edge_betweenness = nx.edge_betweenness_centrality(G, edges=edges_sample, normalized=True)
            else:
                edge_betweenness = nx.edge_betweenness_centrality(G, normalized=True)
        except:
            edge_betweenness = {edge: 0.0 for edge in G.edges()}

        # Compute node-based bridge score: sum of edge betweenness of incident edges
        node_bridge_score = {}
        for node in G.nodes():
            score = 0.0
            for neighbor in G.neighbors(node):
                edge = tuple(sorted([node, neighbor]))  # Ensure consistent ordering
                # Handle both (u,v) and (v,u) edge representations
                if edge in edge_betweenness:
                    score += edge_betweenness[edge]
                else:
                    # Try reversed order
                    edge_rev = tuple(sorted([neighbor, node]))
                    if edge_rev in edge_betweenness:
                        score += edge_betweenness[edge_rev]
            node_bridge_score[node] = score

        # Normalize bridge scores to 0-100 scale
        if node_bridge_score:
            max_bridge = max(node_bridge_score.values()) if node_bridge_score.values() else 1.0
            if max_bridge > 0:
                node_bridge_score = {node: (score / max_bridge) * 100 for node, score in node_bridge_score.items()}
            else:
                node_bridge_score = {node: 0.0 for node in node_bridge_score}
        else:
            node_bridge_score = {}

        # Extract features for transaction accounts
        edge_betweenness_scores = []
        local_bridge_scores = []

        for account in tx_accounts:
            # For edge_betweenness feature, we use the max edge betweenness of incident edges
            max_edge_bet = 0.0
            local_bridge = node_bridge_score.get(account, 0.0)

            for neighbor in G.neighbors(account):
                edge = tuple(sorted([account, neighbor]))
                if edge in edge_betweenness:
                    max_edge_bet = max(max_edge_bet, edge_betweenness[edge])
                else:
                    edge_rev = tuple(sorted([neighbor, account]))
                    if edge_rev in edge_betweenness:
                        max_edge_bet = max(max_edge_bet, edge_betweenness[edge_rev])

            edge_betweenness_scores.append(max_edge_bet * 100)  # Convert to 0-100 scale
            local_bridge_scores.append(local_bridge)

        return {
            'edge_betweenness': np.array(edge_betweenness_scores),
            'local_bridge_score': np.array(local_bridge_scores)
        }

    def compute_graph_score(self,
                          tx: pd.DataFrame,
                          edges: pd.DataFrame = None,
                          accounts: pd.DataFrame = None) -> Union[float, np.ndarray]:
        """
        Compute Graph Score by combining various graph-based features.

        Args:
            tx: Transaction DataFrame with features (must contain 'account_id')
            edges: Network edges DataFrame (optional, if not provided will try to build from tx)
            accounts: Account profiles DataFrame (optional)

        Returns:
            Graph Score(s) in range [0, 100]
        """
        # Build graph from edges data
        if edges is None:
            # If no edges provided, return zero scores (can't compute graph features)
            return np.zeros(len(tx)) if len(tx) > 1 else 0.0

        G = self.build_graph(edges)

        # Get list of account IDs from transactions
        tx_accounts = tx['account_id'].tolist() if 'account_id' in tx.columns else []

        if not tx_accounts:
            return np.zeros(len(tx)) if len(tx) > 1 else 0.0

        # Compute all feature categories
        proximity_features = self._proximity_features(G, tx_accounts)
        centrality_features = self._centrality_features(G, tx_accounts)
        community_features = self._community_features(G, tx_accounts)
        bridge_features = self._bridge_features(G, tx_accounts)

        # Combine features within each category (average)
        proximity_score = np.mean([
            proximity_features['min_distance_to_fraudster'],
            proximity_features['avg_distance_to_fraudster']
        ], axis=0)

        centrality_score = np.mean([
            centrality_features['degree_centrality'],
            centrality_features['betweenness_centrality'],
            centrality_features['closeness_centrality']
        ], axis=0)

        community_score = np.mean([
            community_features['clustering_coefficient'],
            community_features['community_fraud_ratio']
        ], axis=0)

        bridge_score = np.mean([
            bridge_features['edge_betweenness'],
            bridge_features['local_bridge_score']
        ], axis=0)

        # Combine category scores with weights
        graph_score = (
            self.proximity_weight * proximity_score +
            self.centrality_weight * centrality_score +
            self.community_weight * community_score +
            self.bridge_weight * bridge_score
        )

        return np.clip(graph_score, 0.0, 100.0)

    def get_graph_details(self,
                         tx: pd.DataFrame,
                         edges: pd.DataFrame = None,
                         accounts: pd.DataFrame = None) -> Dict[str, Any]:
        """
        Get detailed breakdown of graph scores for analysis.

        Returns:
            Dictionary with individual graph feature scores and final score
        """
        # Build graph from edges data
        if edges is None:
            # Return zero details if no edges
            return {
                'proximity_score': 0.0,
                'centrality_score': 0.0,
                'community_score': 0.0,
                'bridge_score': 0.0,
                'final_graph_score': 0.0
            }

        G = self.build_graph(edges)

        # Get list of account IDs from transactions
        tx_accounts = tx['account_id'].tolist() if 'account_id' in tx.columns else []

        if not tx_accounts:
            return {
                'proximity_score': 0.0,
                'centrality_score': 0.0,
                'community_score': 0.0,
                'bridge_score': 0.0,
                'final_graph_score': 0.0
            }

        # Compute all feature categories
        proximity_features = self._proximity_features(G, tx_accounts)
        centrality_features = self._centrality_features(G, tx_accounts)
        community_features = self._community_features(G, tx_accounts)
        bridge_features = self._bridge_features(G, tx_accounts)

        # Combine features within each category (average)
        proximity_score = np.mean([
            proximity_features['min_distance_to_fraudster'],
            proximity_features['avg_distance_to_fraudster']
        ])

        centrality_score = np.mean([
            centrality_features['degree_centrality'],
            centrality_features['betweenness_centrality'],
            centrality_features['closeness_centrality']
        ])

        community_score = np.mean([
            community_features['clustering_coefficient'],
            community_features['community_fraud_ratio']
        ])

        bridge_score = np.mean([
            bridge_features['edge_betweenness'],
            bridge_features['local_bridge_score']
        ])

        # Combine category scores with weights
        final_graph_score = (
            self.proximity_weight * proximity_score +
            self.centrality_weight * centrality_score +
            self.community_weight * community_score +
            self.bridge_weight * bridge_score
        )

        return {
            'proximity_score': float(np.mean(proximity_score)) if hasattr(proximity_score, '__len__') else float(proximity_score),
            'centrality_score': float(np.mean(centrality_score)) if hasattr(centrality_score, '__len__') else float(centrality_score),
            'community_score': float(np.mean(community_score)) if hasattr(community_score, '__len__') else float(community_score),
            'bridge_score': float(np.mean(bridge_score)) if hasattr(bridge_score, '__len__') else float(bridge_score),
            'final_graph_score': float(np.mean(final_graph_score)) if hasattr(final_graph_score, '__len__') else float(final_graph_score)
        }


# Convenience function for easy usage
def compute_graph_score(tx: pd.DataFrame,
                       edges: pd.DataFrame = None,
                       accounts: pd.DataFrame = None,
                       **kwargs) -> Union[float, np.ndarray]:
    """
    Convenience function to compute Graph Score.

    Args:
        tx: Transaction DataFrame
        edges: Network edges DataFrame (optional)
        accounts: Account profiles DataFrame (optional)
        **kwargs: Additional arguments passed to GraphEngine constructor

    Returns:
        Graph Score(s) in range [0, 100]
    """
    engine = GraphEngine(**kwargs)
    return engine.compute_graph_score(tx, edges, accounts)