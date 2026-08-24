"""
Rule Analysis Tool for Investigation Agent
Provides rule-based explanations for suspicious transactions
"""
import pandas as pd
from typing import Dict, Any, Optional
from src.rule_engine.rule_engine import RuleEngine

class RuleAnalysisTool:
    """
    Tool for analyzing which fraud rules were triggered for a transaction.
    Provides detailed breakdown of rule violations to support investigations.
    """

    def __init__(self):
        """Initialize the Rule Analysis Tool"""
        self.rule_engine = RuleEngine(use_variance_threshold=False)

    def analyze_transaction(self,
                           transaction: pd.Series,
                           accounts: Optional[pd.DataFrame] = None,
                           edges: Optional[pd.DataFrame] = None) -> Dict[str, Any]:
        """
        Analyze which rules were triggered for a transaction.

        Args:
            transaction: Transaction data as a pandas Series
            accounts: Account profiles data (optional)
            edges: Network edges data (optional)

        Returns:
            Dictionary containing detailed rule analysis
        """
        # Convert transaction to DataFrame for compatibility with RuleEngine
        tx_df = transaction.to_frame().T if isinstance(transaction, pd.Series) else transaction

        # Get detailed rule breakdown
        try:
            details = self.rule_engine.get_rule_details(tx_df, accounts, edges)
            return {
                "transaction_id": transaction.get('transaction_id', 'unknown') if isinstance(transaction, pd.Series) else transaction.iloc[0].get('transaction_id', 'unknown'),
                "rule_analysis": details,
                "summary": self._generate_summary(details)
            }
        except Exception as e:
            return {
                "error": f"Error analyzing transaction rules: {str(e)}",
                "transaction_id": transaction.get('transaction_id', 'unknown') if isinstance(transaction, pd.Series) else transaction.iloc[0].get('transaction_id', 'unknown')
            }

    def _generate_summary(self, details: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a human-readable summary of rule analysis results.

        Args:
            details: Raw rule analysis details from RuleEngine

        Returns:
            Dictionary containing summary information
        """
        # Extract individual rule scores
        rule_scores = {
            'velocity': details.get('velocity_score', 0),
            'device': details.get('device_score', 0),
            'ip': details.get('ip_score', 0),
            'amount': details.get('amount_score', 0),
            'impossible_travel': details.get('impossible_travel_score', 0)
        }

        # Find the highest scoring rule(s)
        max_score = max(rule_scores.values())
        top_rules = [rule for rule, score in rule_scores.items() if score == max_score and max_score > 0]

        # This is rule-evidence severity, not the calibrated ML risk tier.
        final_score = details.get('final_rule_score', 0)
        if final_score >= 80:
            severity_level = "HIGH"
            severity_description = "Extreme rule violation"
        elif final_score >= 50:
            severity_level = "MEDIUM"
            severity_description = "Significant rule violation"
        elif final_score >= 30:
            severity_level = "LOW"
            severity_description = "Minor rule violation"
        else:
            severity_level = "VERY LOW"
            severity_description = "Few rule violation indicators"

        return {
            "final_rule_score": final_score,
            "rule_severity_level": severity_level,
            "rule_severity_description": severity_description,
            "top_triggered_rules": top_rules,
            "rule_scores": rule_scores,
            "needs_investigation": final_score >= 30
        }

    def explain_transaction(self,
                           transaction: pd.Series,
                           accounts: Optional[pd.DataFrame] = None,
                           edges: Optional[pd.DataFrame] = None) -> str:
        """
        Generate a human-readable explanation of why a transaction was flagged.

        Args:
            transaction: Transaction data
            accounts: Account profiles data (optional)
            edges: Network edges data (optional)

        Returns:
            String containing human-readable explanation
        """
        analysis = self.analyze_transaction(transaction, accounts, edges)

        if "error" in analysis:
            return f"Error analyzing transaction: {analysis['error']}"

        summary = analysis["summary"]
        details = analysis["rule_analysis"]

        explanation_parts = [
            f"RULE ANALYSIS FOR TRANSACTION {analysis.get('transaction_id', 'N/A')}:",
            f"Overall rule score: {summary['final_rule_score']:.1f}/100",
            f"Rule evidence severity: {summary['rule_severity_level']} ({summary['rule_severity_description']})",
            "",
            "Detailed scores by rule type:"
        ]

        for rule_name, score in summary['rule_scores'].items():
            explanation_parts.append(f"  - {rule_name.capitalize()}: {score:.1f}/100")

        explanation_parts.extend([
            "",
            "Rule(s) most strongly triggered:",
        ])

        if summary['top_triggered_rules']:
            for rule in summary['top_triggered_rules']:
                explanation_parts.append(f"  - {rule.capitalize()} (score: {summary['rule_scores'][rule]:.1f})")
        else:
            explanation_parts.append("  - No rules triggered significantly")

        explanation_parts.extend([
            "",
            "Recommendation:",
            f"  {'Immediate investigation required' if summary['needs_investigation'] else 'Periodic monitoring may be sufficient'}"
        ])

        return "\n".join(explanation_parts)
