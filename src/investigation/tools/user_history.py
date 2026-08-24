"""
User History Tool for Investigation Agent
Provides historical behavior analysis of users/accounts
"""
import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime, timedelta

class UserHistoryTool:
    """
    Tool for analyzing historical behavior of users/accounts to support fraud investigations.
    """

    def __init__(self, data_dir: str = "data/processed/fraud_1m_processed"):
        """
        Initialize the User History Tool.

        Args:
            data_dir: Directory containing processed transaction data
        """
        self.data_dir = Path(data_dir)
        self.transactions_df = None
        self.accounts_df = None
        self._load_data()

    def _load_data(self):
        """Load historical transaction and account data"""
        try:
            self.transactions_df = pd.read_parquet(self.data_dir / "transactions_clean.parquet")
            self.accounts_df = pd.read_parquet(self.data_dir / "account_profiles_clean.parquet")
            # Ensure timestamp is datetime
            if 'timestamp' in self.transactions_df.columns:
                self.transactions_df['timestamp'] = pd.to_datetime(self.transactions_df['timestamp'])
            print(f"Loaded historical data: {len(self.transactions_df)} transactions, {len(self.accounts_df)} accounts")
        except Exception as e:
            print(f"Warning: Could not load historical data: {e}")
            # Create empty dataframes to prevent crashes
            self.transactions_df = pd.DataFrame()
            self.accounts_df = pd.DataFrame()

    def get_user_profile(self, account_id: str) -> Dict[str, Any]:
        """
        Get basic profile information for an account.

        Args:
            account_id: ID of the account to query

        Returns:
            Dictionary containing account profile information
        """
        if self.accounts_df.empty or 'account_id' not in self.accounts_df.columns:
            return {"error": "Account data not available"}

        account_info = self.accounts_df[self.accounts_df['account_id'] == account_id]
        if account_info.empty:
            return {"error": f"Account {account_id} not found"}

        account_data = account_info.iloc[0].to_dict()
        return {
            "account_id": account_id,
            "account_age_days": account_data.get('account_age_days', 0),
            "credit_limit": account_data.get('credit_limit', 0),
            "risk_score": account_data.get('risk_score', 0),
            "is_high_risk": account_data.get('is_high_risk', False),
            "fraud_rate": account_data.get('fraud_rate', 0.0),
            "is_fraudster": account_data.get('is_fraudster', False),
            "avg_amount": account_data.get('avg_amount', 0.0)
        }

    def get_transaction_history(self,
                              account_id: str,
                              days_back: int = 30,
                              max_transactions: int = 100,
                              reference_timestamp: Optional[Any] = None) -> Dict[str, Any]:
        """
        Get transaction history for an account.

        Args:
            account_id: ID of the account to query
            days_back: Number of days to look back
            max_transactions: Maximum number of transactions to return

        Returns:
            Dictionary containing transaction history and statistics
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
                "transaction_count": 0,
                "message": "No transactions found for this account"
            }

        # Filter by time if timestamp column exists
        if 'timestamp' in account_tx.columns:
            as_of = pd.Timestamp(reference_timestamp) if reference_timestamp is not None else account_tx['timestamp'].max()
            cutoff_date = as_of - timedelta(days=days_back)
            account_tx = account_tx[(account_tx['timestamp'] >= cutoff_date) & (account_tx['timestamp'] <= as_of)]

        # Sort by timestamp (most recent first) and limit
        if 'timestamp' in account_tx.columns:
            account_tx = account_tx.sort_values('timestamp', ascending=False).head(max_transactions)
        else:
            account_tx = account_tx.head(max_transactions)

        # Calculate statistics
        stats = {}
        if len(account_tx) > 0:
            stats = {
                "transaction_count": len(account_tx),
                "total_amount": account_tx['amount'].sum() if 'amount' in account_tx.columns else 0,
                "avg_amount": account_tx['amount'].mean() if 'amount' in account_tx.columns else 0,
                "std_amount": account_tx['amount'].std() if 'amount' in account_tx.columns else 0,
                "fraud_count": account_tx['is_fraud'].sum() if 'is_fraud' in account_tx.columns else 0,
                "fraud_rate": account_tx['is_fraud'].mean() if 'is_fraud' in account_tx.columns else 0,
                "avg_velocity": account_tx['velocity_1h'].mean() if 'velocity_1h' in account_tx.columns else 0,
                "max_velocity": account_tx['velocity_1h'].max() if 'velocity_1h' in account_tx.columns else 0,
                "foreign_txn_rate": account_tx['is_foreign_txn'].mean() if 'is_foreign_txn' in account_tx.columns else 0
            }

        # Get recent transactions (last 5)
        recent_tx = []
        if len(account_tx) > 0 and 'timestamp' in account_tx.columns:
            recent_tx = account_tx.head(5)[[
                'timestamp', 'amount', 'is_fraud', 'velocity_1h', 'is_foreign_txn'
            ]].to_dict('records') if all(col in account_tx.columns for col in
                                        ['timestamp', 'amount', 'is_fraud', 'velocity_1h', 'is_foreign_txn']) else []
        elif len(account_tx) > 0:
            recent_tx = account_tx.head(5).to_dict('records')

        return {
            "account_id": account_id,
            "period_days": days_back,
            "transaction_count": len(account_tx),
            "statistics": stats,
            "recent_transactions": recent_tx,
            "data_timestamp": datetime.now().isoformat() if 'timestamp' in account_tx.columns and len(account_tx) > 0 else None
        }

    def get_behavioral_anomalies(self,
                               account_id: str,
                               current_transaction: Optional[pd.Series] = None) -> Dict[str, Any]:
        """
        Detect behavioral anomalies by comparing current transaction to historical patterns.

        Args:
            account_id: ID of the account to analyze
            current_transaction: Current transaction data (optional)

        Returns:
            Dictionary containing behavioral anomaly analysis
        """
        reference_timestamp = current_transaction.get('timestamp') if current_transaction is not None else None
        history = self.get_transaction_history(account_id, days_back=60, reference_timestamp=reference_timestamp)
        if "error" in history:
            return history

        if history["transaction_count"] == 0:
            return {
                "account_id": account_id,
                "anomaly_detected": False,
                "reason": "No historical data available for comparison"
            }

        stats = history["statistics"]
        anomalies = []

        if current_transaction is not None:
            # Compare current transaction to historical averages
            if 'amount' in current_transaction and 'avg_amount' in stats:
                historical_avg = stats['avg_amount']
                current_amount = current_transaction['amount']
                if historical_avg > 0:
                    ratio = current_amount / historical_avg
                    if ratio > 5:  # More than 5x historical average
                        anomalies.append({
                            "type": "amount_spike",
                            "description": f"Current transaction amount ({current_amount:,.0f}) exceeds {ratio:.1f} times the historical average ({historical_avg:,.0f})",
                            "severity": "high" if ratio > 10 else "medium"
                        })

            if 'velocity_1h' in current_transaction and 'avg_velocity' in stats:
                historical_avg_vel = stats['avg_velocity']
                current_vel = current_transaction['velocity_1h']
                if historical_avg_vel > 0:
                    vel_ratio = current_vel / historical_avg_vel
                    if vel_ratio > 3:  # More than 3x historical velocity
                        anomalies.append({
                            "type": "velocity_spike",
                            "description": f"Current transaction velocity ({current_vel:.1f}/hour) exceeds {vel_ratio:.1f} times the historical average ({historical_avg_vel:.1f}/hour)",
                            "severity": "high" if vel_ratio > 5 else "medium"
                        })

            if 'is_foreign_txn' in current_transaction:
                historical_foreign_rate = stats.get('foreign_txn_rate', 0)
                current_is_foreign = current_transaction['is_foreign_txn']
                if historical_foreign_rate < 0.5 and current_is_foreign == 1:  # Normally domestic, now foreign
                    anomalies.append({
                        "type": "foreign_transaction",
                        "description": "Foreign transaction unusual for account that typically conducts domestic transactions",
                        "severity": "medium"
                    })

        # Check for sudden changes in behavior compared to recent history
        if len(history["recent_transactions"]) >= 3:
            recent_tx = history["recent_transactions"]
            if all('amount' in tx for tx in recent_tx):
                recent_amounts = [tx['amount'] for tx in recent_tx]
                recent_avg = np.mean(recent_amounts)
                recent_std = np.std(recent_amounts) if len(recent_amounts) > 1 else 0

                if current_transaction is not None and 'amount' in current_transaction:
                    current_amount = current_transaction['amount']
                    if recent_std > 0:
                        z_score = abs((current_amount - recent_avg) / recent_std)
                        if z_score > 3:  # More than 3 standard deviations from recent mean
                            anomalies.append({
                                "type": "recent_behavior_change",
                                "description": f"Current transaction amount ({current_amount:,.0f}) significantly deviates from recent trend (Avg: {recent_avg:,.0f}, SD: {recent_std:,.0f})",
                                "severity": "high" if z_score > 4 else "medium"
                            })

        return {
            "account_id": account_id,
            "historical_transaction_count": history["transaction_count"],
            "anomalies_detected": len(anomalies) > 0,
            "anomaly_count": len(anomalies),
            "anomalies": anomalies,
            "behavioral_score": min(len(anomalies) * 25, 100),  # Simple scoring: 25 points per anomaly, max 100
            "recommendation": "Requires further investigation" if len(anomalies) > 0 else "Behavior within normal range"
        }

    def investigate_user(self,
                        account_id: str,
                        current_transaction: Optional[pd.Series] = None) -> Dict[str, Any]:
        """
        Perform a comprehensive investigation of a user's historical behavior.

        Args:
            account_id: ID of the account to investigate
            current_transaction: Current transaction data (optional)

        Returns:
            Dictionary containing all user history investigation results
        """
        profile = self.get_user_profile(account_id)
        reference_timestamp = current_transaction.get('timestamp') if current_transaction is not None else None
        history = self.get_transaction_history(account_id, days_back=30, reference_timestamp=reference_timestamp)
        anomalies = self.get_behavioral_anomalies(account_id, current_transaction)

        return {
            "account_id": account_id,
            "profile": profile,
            "transaction_history": history,
            "behavioral_analysis": anomalies,
            "investigation_timestamp": datetime.now().isoformat()
        }
