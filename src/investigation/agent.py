"""
AI Investigation Agent for SentinelAI
Main interface for conducting AI-powered investigations of suspicious transactions
"""
import pandas as pd
from typing import Dict, Any, Optional
from .workflow import InvestigationWorkflow

class InvestigationAgent:
    """
    AI Investigation Agent that orchestrates various tools to investigate
    suspicious transactions and generate comprehensive reports.
    """

    def __init__(self, data_dir: str = "data/processed/fraud_1m_processed", llm_model: Optional[str] = None):
        """
        Initialize the Investigation Agent.

        Args:
            data_dir: Directory containing processed data
        """
        self.workflow = InvestigationWorkflow(data_dir, llm_model=llm_model)
        print("Investigation Agent initialized successfully")

    def investigate_transaction(self,
                               transaction_data: pd.Series,
                               accounts_data: Optional[pd.DataFrame] = None,
                               edges_data: Optional[pd.DataFrame] = None) -> Dict[str, Any]:
        """
        Investigate a suspicious transaction and generate a comprehensive report.

        Args:
            transaction_data: Transaction data to investigate (as pandas Series)
            accounts_data: Account profiles data (optional, will load from default if not provided)
            edges_data: Network edges data (optional, will load from default if not provided)

        Returns:
            Dictionary containing complete investigation results and report
        """
        # Load only the missing default datasets. Read/parquet errors must be
        # visible to the caller instead of being silently replaced with empties.
        if accounts_data is None or edges_data is None:
            from pathlib import Path
            data_path = Path(self.workflow.data_dir)
            if accounts_data is None:
                accounts_file = data_path / "account_profiles_clean.parquet"
                accounts_data = pd.read_parquet(accounts_file) if accounts_file.exists() else pd.DataFrame()
            if edges_data is None:
                edges_file = data_path / "network_edges_clean.parquet"
                edges_data = pd.read_parquet(edges_file) if edges_file.exists() else pd.DataFrame()

        # Conduct the investigation
        investigation_result = self.workflow.investigate(
            transaction_data,
            accounts_data,
            edges_data
        )

        return investigation_result

    def get_investigation_report(self,
                                investigation_result: Dict[str, Any]) -> str:
        """
        Generate a human-readable investigation report from investigation results.

        Args:
            investigation_result: Results from investigate_transaction method

        Returns:
            String containing formatted investigation report
        """
        # Extract the reasoning from the investigation summary if available
        if "investigation_summary" in investigation_result:
            final_rec = investigation_result["investigation_summary"].get("final_recommendation", {})
            if "reasoning" in final_rec:
                return final_rec["reasoning"]

        # Fallback: generate a basic report
        report_lines = [
            "=" * 60,
            "TRANSACTION INVESTIGATION REPORT",
            "=" * 60,
            f"Transaction ID: {investigation_result.get('transaction_id', 'N/A')}",
            f"Investigation timestamp: {investigation_result.get('investigation_timestamp', 'N/A')}",
            "",
            "INVESTIGATION RESULTS:",
            f"  Recommended action: {investigation_result.get('recommended_action', 'N/A')}",
            f"  Action code: {investigation_result.get('action_code', 'N/A')}",
            f"  Confidence level: {investigation_result.get('confidence_score', 0):.1%}",
            ""
        ]

        # Add investigation summary if available
        if "investigation_summary" in investigation_result:
            summary = investigation_result["investigation_summary"]
            report_lines.extend([
                "INVESTIGATION SUMMARY:",
                f"  Composite risk score: {summary.get('composite_risk_score', 0):.1f}/100",
                f"  Risk tier: {summary.get('risk_tier', 'N/A')}",
                ""
            ])

            # Component scores
            components = summary.get("component_scores", {})
            if components:
                report_lines.append("SCORES BY COMPONENT:")
                for component, score in components.items():
                    report_lines.append(f"  - {component.replace('_', ' ').title()}: {score:.1f}/100")
                report_lines.append("")

            # Key findings
            key_findings = summary.get("key_findings", {})
            if key_findings.get("high_risk_factors"):
                report_lines.append("HIGH RISK FACTORS:")
                for factor in key_findings["high_risk_factors"]:
                    report_lines.append(f"  - {factor}")
                report_lines.append("")

        # Add errors if any
        errors = investigation_result.get("errors", [])
        if errors:
            report_lines.extend([
                "",
                "WARNINGS - DATA ISSUES:",
                *[f"  - {error}" for error in errors]
            ])

        report_lines.append("=" * 60)

        return "\n".join(report_lines)

    def quick_investigation(self,
                           transaction_id: str,
                           amount: float,
                           velocity_1h: float,
                           is_fraud: bool = False) -> Dict[str, Any]:
        """
        Conduct a quick investigation with synthetic demo data.

        Warning:
            This helper is for demonstrations only. Production callers must
            pass a complete processed transaction through
            ``investigate_transaction`` so that the same inference feature
            pipeline used in serving is applied to real inputs.

        Args:
            transaction_id: ID of the transaction
            amount: Transaction amount
            velocity_1h: Transaction velocity (transactions per hour)
            is_fraud: Whether the transaction is known to be fraud

        Returns:
            Dictionary containing investigation results
        """
        # Create a minimal transaction data series
        transaction_data = pd.Series({
            'transaction_id': transaction_id,
            'amount': amount,
            'velocity_1h': velocity_1h,
            'is_fraud': is_fraud,
            'timestamp': pd.Timestamp.now(),
            'account_id': 'UNKNOWN_ACCOUNT',  # Placeholder
            'hour_of_day': 12,
            'day_of_week': 0,
            'is_weekend': 0,
            'is_foreign_txn': 0,
            'ip_risk_score': 0,
            'amount_vs_avg_ratio': 1.0,
            'time_since_last_s': 3600,
            'card_present': 1,
            'device_known': 1,
            'has_2fa': 1,
            'account_age_days': 365,
            'credit_limit': max(amount * 2, 1.0),
            'n_shared_types': 0,
            'in_ring': 0,
            'account_degree': 0
        })

        return self.investigate_transaction(transaction_data)


