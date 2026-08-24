"""
IP History Tool for Investigation Agent
Provides historical analysis of IP address usage and reputation
"""
import pandas as pd
import numpy as np
from typing import Dict, Any, Optional
from pathlib import Path
from datetime import datetime, timedelta

class IPHistoryTool:
    """
    Tool for analyzing historical IP address usage patterns to support fraud investigations.
    """

    def __init__(self, data_dir: str = "data/processed/fraud_1m_processed"):
        """
        Initialize the IP History Tool.

        Args:
            data_dir: Directory containing processed data
        """
        self.data_dir = Path(data_dir)
        self.transactions_df = None
        self.accounts_df = None
        self._load_data()

    def _load_data(self):
        """Load transaction and account data"""
        try:
            self.transactions_df = pd.read_parquet(self.data_dir / "transactions_clean.parquet")
            self.accounts_df = pd.read_parquet(self.data_dir / "account_profiles_clean.parquet")
            if 'timestamp' in self.transactions_df.columns:
                self.transactions_df['timestamp'] = pd.to_datetime(self.transactions_df['timestamp'])
            print(f"Loaded IP data: {len(self.transactions_df)} transactions, {len(self.accounts_df)} accounts")
        except Exception as e:
            print(f"Warning: Could not load IP data: {e}")
            self.transactions_df = pd.DataFrame()
            self.accounts_df = pd.DataFrame()

    def get_ip_usage_history(self,
                           ip_address: str,
                           days_back: int = 60,
                           reference_timestamp: Optional[Any] = None) -> Dict[str, Any]:
        """
        Get usage history for a specific IP address.

        Args:
            ip_address: IP address to query (we'll use proxy from transaction data)
            days_back: Number of days to look back

        Returns:
            Dictionary containing IP usage history
        """
        # Note: In the current dataset, we don't have explicit IP addresses
        # We'll use ip_risk_score and ip_risk_high features as proxies
        # For a real implementation, this would connect to IP reputation databases

        if self.transactions_df.empty:
            return {"error": "Transaction data not available"}

        # We'll analyze transactions with high IP risk scores as suspicious
        if 'ip_risk_score' not in self.transactions_df.columns:
            return {"error": "IP risk score data not available"}

        # Filter by time if timestamp exists
        ip_tx = self.transactions_df.copy()
        if 'timestamp' in ip_tx.columns:
            as_of = pd.Timestamp(reference_timestamp) if reference_timestamp is not None else ip_tx['timestamp'].max()
            cutoff_date = as_of - timedelta(days=days_back)
            ip_tx = ip_tx[(ip_tx['timestamp'] >= cutoff_date) & (ip_tx['timestamp'] <= as_of)]

        if ip_tx.empty:
            return {
                "ip_address": ip_address or "unknown",
                "period_days": days_back,
                "message": "No transactions found in the specified time period"
            }

        # Analyze high-risk IP usage
        high_risk_ip_tx = ip_tx[ip_tx['ip_risk_score'] >= 50] if 'ip_risk_score' in ip_tx.columns else pd.DataFrame()
        medium_risk_ip_tx = ip_tx[(ip_tx['ip_risk_score'] >= 20) & (ip_tx['ip_risk_score'] < 50)] if 'ip_risk_score' in ip_tx.columns else pd.DataFrame()
        low_risk_ip_tx = ip_tx[ip_tx['ip_risk_score'] < 20] if 'ip_risk_score' in ip_tx.columns else pd.DataFrame()

        # Calculate statistics
        stats = {
            "total_transactions": len(ip_tx),
            "high_risk_ip_transactions": len(high_risk_ip_tx),
            "medium_risk_ip_transactions": len(medium_risk_ip_tx),
            "low_risk_ip_transactions": len(low_risk_ip_tx),
            "high_risk_ip_ratio": len(high_risk_ip_tx) / len(ip_tx) if len(ip_tx) > 0 else 0
        }

        if len(high_risk_ip_tx) > 0:
            stats.update({
                "high_risk_ip_avg_amount": high_risk_ip_tx['amount'].mean() if 'amount' in high_risk_ip_tx.columns else 0,
                "high_risk_ip_fraud_rate": high_risk_ip_tx['is_fraud'].mean() if 'is_fraud' in high_risk_ip_tx.columns else 0,
                "high_risk_ip_avg_velocity": high_risk_ip_tx['velocity_1h'].mean() if 'velocity_1h' in high_risk_ip_tx.columns else 0
            })

        # Get recent high-risk IP transactions
        recent_high_risk = []
        if len(high_risk_ip_tx) > 0 and 'timestamp' in high_risk_ip_tx.columns:
            recent_high_risk = high_risk_ip_tx.tail(5)[[
                'timestamp', 'amount', 'ip_risk_score', 'is_fraud', 'account_id'
            ]].to_dict('records') if all(col in high_risk_ip_tx.columns for col in
                                        ['timestamp', 'amount', 'ip_risk_score', 'is_fraud', 'account_id']) else []
            # Convert timestamps
            for tx in recent_high_risk:
                if 'timestamp' in tx and pd.notna(tx['timestamp']):
                    ts = tx['timestamp']
                    if isinstance(ts, str):
                        pass
                    else:
                        tx['timestamp'] = ts.isoformat() if hasattr(ts, 'isoformat') else str(ts)

        return {
            "ip_address": ip_address or "unknown_ip_analysis",
            "period_days": days_back,
            "usage_statistics": stats,
            "recent_high_risk_ip_transactions": recent_high_risk,
            "evidence_assessment": {
                "severity_level": "HIGH" if stats["high_risk_ip_ratio"] > 0.3 else
                             "MEDIUM" if stats["high_risk_ip_ratio"] > 0.1 else
                             "LOW" if stats["high_risk_ip_ratio"] > 0.03 else
                             "VERY LOW",
                "description": f"Ratio of high-risk IP usage: {stats['high_risk_ip_ratio']*100:.1f}%"
            },
            "analysis_timestamp": datetime.now().isoformat()
        }

    def get_ip_reputation_trends(self,
                               account_id: str,
                               days_back: int = 60,
                               reference_timestamp: Optional[Any] = None) -> Dict[str, Any]:
        """
        Analyze IP reputation trends for an account.

        Args:
            account_id: ID of the account to analyze
            days_back: Number of days to look back

        Returns:
            Dictionary containing IP reputation analysis
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

        # Filter by time if timestamp exists
        if 'timestamp' in account_tx.columns:
            as_of = pd.Timestamp(reference_timestamp) if reference_timestamp is not None else account_tx['timestamp'].max()
            cutoff_date = as_of - timedelta(days=days_back)
            account_tx = account_tx[(account_tx['timestamp'] >= cutoff_date) & (account_tx['timestamp'] <= as_of)]

        # Analyze IP risk trends using ip_risk_score feature
        if 'ip_risk_score' in account_tx.columns and len(account_tx) > 0:
            # Sort by timestamp to see trends
            if 'timestamp' in account_tx.columns:
                account_tx = account_tx.sort_values('timestamp')

            ip_stats = {
                "total_transactions": len(account_tx),
                "avg_ip_risk_score": account_tx['ip_risk_score'].mean(),
                "max_ip_risk_score": account_tx['ip_risk_score'].max(),
                "min_ip_risk_score": account_tx['ip_risk_score'].min(),
                "std_ip_risk_score": account_tx['ip_risk_score'].std(),
                "high_risk_transactions": len(account_tx[account_tx['ip_risk_score'] >= 50]),
                "high_risk_ratio": len(account_tx[account_tx['ip_risk_score'] >= 50]) / len(account_tx)
            }

            # Calculate trend (increasing/decreasing risk over time)
            if len(account_tx) >= 2 and 'timestamp' in account_tx.columns:
                # Split into first and second half
                mid_point = len(account_tx) // 2
                first_half = account_tx.iloc[:mid_point]
                second_half = account_tx.iloc[mid_point:]

                if len(first_half) > 0 and len(second_half) > 0:
                    first_half_avg = first_half['ip_risk_score'].mean()
                    second_half_avg = second_half['ip_risk_score'].mean()
                    trend_change = second_half_avg - first_half_avg
                    ip_stats["risk_trend"] = {
                        "direction": "INCREASING" if trend_change > 5 else "DECREASING" if trend_change < -5 else "STABLE",
                        "change_points": trend_change,
                        "first_half_avg": first_half_avg,
                        "second_half_avg": second_half_avg
                    }
                else:
                    ip_stats["risk_trend"] = {
                        "direction": "INSUFFICIENT DATA",
                        "change_points": 0
                    }
            else:
                ip_stats["risk_trend"] = {
                    "direction": "INSUFFICIENT DATA",
                    "change_points": 0
                }

            # Get recent high-risk IP transactions
            recent_high_risk = []
            if len(account_tx[account_tx['ip_risk_score'] >= 50]) > 0:
                high_risk_subset = account_tx[account_tx['ip_risk_score'] >= 50]
                if 'timestamp' in high_risk_subset.columns:
                    recent_high_risk = high_risk_subset.tail(3)[[
                        'timestamp', 'amount', 'ip_risk_score', 'is_fraud'
                    ]].to_dict('records') if all(col in high_risk_subset.columns for col in
                                               ['timestamp', 'amount', 'ip_risk_score', 'is_fraud']) else []
                    # Convert timestamps
                    for tx in recent_high_risk:
                        if 'timestamp' in tx and pd.notna(tx['timestamp']):
                            ts = tx['timestamp']
                            if isinstance(ts, str):
                                pass
                            else:
                                tx['timestamp'] = ts.isoformat() if hasattr(ts, 'isoformat') else str(ts)
            else:
                recent_high_risk = []
        else:
            ip_stats = {
                "error": "IP risk score data not available"
            }
            recent_high_risk = []

        return {
            "account_id": account_id,
            "period_days": days_back,
            "ip_reputation_statistics": ip_stats,
            "recent_high_risk_ip_transactions": recent_high_risk,
            "evidence_assessment": {
                "severity_level": "HIGH" if ip_stats.get("high_risk_ratio", 0) > 0.4 else
                             "MEDIUM" if ip_stats.get("high_risk_ratio", 0) > 0.2 else
                             "LOW" if ip_stats.get("high_risk_ratio", 0) > 0.05 else
                             "VERY LOW",
                "description": f"Ratio of transactions with high-risk IP: {ip_stats.get('high_risk_ratio', 0)*100:.1f}%"
            },
            "analysis_timestamp": datetime.now().isoformat()
        }

    def investigate_ip(self,
                      ip_address: Optional[str] = None,
                      account_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Perform a comprehensive investigation related to IP address usage.

        Args:
            ip_address: IP address to investigate (optional)
            account_id: ID of the account to analyze IP usage for (optional)

        Returns:
            Dictionary containing IP history investigation results
        """
        results = {
            "investigation_timestamp": datetime.now().isoformat()
        }

        if ip_address:
            results["ip_usage"] = self.get_ip_usage_history(ip_address, days_back=60)

        if account_id:
            results["ip_reputation"] = self.get_ip_reputation_trends(account_id, days_back=60)

        return results
