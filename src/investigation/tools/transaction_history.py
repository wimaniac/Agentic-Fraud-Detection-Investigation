"""
Transaction History Tool for Investigation Agent
Provides analysis of transaction patterns and relationships
"""
import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime, timedelta

class TransactionHistoryTool:
    """
    Tool for analyzing transaction patterns and relationships to support fraud investigations.
    """

    def __init__(self, data_dir: str = "data/processed/fraud_1m_processed"):
        """
        Initialize the Transaction History Tool.

        Args:
            data_dir: Directory containing processed transaction data
        """
        self.data_dir = Path(data_dir)
        self.transactions_df = None
        self.accounts_df = None
        self.edges_df = None
        self._load_data()

    def _load_data(self):
        """Load transaction and related data"""
        try:
            self.transactions_df = pd.read_parquet(self.data_dir / "transactions_clean.parquet")
            self.accounts_df = pd.read_parquet(self.data_dir / "account_profiles_clean.parquet")
            self.edges_df = pd.read_parquet(self.data_dir / "network_edges_clean.parquet")

            # Ensure timestamp is datetime
            if 'timestamp' in self.transactions_df.columns:
                self.transactions_df['timestamp'] = pd.to_datetime(self.transactions_df['timestamp'])

            print(f"Loaded transaction data: {len(self.transactions_df)} transactions")
        except Exception as e:
            print(f"Warning: Could not load transaction data: {e}")
            # Create empty dataframes to prevent crashes
            self.transactions_df = pd.DataFrame()
            self.accounts_df = pd.DataFrame()
            self.edges_df = pd.DataFrame()

    def get_transaction_details(self, transaction_id: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific transaction.

        Args:
            transaction_id: ID of the transaction to query

        Returns:
            Dictionary containing transaction details
        """
        if self.transactions_df.empty or 'transaction_id' not in self.transactions_df.columns:
            return {"error": "Transaction data not available"}

        tx_info = self.transactions_df[self.transactions_df['transaction_id'] == transaction_id]
        if tx_info.empty:
            return {"error": f"Transaction {transaction_id} not found"}

        tx_data = tx_info.iloc[0].to_dict()
        # Convert datetime to string for JSON serialization
        if 'timestamp' in tx_data and pd.notna(tx_data['timestamp']):
            tx_data['timestamp'] = tx_data['timestamp'].isoformat()

        return {
            "transaction_id": transaction_id,
            "details": tx_data
        }

    def get_similar_transactions(self,
                               transaction: pd.Series,
                               days_back: int = 30,
                               similarity_threshold: float = 0.8,
                               max_results: int = 10,
                               reference_timestamp: Optional[Any] = None) -> Dict[str, Any]:
        """
        Find transactions similar to the given transaction based on features.

        Args:
            transaction: Transaction data to compare against
            days_back: Number of days to look back for comparison
            similarity_threshold: Minimum similarity score (0-1) to consider a match
            max_results: Maximum number of similar transactions to return

        Returns:
            Dictionary containing similar transactions and their details
        """
        if self.transactions_df.empty:
            return {"error": "Transaction data not available"}

        # Prepare feature columns for comparison
        feature_cols = [
            'amount', 'velocity_1h', 'is_foreign_txn',
            'ip_risk_score', 'amount_vs_avg_ratio', 'time_since_last_s'
        ]

        # Filter to columns that exist in both the transaction and dataframe
        available_cols = [col for col in feature_cols if col in self.transactions_df.columns]
        if not available_cols:
            return {"error": "No comparable features available"}

        # Filter by time if timestamp exists
        search_df = self.transactions_df.copy()
        if 'timestamp' in search_df.columns:
            as_of = pd.Timestamp(reference_timestamp) if reference_timestamp is not None else pd.Timestamp(transaction.get('timestamp', search_df['timestamp'].max()))
            cutoff_date = as_of - timedelta(days=days_back)
            search_df = search_df[(search_df['timestamp'] >= cutoff_date) & (search_df['timestamp'] <= as_of)]

        # Exclude the transaction itself if it's in the dataset
        if 'transaction_id' in transaction and 'transaction_id' in search_df.columns:
            tx_id = transaction['transaction_id']
            search_df = search_df[search_df['transaction_id'] != tx_id]
        elif 'transaction_id' in search_df.columns and len(transaction) == 1:
            # If transaction is a DataFrame row
            tx_id = transaction.iloc[0]['transaction_id']
            search_df = search_df[search_df['transaction_id'] != tx_id]

        if search_df.empty:
            return {
                "transaction_id": transaction.get('transaction_id', 'unknown') if isinstance(transaction, pd.Series) else transaction.iloc[0].get('transaction_id', 'unknown'),
                "similar_transactions": [],
                "message": "No transactions found in the specified time period"
            }

        # Calculate similarity scores
        similarities = []
        tx_values = {}

        # Extract values from the transaction to compare
        if isinstance(transaction, pd.Series):
            for col in available_cols:
                tx_values[col] = transaction[col]
        else:  # DataFrame
            for col in available_cols:
                tx_values[col] = transaction.iloc[0][col]

        # Calculate similarity for each transaction in search_df
        for _, row in search_df.iterrows():
            try:
                # Calculate normalized similarity for each feature
                feature_similarities = []
                for col in available_cols:
                    tx_val = tx_values[col]
                    row_val = row[col]

                    # Handle different data types
                    if pd.isna(tx_val) and pd.isna(row_val):
                        similarity = 1.0  # Both missing
                    elif pd.isna(tx_val) or pd.isna(row_val):
                        similarity = 0.0  # One missing
                    else:
                        # For numerical features, use normalized difference
                        if col in ['amount', 'velocity_1h', 'ip_risk_score', 'amount_vs_avg_ratio', 'time_since_last_s']:
                            # Avoid division by zero
                            max_val = max(abs(tx_val), abs(row_val), 1)
                            if max_val == 0:
                                similarity = 1.0
                            else:
                                similarity = 1.0 - (abs(tx_val - row_val) / max_val)
                        elif col in ['is_foreign_txn']:
                            # Binary feature
                            similarity = 1.0 if tx_val == row_val else 0.0
                        else:
                            # Default to exact match for other types
                            similarity = 1.0 if tx_val == row_val else 0.0

                        feature_similarities.append(max(0, similarity))  # Ensure non-negative

                # Overall similarity is average of feature similarities
                if feature_similarities:
                    overall_similarity = np.mean(feature_similarities)
                    if overall_similarity >= similarity_threshold:
                        similarities.append({
                            'transaction_id': row['transaction_id'],
                            'similarity_score': overall_similarity,
                            'transaction_data': row.to_dict()
                        })
            except Exception:
                # Skip transactions that cause errors in similarity calculation
                continue

        # Sort by similarity score (descending) and limit results
        similarities.sort(key=lambda x: x['similarity_score'], reverse=True)
        top_similar = similarities[:max_results]

        # Convert transaction data timestamps to strings for JSON serialization
        for sim in top_similar:
            if 'transaction_data' in sim and 'timestamp' in sim['transaction_data']:
                ts = sim['transaction_data']['timestamp']
                if pd.notna(ts):
                    if isinstance(ts, str):
                        # Already a string, keep as is
                        pass
                    else:
                        # Convert to string
                        sim['transaction_data']['timestamp'] = ts.isoformat() if hasattr(ts, 'isoformat') else str(ts)

        return {
            "transaction_id": transaction.get('transaction_id', 'unknown') if isinstance(transaction, pd.Series) else transaction.iloc[0].get('transaction_id', 'unknown'),
            "search_period_days": days_back,
            "similarity_threshold": similarity_threshold,
            "similar_transactions_count": len(top_similar),
            "similar_transactions": top_similar
        }

    def get_transaction_patterns(self,
                               account_id: str,
                               days_back: int = 60,
                               reference_timestamp: Optional[Any] = None) -> Dict[str, Any]:
        """
        Analyze transaction patterns for an account over time.

        Args:
            account_id: ID of the account to analyze
            days_back: Number of days to look back

        Returns:
            Dictionary containing transaction pattern analysis
        """
        if self.transactions_df.empty:
            return {"error": "Transaction data not available"}

        # Filter transactions for this account
        if 'account_id' not in self.transactions_df.columns:
            return {"error": "Account ID column not found in transaction data"}

        account_tx = self.transactions_df[
            self.transactions_df['account_id'] == account_id
        ].copy()

        if account_tx.empty:
            return {
                "account_id": account_id,
                "message": "No transactions found for this account"
            }

        # Filter by time if timestamp column exists
        if 'timestamp' in account_tx.columns:
            as_of = pd.Timestamp(reference_timestamp) if reference_timestamp is not None else account_tx['timestamp'].max()
            cutoff_date = as_of - timedelta(days=days_back)
            account_tx = account_tx[(account_tx['timestamp'] >= cutoff_date) & (account_tx['timestamp'] <= as_of)]

        if account_tx.empty:
            return {
                "account_id": account_id,
                "period_days": days_back,
                "transaction_count": 0,
                "message": "No transactions found in the specified time period"
            }

        # Sort by timestamp
        if 'timestamp' in account_tx.columns:
            account_tx = account_tx.sort_values('timestamp')

        # Calculate time-based patterns
        patterns = {}

        if 'timestamp' in account_tx.columns and len(account_tx) > 1:
            # Time between transactions
            time_diffs = account_tx['timestamp'].diff().dt.total_seconds() / 3600  # Convert to hours
            time_diffs = time_diffs.dropna()  # Remove first NaN

            if len(time_diffs) > 0:
                patterns['time_between_transactions'] = {
                    'mean_hours': time_diffs.mean(),
                    'median_hours': time_diffs.median(),
                    'std_hours': time_diffs.std(),
                    'min_hours': time_diffs.min(),
                    'max_hours': time_diffs.max()
                }

        # Amount patterns
        if 'amount' in account_tx.columns:
            patterns['amount_patterns'] = {
                'mean': account_tx['amount'].mean(),
                'median': account_tx['amount'].median(),
                'std': account_tx['amount'].std(),
                'min': account_tx['amount'].min(),
                'max': account_tx['amount'].max(),
                'count': len(account_tx)
            }

        # Velocity patterns
        if 'velocity_1h' in account_tx.columns:
            patterns['velocity_patterns'] = {
                'mean': account_tx['velocity_1h'].mean(),
                'median': account_tx['velocity_1h'].median(),
                'std': account_tx['velocity_1h'].std(),
                'min': account_tx['velocity_1h'].min(),
                'max': account_tx['velocity_1h'].max()
            }

        # Foreign transaction patterns
        if 'is_foreign_txn' in account_tx.columns:
            patterns['foreign_transaction_patterns'] = {
                'count': account_tx['is_foreign_txn'].sum(),
                'rate': account_tx['is_foreign_txn'].mean(),
                'percentage': account_tx['is_foreign_txn'].mean() * 100
            }

        # Fraud patterns (if label exists)
        if 'is_fraud' in account_tx.columns:
            patterns['fraud_patterns'] = {
                'count': account_tx['is_fraud'].sum(),
                'rate': account_tx['is_fraud'].mean(),
                'percentage': account_tx['is_fraud'].mean() * 100
            }

        # Recent transactions (last 5)
        recent_tx = []
        if len(account_tx) > 0:
            cols_to_show = ['timestamp', 'amount', 'is_fraud', 'velocity_1h', 'is_foreign_txn']
            available_cols = [col for col in cols_to_show if col in account_tx.columns]
            if available_cols:
                recent_tx = account_tx.tail(5)[available_cols].to_dict('records')
                # Convert timestamps to strings
                for tx in recent_tx:
                    if 'timestamp' in tx and pd.notna(tx['timestamp']):
                        ts = tx['timestamp']
                        if isinstance(ts, str):
                            pass
                        else:
                            tx['timestamp'] = ts.isoformat() if hasattr(ts, 'isoformat') else str(ts)

        return {
            "account_id": account_id,
            "period_days": days_back,
            "transaction_count": len(account_tx),
            "patterns": patterns,
            "recent_transactions": recent_tx,
            "analysis_timestamp": datetime.now().isoformat()
        }

    def investigate_transaction(self,
                              transaction_id: str,
                              include_similar: bool = True) -> Dict[str, Any]:
        """
        Perform a comprehensive investigation of a transaction.

        Args:
            transaction_id: ID of the transaction to investigate
            include_similar: Whether to include similar transaction analysis

        Returns:
            Dictionary containing all transaction history investigation results
        """
        # Get transaction details
        tx_details = self.get_transaction_details(transaction_id)
        if "error" in tx_details:
            return tx_details

        # Extract transaction as Series for similarity search
        tx_row = self.transactions_df[self.transactions_df['transaction_id'] == transaction_id].iloc[0]

        results = {
            "transaction_id": transaction_id,
            "transaction_details": tx_details["details"],
            "transaction_patterns": None,
            "similar_transactions": None
        }

        # Get account ID from transaction for pattern analysis
        if 'account_id' in tx_row:
            account_id = tx_row['account_id']
            results["transaction_patterns"] = self.get_transaction_patterns(account_id, days_back=60)

        # Get similar transactions if requested
        if include_similar:
            results["similar_transactions"] = self.get_similar_transactions(
                tx_row,
                days_back=30,
                similarity_threshold=0.7,
                max_results=5
            )

        return results