# Convenience function for easy usage
def investigate_transaction(transaction_data: pd.Series,
                           accounts_data: Optional[pd.DataFrame] = None,
                           edges_data: Optional[pd.DataFrame] = None) -> Dict[str, Any]:
    """
    Convenience function to investigate a transaction.

    Args:
        transaction_data: Transaction data to investigate
        accounts_data: Account profiles data (optional)
        edges_data: Network edges data (optional)

    Returns:
        Dictionary containing investigation results
    """
    agent = InvestigationAgent()
    return agent.investigate_transaction(transaction_data, accounts_data, edges_data)


# Example usage
if __name__ == "__main__":
    # Example of how to use the Investigation Agent
    print("Initializing Investigation Agent...")
    agent = InvestigationAgent()

    # Create a sample transaction for demonstration
    sample_transaction = pd.Series({
        'transaction_id': 'TX_DEMO_001',
        'amount': 5000000,  # 5,000,000 VND
        'velocity_1h': 5.0,  # 5 transactions per hour
        'is_fraud': False,  # We don't know yet - that's what we're investigating
        'timestamp': pd.Timestamp.now(),
        'account_id': 'ACC_DEMO_001',
        'is_foreign_txn': 1,  # Foreign transaction
        'ip_risk_score': 75,  # High risk IP
        'amount_vs_avg_ratio': 8.5,  # 8.5x average amount
        'time_since_last_s': 1800,  # 30 minutes since last transaction
        'device_known': 0,  # Unknown device
        'n_shared_types': 3,  # Sharing 3 types of entities
        'in_ring': 1,  # Part of a fraud ring
        'account_degree': 15  # High degree in the network
    })

    print("Investigating sample transaction...")
    result = agent.investigate_transaction(sample_transaction)

    print("\n" + "="*60)
    print("INVESTIGATION RESULTS")
    print("="*60)
    print(agent.get_investigation_report(result))
