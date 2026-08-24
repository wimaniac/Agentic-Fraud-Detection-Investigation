"""
Demo script for the Investigation Agent
Shows how to use the investigation tools to analyze a suspicious transaction
"""
import sys
from pathlib import Path

# Add the project root to the Python path so we can import src modules
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import pandas as pd
from src.investigation import investigate_transaction, InvestigationAgent

def demo_investigation():
    """Demonstrate the investigation agent with a sample transaction"""
    print("SentinelAI Investigation Agent Demo")
    print("=" * 50)

    # Create a sample high-risk transaction
    sample_transaction = pd.Series({
        'transaction_id': 'TX_DEMO_HIGH_RISK_001',
        'amount': 10000000,  # 10,000,000 VND (high amount)
        'velocity_1h': 15.0,  # Very high velocity
        'is_fraud': False,  # Unknown - this is what we're investigating
        'timestamp': pd.Timestamp.now(),
        'account_id': 'ACC_SUSPICIOUS_001',
        'is_foreign_txn': 1,  # Foreign transaction
        'ip_risk_score': 90,  # Very high risk IP
        'amount_vs_avg_ratio': 15.0,  # 15x average amount (extremely high)
        'time_since_last_s': 300,  # Only 5 minutes since last transaction
        'device_known': 0,  # Unknown device
        'n_shared_types': 4,  # Sharing multiple entities
        'in_ring': 1,  # Part of known fraud ring
        'account_degree': 25  # Very high network connectivity
    })

    print(f"Investigating transaction: {sample_transaction['transaction_id']}")
    print(f"Amount: {sample_transaction['amount']:,.0f} VND")
    print(f"Velocity: {sample_transaction['velocity_1h']} transactions/hour")
    print(f"Foreign transaction: {'Yes' if sample_transaction['is_foreign_txn'] else 'No'}")
    print(f"IP risk score: {sample_transaction['ip_risk_score']}/100")
    print(f"Amount vs average ratio: {sample_transaction['amount_vs_avg_ratio']:.1f}x")
    print(f"Time since last transaction: {sample_transaction['time_since_last_s']} seconds")
    print(f"Known device: {'Yes' if sample_transaction['device_known'] else 'No'}")
    print(f"Shared entity types: {sample_transaction['n_shared_types']}")
    print(f"Part of fraud ring: {'Yes' if sample_transaction['in_ring'] else 'No'}")
    print(f"Account degree in network: {sample_transaction['account_degree']}")
    print()

    # Conduct the investigation
    print("Performing detailed investigation...")
    investigation_result = investigate_transaction(sample_transaction)

    # Display the results
    agent = InvestigationAgent()
    report = agent.get_investigation_report(investigation_result)
    print(report)

    # Also show some key metrics from the investigation
    print("\n" + "=" * 50)
    print("DETAILED INVESTIGATION METRICS")
    print("=" * 50)

    if 'investigation_summary' in investigation_result:
        summary = investigation_result['investigation_summary']
        print(f"Composite risk score: {summary.get('composite_risk_score', 0):.1f}/100")
        print(f"Risk level: {summary.get('risk_tier', 'N/A')}")

        if 'component_scores' in summary:
            print("\nScores by component:")
            for component, score in summary['component_scores'].items():
                print(f"  {component.replace('_', ' ').title()}: {score:.1f}/100")

    print(f"\nRecommended action: {investigation_result.get('recommended_action', 'N/A')}")
    print(f"Confidence level: {investigation_result.get('confidence_score', 0):.1%}")

    # Show investigation steps completed
    print(f"\nInvestigation steps completed: {investigation_result.get('current_step', 'N/A')}")
    if investigation_result.get('errors'):
        print(f"Errors encountered: {len(investigation_result['errors'])}")
        for error in investigation_result['errors']:
            print(f"  - {error}")

def demo_quick_investigation():
    """Demonstrate the quick investigation function"""
    print("\n" + "=" * 50)
    print("QUICK INVESTIGATION DEMO")
    print("=" * 50)

    agent = InvestigationAgent()

    # Quick investigation with minimal data
    quick_result = agent.quick_investigation(
        transaction_id='TX_QUICK_001',
        amount=2000000,  # 2,000,000 VND
        velocity_1h=3.0,  # 3 transactions per hour
        is_fraud=False
    )

    print(f"Transaction: {quick_result.get('transaction_id', 'N/A')}")
    print(f"Action: {quick_result.get('recommended_action', 'N/A')}")
    print(f"Confidence: {quick_result.get('confidence_score', 0):.1%}")

if __name__ == "__main__":
    demo_investigation()
    demo_quick_investigation()
    print("\nDemo completed!")