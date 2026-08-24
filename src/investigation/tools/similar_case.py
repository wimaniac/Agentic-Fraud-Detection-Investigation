"""
Similar Case Tool for Investigation Agent
Finds historically similar transactions/cases for reference
"""
import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path
from datetime import datetime, timedelta

class SimilarCaseTool:
    """
    Tool for finding historically similar transactions to support investigations.
    Uses feature similarity to identify past cases with known outcomes.
    """

    def __init__(self, data_dir: str = "data/processed/fraud_1m_processed"):
        """
        Initialize the Similar Case Tool.

        Args:
            data_dir: Directory containing processed transaction data
        """
        self.data_dir = Path(data_dir)
        self.transactions_df = None
        self.feature_columns = None
        self._load_data()
        self._prepare_features()

    def _load_data(self):
        """Load transaction data"""
        try:
            self.transactions_df = pd.read_parquet(self.data_dir / "transactions_clean.parquet")
            if 'timestamp' in self.transactions_df.columns:
                self.transactions_df['timestamp'] = pd.to_datetime(self.transactions_df['timestamp'])
            print(f"Loaded similar case data: {len(self.transactions_df)} transactions")
        except Exception as e:
            print(f"Warning: Could not load similar case data: {e}")
            self.transactions_df = pd.DataFrame()

    def _prepare_features(self):
        """Prepare feature columns for similarity comparison"""
        # Define feature columns that are useful for similarity matching
        potential_features = [
            'amount', 'velocity_1h', 'is_foreign_txn',
            'ip_risk_score', 'amount_vs_avg_ratio', 'time_since_last_s',
            'device_known', 'n_shared_types', 'in_ring', 'account_degree'
        ]

        # Filter to columns that actually exist in the data
        if not self.transactions_df.empty:
            self.feature_columns = [col for col in potential_features if col in self.transactions_df.columns]
            print(f"Features used for similarity comparison: {self.feature_columns}")
        else:
            self.feature_columns = []

    def _calculate_similarity(self, tx1: pd.Series, tx2: pd.Series) -> float:
        """
        Calculate similarity between two transactions based on features.

        Args:
            tx1: First transaction
            tx2: Second transaction

        Returns:
            Similarity score between 0 and 1
        """
        if not self.feature_columns:
            return 0.0

        similarities = []
        valid_comparisons = 0

        for col in self.feature_columns:
            val1 = tx1[col] if col in tx1 else None
            val2 = tx2[col] if col in tx2 else None

            # Skip if either value is missing
            if pd.isna(val1) or pd.isna(val2):
                continue

            # Calculate similarity based on feature type
            if col in ['amount', 'velocity_1h', 'ip_risk_score', 'amount_vs_avg_ratio', 'time_since_last_s', 'account_degree']:
                # Numerical features: use normalized difference
                max_val = max(abs(val1), abs(val2), 1)  # Avoid division by zero
                if max_val == 0:
                    similarity = 1.0
                else:
                    similarity = 1.0 - (abs(val1 - val2) / max_val)
                similarities.append(max(0, similarity))  # Ensure non-negative
                valid_comparisons += 1

            elif col in ['is_foreign_txn', 'device_known', 'in_ring', 'n_shared_types']:
                # Binary/integer features: exact match or normalized difference
                if col == 'n_shared_types':
                    # Treat as numerical but cap at reasonable value
                    max_val = max(abs(val1), abs(val2), 5)  # Cap at 5 for sharing types
                    similarity = 1.0 - (abs(val1 - val2) / max_val)
                else:
                    # Binary features
                    similarity = 1.0 if val1 == val2 else 0.0
                similarities.append(similarity)
                valid_comparisons += 1

        # Return average similarity if we had valid comparisons
        if valid_comparisons > 0:
            return np.mean(similarities)
        else:
            return 0.0

    def find_similar_cases(self,
                          transaction: pd.Series,
                          days_back: int = 180,
                          similarity_threshold: float = 0.7,
                          max_results: int = 10,
                          include_fraud_outcomes: bool = True) -> Dict[str, Any]:
        """
        Find historical transactions similar to the given transaction.

        Args:
            transaction: Transaction data to compare against
            days_back: Number of days to look back for comparison
            similarity_threshold: Minimum similarity score (0-1) to consider a match
            max_results: Maximum number of similar cases to return
            include_fraud_outcomes: Whether to include fraud outcomes in results

        Returns:
            Dictionary containing similar cases and their outcomes
        """
        if self.transactions_df.empty:
            return {"error": "Transaction data not available"}

        if not self.feature_columns:
            return {"error": "No features available for similarity comparison"}

        # Prepare the transaction to compare
        if isinstance(transaction, pd.DataFrame) and len(transaction) == 1:
            tx_to_compare = transaction.iloc[0]
        elif isinstance(transaction, pd.Series):
            tx_to_compare = transaction
        else:
            return {"error": "Invalid transaction format"}

        # Filter by time if timestamp exists
        search_df = self.transactions_df.copy()
        if 'timestamp' in search_df.columns:
            as_of = pd.Timestamp(tx_to_compare.get('timestamp', search_df['timestamp'].max()))
            cutoff_date = as_of - timedelta(days=days_back)
            search_df = search_df[(search_df['timestamp'] >= cutoff_date) & (search_df['timestamp'] <= as_of)]

        # Exclude the transaction itself if it's in the dataset
        if 'transaction_id' in tx_to_compare and 'transaction_id' in search_df.columns:
            tx_id = tx_to_compare['transaction_id']
            search_df = search_df[search_df['transaction_id'] != tx_id]

        if search_df.empty:
            return {
                "transaction_id": tx_to_compare.get('transaction_id', 'unknown'),
                "search_period_days": days_back,
                "similar_cases": [],
                "message": "No transactions found in the specified time period for comparison"
            }

        # Calculate similarity scores
        similar_cases = []

        for _, row in search_df.iterrows():
            try:
                similarity = self._calculate_similarity(tx_to_compare, row)
                if similarity >= similarity_threshold:
                    case_data = {
                        'transaction_id': row['transaction_id'],
                        'similarity_score': similarity,
                        'transaction_data': row.to_dict()
                    }

                    # Include fraud outcome if requested and available
                    if include_fraud_outcomes and 'is_fraud' in row:
                        case_data['known_outcome'] = {
                            'is_fraud': bool(row['is_fraud']),
                            'fraud_label': 'FRAUD' if row['is_fraud'] else 'LEGITIMATE'
                        }

                    similar_cases.append(case_data)
            except Exception:
                # Skip transactions that cause errors in similarity calculation
                continue

        # Sort by similarity score (descending) and limit results
        similar_cases.sort(key=lambda x: x['similarity_score'], reverse=True)
        top_cases = similar_cases[:max_results]

        # Convert timestamps to strings for JSON serialization
        for case in top_cases:
            if 'transaction_data' in case and 'timestamp' in case['transaction_data']:
                ts = case['transaction_data']['timestamp']
                if pd.notna(ts):
                    if isinstance(ts, str):
                        pass
                    else:
                        case['transaction_data']['timestamp'] = ts.isoformat() if hasattr(ts, 'isoformat') else str(ts)

        # Calculate statistics
        fraud_cases = [case for case in top_cases if case.get('known_outcome', {}).get('is_fraud', False)]
        legitimate_cases = [case for case in top_cases if not case.get('known_outcome', {}).get('is_fraud', True)]

        stats = {
            "total_similar_cases": len(top_cases),
            "fraud_cases": len(fraud_cases),
            "legitimate_cases": len(legitimate_cases),
            "fraud_rate_among_similar": len(fraud_cases) / len(top_cases) if len(top_cases) > 0 else 0,
            "avg_similarity_score": np.mean([case['similarity_score'] for case in top_cases]) if len(top_cases) > 0 else 0
        }

        return {
            "transaction_id": tx_to_compare.get('transaction_id', 'unknown'),
            "search_period_days": days_back,
            "similarity_threshold": similarity_threshold,
            "similar_cases": top_cases,
            "statistics": stats,
            "fraud_evidence_assessment": {
                "severity_level": "HIGH" if stats["fraud_rate_among_similar"] > 0.7 else
                             "MEDIUM" if stats["fraud_rate_among_similar"] > 0.3 else
                             "LOW" if stats["fraud_rate_among_similar"] > 0.1 else
                             "VERY LOW",
                "description": f"Fraud rate among similar cases: {stats['fraud_rate_among_similar']*100:.1f}%"
            },
            "analysis_timestamp": datetime.now().isoformat()
        }

    def get_case_outcomes(self,
                         transaction_ids: List[str]) -> Dict[str, Any]:
        """
        Get known outcomes for a list of transaction IDs.

        Args:
            transaction_ids: List of transaction IDs to query

        Returns:
            Dictionary mapping transaction IDs to their known outcomes
        """
        if self.transactions_df.empty or 'transaction_id' not in self.transactions_df.columns:
            return {"error": "Transaction data not available"}

        outcomes = {}
        for tx_id in transaction_ids:
            tx_info = self.transactions_df[self.transactions_df['transaction_id'] == tx_id]
            if not tx_info.empty:
                tx_data = tx_info.iloc[0]
                outcomes[tx_id] = {
                    'transaction_id': tx_id,
                    'is_fraud': bool(tx_data.get('is_fraud', False)) if 'is_fraud' in tx_data else None,
                    'amount': tx_data.get('amount', 0) if 'amount' in tx_data else None,
                    'timestamp': tx_data['timestamp'].isoformat() if 'timestamp' in tx_data and pd.notna(tx_data['timestamp']) else None,
                    'risk_factors': {}
                }

                # Add common risk factors if available
                risk_fields = ['velocity_1h', 'amount_vs_avg_ratio', 'ip_risk_score', 'is_foreign_txn']
                for field in risk_fields:
                    if field in tx_data:
                        outcomes[tx_id]['risk_factors'][field] = tx_data[field]
            else:
                outcomes[tx_id] = {
                    'transaction_id': tx_id,
                    'error': 'Transaction not found'
                }

        return {
            "queried_transactions": len(transaction_ids),
            "found_outcomes": len([v for v in outcomes.values() if 'error' not in v]),
            "outcomes": outcomes
        }

    def investigate_similar_cases(self,
                                 transaction: pd.Series,
                                 include_temporal_context: bool = True) -> Dict[str, Any]:
        """
        Perform a comprehensive investigation using similar historical cases.

        Args:
            transaction: Transaction data to investigate
            include_temporal_context: Whether to include temporal context analysis

        Returns:
            Dictionary containing similar case investigation results
        """
        # Find similar cases
        similar_cases_result = self.find_similar_cases(
            transaction,
            days_back=180,
            similarity_threshold=0.6,
            max_results=15,
            include_fraud_outcomes=True
        )

        investigation_result = {
            "transaction_id": transaction.get('transaction_id', 'unknown') if isinstance(transaction, pd.Series) else transaction.iloc[0].get('transaction_id', 'unknown'),
            "similar_cases_analysis": similar_cases_result
        }

        # Add temporal context if requested
        if include_temporal_context and not self.transactions_df.empty:
            # Analyze when similar fraud cases tend to occur
            similar_cases = similar_cases_result.get('similar_cases', [])
            fraud_cases = [case for case in similar_cases if case.get('known_outcome', {}).get('is_fraud', False)]

            if fraud_cases and 'timestamp' in self.transactions_df.columns:
                # Extract timestamps of fraud cases
                fraud_timestamps = []
                for case in fraud_cases:
                    tx_id = case['transaction_id']
                    tx_info = self.transactions_df[self.transactions_df['transaction_id'] == tx_id]
                    if not tx_info.empty and 'timestamp' in tx_info.iloc[0]:
                        ts = tx_info.iloc[0]['timestamp']
                        if pd.notna(ts):
                            fraud_timestamps.append(ts)

                if fraud_timestamps:
                    # Analyze temporal patterns
                    hours = [ts.hour for ts in fraud_timestamps]
                    days_of_week = [ts.weekday() for ts in fraud_timestamps]  # Monday=0, Sunday=6

                    temporal_analysis = {
                        "fraud_cases_with_timestamp": len(fraud_timestamps),
                        "most_common_fraud_hour": max(set(hours), key=hours.count) if hours else None,
                        "most_common_fraud_day": max(set(days_of_week), key=days_of_week.count) if days_of_week else None,
                        "fraud_hour_distribution": {str(h): hours.count(h) for h in set(hours)},
                        "fraud_day_distribution": {str(d): days_of_week.count(d) for d in set(days_of_week)}
                    }

                    investigation_result["temporal_context"] = temporal_analysis

        return investigation_result
