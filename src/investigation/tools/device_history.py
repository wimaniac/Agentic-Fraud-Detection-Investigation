"""
Device History Tool for Investigation Agent
Provides historical analysis of device usage and associations
"""
import pandas as pd
import numpy as np
from typing import Dict, Any, Optional
from pathlib import Path
from datetime import datetime, timedelta

class DeviceHistoryTool:
    """
    Tool for analyzing historical device usage patterns to support fraud investigations.
    """

    def __init__(self, data_dir: str = "data/processed/fraud_1m_processed"):
        """
        Initialize the Device History Tool.

        Args:
            data_dir: Directory containing processed data
        """
        self.data_dir = Path(data_dir)
        self.transactions_df = None
        self._load_data()

    def _load_data(self):
        """Load transaction data"""
        try:
            self.transactions_df = pd.read_parquet(self.data_dir / "transactions_clean.parquet")
            if 'timestamp' in self.transactions_df.columns:
                self.transactions_df['timestamp'] = pd.to_datetime(self.transactions_df['timestamp'])
            print(f"Loaded device data: {len(self.transactions_df)} transactions")
        except Exception as e:
            print(f"Warning: Could not load device data: {e}")
            self.transactions_df = pd.DataFrame()

    def get_device_usage_history(self,
                               device_id: str,
                               days_back: int = 60,
                               reference_timestamp: Optional[Any] = None) -> Dict[str, Any]:
        """
        Get usage history for a specific device.

        Args:
            device_id: ID of the device to query (we'll use proxy from transaction data)
            days_back: Number of days to look back

        Returns:
            Dictionary containing device usage history
        """
        # Note: In the current dataset, we don't have explicit device IDs
        # We'll use device_known flag and other device-related features as proxies
        # For a real implementation, this would connect to device fingerprinting data

        if self.transactions_df.empty:
            return {"error": "Transaction data not available"}

        # We'll analyze transactions where device_known = 0 (unknown devices)
        # as these are more suspicious
        if 'device_known' not in self.transactions_df.columns:
            return {"error": "Device knowledge data not available"}

        # Filter by time if timestamp exists
        device_tx = self.transactions_df.copy()
        if 'timestamp' in device_tx.columns:
            as_of = pd.Timestamp(reference_timestamp) if reference_timestamp is not None else device_tx['timestamp'].max()
            cutoff_date = as_of - timedelta(days=days_back)
            device_tx = device_tx[(device_tx['timestamp'] >= cutoff_date) & (device_tx['timestamp'] <= as_of)]

        if device_tx.empty:
            return {
                "device_id": device_id or "unknown",
                "period_days": days_back,
                "message": "No transactions found in the specified time period"
            }

        # Analyze unknown device usage
        unknown_device_tx = device_tx[device_tx['device_known'] == 0] if 'device_known' in device_tx.columns else pd.DataFrame()
        known_device_tx = device_tx[device_tx['device_known'] == 1] if 'device_known' in device_tx.columns else pd.DataFrame()

        # Calculate statistics
        stats = {
            "total_transactions": len(device_tx),
            "unknown_device_transactions": len(unknown_device_tx),
            "known_device_transactions": len(known_device_tx),
            "unknown_device_ratio": len(unknown_device_tx) / len(device_tx) if len(device_tx) > 0 else 0
        }

        if len(unknown_device_tx) > 0:
            stats.update({
                "unknown_device_avg_amount": unknown_device_tx['amount'].mean() if 'amount' in unknown_device_tx.columns else 0,
                "unknown_device_fraud_rate": unknown_device_tx['is_fraud'].mean() if 'is_fraud' in unknown_device_tx.columns else 0,
                "unknown_device_avg_velocity": unknown_device_tx['velocity_1h'].mean() if 'velocity_1h' in unknown_device_tx.columns else 0
            })

        # Get recent unknown device transactions
        recent_unknown = []
        if len(unknown_device_tx) > 0 and 'timestamp' in unknown_device_tx.columns:
            recent_unknown = unknown_device_tx.tail(5)[[
                'timestamp', 'amount', 'is_fraud', 'velocity_1h', 'account_id'
            ]].to_dict('records') if all(col in unknown_device_tx.columns for col in
                                        ['timestamp', 'amount', 'is_fraud', 'velocity_1h', 'account_id']) else []
            # Convert timestamps
            for tx in recent_unknown:
                if 'timestamp' in tx and pd.notna(tx['timestamp']):
                    ts = tx['timestamp']
                    if isinstance(ts, str):
                        pass
                    else:
                        tx['timestamp'] = ts.isoformat() if hasattr(ts, 'isoformat') else str(ts)

        return {
            "device_id": device_id or "unknown_device_analysis",
            "period_days": days_back,
            "usage_statistics": stats,
            "recent_unknown_device_transactions": recent_unknown,
            "evidence_assessment": {
                "severity_level": "HIGH" if stats["unknown_device_ratio"] > 0.5 else
                             "MEDIUM" if stats["unknown_device_ratio"] > 0.2 else
                             "LOW" if stats["unknown_device_ratio"] > 0.05 else
                             "VERY LOW",
                "description": f"Ratio of unknown device usage: {stats['unknown_device_ratio']*100:.1f}%"
            },
            "analysis_timestamp": datetime.now().isoformat()
        }

    def get_device_sharing_patterns(self,
                                  account_id: str,
                                  days_back: int = 60,
                                  reference_timestamp: Optional[Any] = None) -> Dict[str, Any]:
        """
        Analyze device sharing patterns for an account.

        Args:
            account_id: ID of the account to analyze
            days_back: Number of days to look back

        Returns:
            Dictionary containing device sharing analysis
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

        # Analyze device sharing using n_shared_types feature as proxy
        if 'n_shared_types' in account_tx.columns:
            sharing_stats = {
                "total_transactions": len(account_tx),
                "avg_shared_types": account_tx['n_shared_types'].mean(),
                "max_shared_types": account_tx['n_shared_types'].max(),
                "high_sharing_transactions": len(account_tx[account_tx['n_shared_types'] >= 3]),  # 3+ shared types
                "high_sharing_ratio": len(account_tx[account_tx['n_shared_types'] >= 3]) / len(account_tx) if len(account_tx) > 0 else 0
            }

            # Get transactions with high sharing
            high_sharing_tx = account_tx[account_tx['n_shared_types'] >= 3] if len(account_tx) > 0 else pd.DataFrame()
            recent_high_sharing = []
            if len(high_sharing_tx) > 0 and 'timestamp' in high_sharing_tx.columns:
                recent_high_sharing = high_sharing_tx.tail(3)[[
                    'timestamp', 'amount', 'n_shared_types', 'is_fraud'
                ]].to_dict('records') if all(col in high_sharing_tx.columns for col in
                                           ['timestamp', 'amount', 'n_shared_types', 'is_fraud']) else []
                # Convert timestamps
                for tx in recent_high_sharing:
                    if 'timestamp' in tx and pd.notna(tx['timestamp']):
                        ts = tx['timestamp']
                        if isinstance(ts, str):
                            pass
                        else:
                            tx['timestamp'] = ts.isoformat() if hasattr(ts, 'isoformat') else str(ts)
        else:
            sharing_stats = {
                "error": "Device sharing data (n_shared_types) not available"
            }
            recent_high_sharing = []

        return {
            "account_id": account_id,
            "period_days": days_back,
            "device_sharing_statistics": sharing_stats,
            "recent_high_sharing_transactions": recent_high_sharing,
            "evidence_assessment": {
                "severity_level": "HIGH" if sharing_stats.get("high_sharing_ratio", 0) > 0.5 else
                             "MEDIUM" if sharing_stats.get("high_sharing_ratio", 0) > 0.2 else
                             "LOW" if sharing_stats.get("high_sharing_ratio", 0) > 0.05 else
                             "VERY LOW",
                "description": f"Ratio of high device sharing transactions: {sharing_stats.get('high_sharing_ratio', 0)*100:.1f}%"
            },
            "analysis_timestamp": datetime.now().isoformat()
        }

    def investigate_device(self,
                          device_id: Optional[str] = None,
                          account_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Perform a comprehensive investigation related to device usage.

        Args:
            device_id: ID of the device to investigate (optional)
            account_id: ID of the account to analyze device usage for (optional)

        Returns:
            Dictionary containing device history investigation results
        """
        results = {
            "investigation_timestamp": datetime.now().isoformat()
        }

        if device_id:
            results["device_usage"] = self.get_device_usage_history(device_id, days_back=60)

        if account_id:
            results["device_sharing"] = self.get_device_sharing_patterns(account_id, days_back=60)

        return results
