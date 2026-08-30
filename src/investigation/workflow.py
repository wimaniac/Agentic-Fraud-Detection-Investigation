"""
Investigation Workflow for Investigation Agent
Orchestrates the investigation process using various tools
"""
import pandas as pd
import os
from typing import Dict, Any, Optional, List
from datetime import datetime
from dotenv import load_dotenv

# Try to import langgraph, fall back to simple implementation if not available
try:
    from langgraph.graph import StateGraph, END
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False
    print("Warning: LangGraph not available. Using simple workflow instead.")

from .tools.graph_query import GraphQueryTool
from .tools.rule_analysis import RuleAnalysisTool
from .tools.user_history import UserHistoryTool
from .tools.transaction_history import TransactionHistoryTool
from .tools.device_history import DeviceHistoryTool
from .tools.ip_history import IPHistoryTool
from .tools.similar_case import SimilarCaseTool


class InvestigationState:
    """
    Represents the state of an investigation as it progresses through the workflow.
    """
    def __init__(self):
        self.transaction_data: Optional[pd.Series] = None
        self.transaction_id: Optional[str] = None
        self.accounts_data: Optional[pd.DataFrame] = None
        self.edges_data: Optional[pd.DataFrame] = None

        # Results from various tools
        self.risk_scores: Dict[str, Any] = {}
        self.rule_analysis: Dict[str, Any] = {}
        self.graph_analysis: Dict[str, Any] = {}
        self.user_history: Dict[str, Any] = {}
        self.transaction_history: Dict[str, Any] = {}
        self.device_history: Dict[str, Any] = {}
        self.ip_history: Dict[str, Any] = {}
        self.similar_cases: Dict[str, Any] = {}

        # Final investigation results
        self.investigation_summary: Dict[str, Any] = {}
        self.recommended_action: str = ""
        self.confidence_score: float = 0.0
        self.investigation_timestamp: str = ""

        # Control flow
        self.current_step: str = "start"
        self.errors: List[str] = []


class InvestigationWorkflow:
    """
    Orchestrates the investigation process using various tools.
    """

    def __init__(self, data_dir: str = "data/processed/fraud_1m_processed", llm_model: Optional[str] = None):
        """
        Initialize the Investigation Workflow.

        Args:
            data_dir: Directory containing processed data
        """
        self.data_dir = data_dir
        self.report_generator = None
        load_dotenv()

        # Initialize all tools
        self.graph_tool = GraphQueryTool(data_dir)
        self.rule_tool = RuleAnalysisTool()
        self.user_tool = UserHistoryTool(data_dir)
        self.transaction_tool = TransactionHistoryTool(data_dir)
        self.device_tool = DeviceHistoryTool(data_dir)
        self.ip_tool = IPHistoryTool(data_dir)
        self.similar_tool = SimilarCaseTool(data_dir)

        # DeepSeek is optional at runtime so local/offline investigation remains
        # usable. Set DEEPSEEK_API_KEY (and optionally DEEPSEEK_MODEL) to enable it.
        # A key is a credential, not an instruction to make paid network calls.
        # Enable report generation explicitly with ``llm_model`` or
        # DEEPSEEK_MODEL=deepseek-v4-flash.
        selected_model = llm_model or os.getenv("DEEPSEEK_MODEL")
        if selected_model:
            from .llm_agent import DeepSeekReportGenerator
            self.report_generator = DeepSeekReportGenerator(selected_model)

        # Build workflow if langgraph is available
        if LANGGRAPH_AVAILABLE:
            self.workflow = self._build_langgraph_workflow()
        else:
            self.workflow = None
            print("Warning: LangGraph not available. Using simple workflow instead.")

    def _build_langgraph_workflow(self):
        """
        Build the LangGraph workflow for investigation.
        Returns a compiled StateGraph.
        """
        # Define the state schema
        workflow = StateGraph(InvestigationState)

        # Add nodes for each step in the investigation
        workflow.add_node("risk_assessment", self._risk_assessment_step)
        workflow.add_node("rule_analysis", self._rule_analysis_step)
        workflow.add_node("graph_analysis", self._graph_analysis_step)
        workflow.add_node("user_history", self._user_history_step)
        workflow.add_node("transaction_history", self._transaction_history_step)
        workflow.add_node("device_history", self._device_history_step)
        workflow.add_node("ip_history", self._ip_history_step)
        workflow.add_node("similar_cases", self._similar_cases_step)
        workflow.add_node("synthesis", self._synthesis_step)
        workflow.add_node("recommendation", self._recommendation_step)
        workflow.add_node("llm_report", self._llm_report_step)

        # Set entry point
        workflow.set_entry_point("risk_assessment")

        # Add edges - sequential flow for now
        workflow.add_edge("risk_assessment", "rule_analysis")
        workflow.add_edge("rule_analysis", "graph_analysis")
        workflow.add_edge("graph_analysis", "user_history")
        workflow.add_edge("user_history", "transaction_history")
        workflow.add_edge("transaction_history", "device_history")
        workflow.add_edge("device_history", "ip_history")
        workflow.add_edge("ip_history", "similar_cases")
        workflow.add_edge("similar_cases", "synthesis")
        workflow.add_edge("synthesis", "recommendation")
        workflow.add_edge("recommendation", "llm_report")
        workflow.add_edge("llm_report", END)

        # Compile the workflow
        return workflow.compile()

    def investigate(self,
                   transaction_data: pd.Series,
                   accounts_data: Optional[pd.DataFrame] = None,
                   edges_data: Optional[pd.DataFrame] = None) -> Dict[str, Any]:
        """
        Perform a complete investigation of a transaction.

        Args:
            transaction_data: Transaction data to investigate
            accounts_data: Account profiles data (optional)
            edges_data: Network edges data (optional)

        Returns:
            Dictionary containing complete investigation results
        """
        # Initialize state
        state = InvestigationState()
        state.transaction_data = transaction_data
        state.transaction_id = transaction_data.get('transaction_id', 'unknown')
        state.accounts_data = accounts_data
        state.edges_data = edges_data
        state.investigation_timestamp = datetime.now().isoformat()

        if LANGGRAPH_AVAILABLE and self.workflow:
            # Use LangGraph workflow
            try:
                result = self.workflow.invoke(state)
                # Convert result back to dictionary if needed
                if hasattr(result, 'dict'):
                    return result.dict()
                elif isinstance(result, InvestigationState):
                    return self._state_to_dict(result)
                else:
                    return dict(result)
            except Exception as e:
                print(f"Error in LangGraph workflow: {e}")
                # Fall back to sequential workflow
                return self._sequential_investigation(state)
        else:
            # Use sequential workflow
            return self._sequential_investigation(state)

    def _sequential_investigation(self, initial_state: InvestigationState) -> Dict[str, Any]:
        """
        Perform investigation using sequential steps (fallback when LangGraph not available).

        Args:
            initial_state: Initial investigation state

        Returns:
            Dictionary containing investigation results
        """
        state = initial_state

        try:
            # Execute each step sequentially
            state = self._risk_assessment_step(state)
            state = self._rule_analysis_step(state)
            state = self._graph_analysis_step(state)
            state = self._user_history_step(state)
            state = self._transaction_history_step(state)
            state = self._device_history_step(state)
            state = self._ip_history_step(state)
            state = self._similar_cases_step(state)
            state = self._synthesis_step(state)
            state = self._recommendation_step(state)
            state = self._llm_report_step(state)

            return self._state_to_dict(state)
        except Exception as e:
            state.errors.append(f"Error in investigation: {str(e)}")
            return self._state_to_dict(state)

    def _risk_assessment_step(self, state: InvestigationState) -> InvestigationState:
        """Step 1: Assess risk scores using the validated RiskScoreAggregator"""
        try:
            state.current_step = "risk_assessment"

            # Import here to avoid circular imports
            from src.features.feature_pipeline import extract_features, FEATURE_COLS
            from src.risk_engine.aggregator import RiskScoreAggregator
            from src.anomaly.isolation_forest_detector import IsolationForestAnomalyDetector
            import joblib
            from pathlib import Path

            # Prepare transaction data for feature extraction
            tx_df = (
                state.transaction_data.to_frame().T
                if isinstance(state.transaction_data, pd.Series)
                else state.transaction_data.copy()
            )
            # A mixed-type Series becomes an object DataFrame after transpose.
            # Restore the numeric raw columns before feature engineering.
            numeric_columns = [
                "amount", "velocity_1h", "amount_vs_avg_ratio", "time_since_last_s",
                "ip_risk_score", "hour_of_day", "day_of_week", "is_weekend",
                "is_foreign_txn", "card_present", "device_known", "has_2fa",
                "account_age_days", "credit_limit", "in_ring", "account_degree", "n_shared_types",
            ]
            for column in numeric_columns:
                if column in tx_df.columns:
                    tx_df[column] = pd.to_numeric(tx_df[column], errors="raise")

            # Load models and artifacts (in production these would be cached)
            model_dir = Path("models")
            if model_dir.exists():
                # Load pre-trained models for feature extraction and ML prediction
                try:
                    # Load the calibrated XGBoost model and scaler/artifacts
                    import joblib
                    from src.features.feature_pipeline import extract_features, FEATURE_COLS

                    # Load artifacts
                    cal_xgb = joblib.load(model_dir / "xgb_calibrated.pkl")
                    acc_stats_train = joblib.load(model_dir / "acc_stats_train.pkl")
                    train_median = joblib.load(model_dir / "train_median.pkl")

                    # Extract features using the pipeline (infer mode)
                    features_df, _, _ = extract_features(
                        tx_df,
                        edges=pd.read_parquet(model_dir / "_edges_ref.parquet") if (model_dir / "_edges_ref.parquet").exists() else None,
                        accounts=pd.read_parquet(model_dir / "_accounts_ref.parquet") if (model_dir / "_accounts_ref.parquet").exists() else None,
                        acc_stats_train=acc_stats_train,
                        train_median=train_median,
                        mode="infer"
                    )
                    X_features = features_df[FEATURE_COLS].apply(pd.to_numeric, errors="raise")

                    # Get ML probability from the calibrated model
                    probabilities = cal_xgb.predict_proba(X_features)
                    classes = list(cal_xgb.classes_)
                    if 1 not in classes:
                        raise ValueError("Calibrated model has no fraud class (label 1)")
                    ml_prob = probabilities[:, classes.index(1)]

                    # Phase 5 validated ML-only aggregation. Rule/anomaly
                    # results remain independent escalation signals/evidence.
                    risk_score = RiskScoreAggregator().calculate_risk_score(
                        ml_prob=ml_prob,
                        anomaly_score=0.0,
                        rule_score=0.0,
                    )
                    risk_score_value = float(risk_score[0])
                    # Explain the already-computed model input. TreeSHAP is
                    # evidence only: it neither recalculates the probability
                    # nor changes the ML-only risk score/policy path.
                    from src.explainability import ModelExplainer
                    model_explanation = ModelExplainer().explain(cal_xgb, X_features)

                    state.risk_scores = {
                        "ml_risk_score": risk_score_value if len(risk_score) == 1 else risk_score.tolist(),
                        "risk_tier": self._get_risk_tier(risk_score_value),
                        "model_explanation": model_explanation,
                        "components": {
                            # Try to get component contributions if available
                            # For now, we'll use placeholder values
                            "amount_contribution": 0.0,
                            "velocity_contribution": 0.0,
                            "ip_contribution": 0.0
                        }
                    }
                except Exception as model_error:
                    raise RuntimeError(
                        f"Unable to score transaction with the calibrated XGBoost model: {model_error}"
                    ) from model_error
            else:
                raise FileNotFoundError("Calibrated model artifacts directory 'models' was not found")

        except Exception as e:
            state.errors.append(f"Error in risk assessment step: {str(e)}")
            state.risk_scores = {"error": str(e)}

        return state

    def _rule_analysis_step(self, state: InvestigationState) -> InvestigationState:
        """Step 2: Analyze rule violations"""
        try:
            state.current_step = "rule_analysis"

            # Use the rule analysis tool
            rule_result = self.rule_tool.analyze_transaction(
                state.transaction_data,
                state.accounts_data,
                state.edges_data
            )
            state.rule_analysis = rule_result

        except Exception as e:
            state.errors.append(f"Error in rule analysis step: {str(e)}")
            state.rule_analysis = {"error": str(e)}

        return state

    def _graph_analysis_step(self, state: InvestigationState) -> InvestigationState:
        """Step 3: Analyze graph relationships"""
        try:
            state.current_step = "graph_analysis"

            # Extract account ID from transaction
            account_id = None
            if isinstance(state.transaction_data, pd.Series):
                account_id = state.transaction_data.get('account_id')
            else:
                account_id = state.transaction_data.iloc[0].get('account_id') if len(state.transaction_data) > 0 else None

            if account_id:
                # Get comprehensive graph analysis for the account
                graph_result = self.graph_tool.investigate_entity(account_id)
                state.graph_analysis = graph_result
            else:
                state.graph_analysis = {"warning": "No account ID found in transaction data"}

        except Exception as e:
            state.errors.append(f"Error in graph analysis step: {str(e)}")
            state.graph_analysis = {"error": str(e)}

        return state

    def _user_history_step(self, state: InvestigationState) -> InvestigationState:
        """Step 4: Analyze user historical behavior"""
        try:
            state.current_step = "user_history"

            # Extract account ID from transaction
            account_id = None
            if isinstance(state.transaction_data, pd.Series):
                account_id = state.transaction_data.get('account_id')
            else:
                account_id = state.transaction_data.iloc[0].get('account_id') if len(state.transaction_data) > 0 else None

            if account_id:
                # Get comprehensive user history
                user_result = self.user_tool.investigate_user(
                    account_id,
                    state.transaction_data
                )
                state.user_history = user_result
            else:
                state.user_history = {"warning": "No account ID found in transaction data"}

        except Exception as e:
            state.errors.append(f"Error in user history step: {str(e)}")
            state.user_history = {"error": str(e)}

        return state

    def _transaction_history_step(self, state: InvestigationState) -> InvestigationState:
        """Step 5: Analyze transaction history and patterns"""
        try:
            state.current_step = "transaction_history"

            # Get transaction ID
            tx_id = None
            if isinstance(state.transaction_data, pd.Series):
                tx_id = state.transaction_data.get('transaction_id')
            else:
                tx_id = state.transaction_data.iloc[0].get('transaction_id') if len(state.transaction_data) > 0 else None

            if tx_id:
                # Get comprehensive transaction history
                tx_result = self.transaction_tool.investigate_transaction(tx_id, include_similar=False)
                state.transaction_history = tx_result
            else:
                state.transaction_history = {"warning": "No transaction ID found"}

        except Exception as e:
            state.errors.append(f"Error in transaction history step: {str(e)}")
            state.transaction_history = {"error": str(e)}

        return state

    def _device_history_step(self, state: InvestigationState) -> InvestigationState:
        """Step 6: Analyze device history"""
        try:
            state.current_step = "device_history"

            # Extract account ID from transaction
            account_id = None
            if isinstance(state.transaction_data, pd.Series):
                account_id = state.transaction_data.get('account_id')
            else:
                account_id = state.transaction_data.iloc[0].get('account_id') if len(state.transaction_data) > 0 else None

            if account_id:
                # Get device history for the account
                reference_timestamp = state.transaction_data.get('timestamp')
                device_result = self.device_tool.get_device_sharing_patterns(
                    account_id, days_back=60, reference_timestamp=reference_timestamp
                )
                state.device_history = device_result
            else:
                state.device_history = {"warning": "No account ID found in transaction data"}

        except Exception as e:
            state.errors.append(f"Error in device history step: {str(e)}")
            state.device_history = {"error": str(e)}

        return state

    def _ip_history_step(self, state: InvestigationState) -> InvestigationState:
        """Step 7: Analyze IP history"""
        try:
            state.current_step = "ip_history"

            # Extract account ID from transaction
            account_id = None
            if isinstance(state.transaction_data, pd.Series):
                account_id = state.transaction_data.get('account_id')
            else:
                account_id = state.transaction_data.iloc[0].get('account_id') if len(state.transaction_data) > 0 else None

            if account_id:
                # Get IP history for the account
                reference_timestamp = state.transaction_data.get('timestamp')
                ip_result = self.ip_tool.get_ip_reputation_trends(
                    account_id, days_back=60, reference_timestamp=reference_timestamp
                )
                state.ip_history = ip_result
            else:
                state.ip_history = {"warning": "No account ID found in transaction data"}

        except Exception as e:
            state.errors.append(f"Error in IP history step: {str(e)}")
            state.ip_history = {"error": str(e)}

        return state

    def _similar_cases_step(self, state: InvestigationState) -> InvestigationState:
        """Step 8: Find similar historical cases"""
        try:
            state.current_step = "similar_cases"

            # Find similar cases
            similar_result = self.similar_tool.investigate_similar_cases(
                state.transaction_data,
                include_temporal_context=True
            )
            state.similar_cases = similar_result

        except Exception as e:
            state.errors.append(f"Error in similar cases step: {str(e)}")
            state.similar_cases = {"error": str(e)}

        return state

    def _synthesis_step(self, state: InvestigationState) -> InvestigationState:
        """Step 9: Synthesize all findings using validated components"""
        try:
            state.current_step = "synthesis"
            llm_metadata = {
                key: state.investigation_summary[key]
                for key in ("llm_narrative", "llm_model", "llm_provider")
                if key in state.investigation_summary
            }

            # Extract key information from each step
            # Use the ML risk score from risk assessment (now properly calculated)
            risk_score = state.risk_scores.get("ml_risk_score")
            if risk_score is None:
                raise RuntimeError("No calibrated ML risk score is available for synthesis")

            rule_score = state.rule_analysis.get("summary", {}).get("final_rule_score", 0)
            similar_cases_fraud_rate = state.similar_cases.get("statistics", {}).get("fraud_rate_among_similar", 0)

            user_anomalies = state.user_history.get("behavioral_analysis", {}).get("anomalies_detected", False)
            user_anomaly_count = state.user_history.get("behavioral_analysis", {}).get("anomaly_count", 0)

            # Preserve the validated ML score. Investigation findings are
            # evidence and independent escalation flags, not score adjustments.
            composite_score = float(risk_score)
            escalation_flags = {
                "extreme_rule_violation": rule_score >= 80,
            }
            # These are investigation evidence only. Some graph relationships
            # are derived from known historical fraud labels, so they must not
            # become an automated serving decision or an ML input.
            investigation_evidence = {
                "behavioral_anomaly": bool(user_anomalies),
                "similar_fraud_cases": similar_cases_fraud_rate >= 0.7,
                "fraud_ring": bool(state.graph_analysis.get("fraud_ring", {}).get("in_fraud_ring", False)),
            }
            from src.explainability import GraphEvidenceExtractor
            graph_evidence = GraphEvidenceExtractor().extract(state.graph_analysis)

            state.investigation_summary = {
                "composite_risk_score": composite_score,
                "component_scores": {
                    "ml_risk_score": composite_score,
                },
                "risk_tier": self._get_risk_tier(composite_score),
                "escalation_flags": escalation_flags,
                "investigation_evidence": investigation_evidence,
                "model_explanation": state.risk_scores.get("model_explanation"),
                "graph_evidence": graph_evidence,
                "key_findings": {
                    "high_risk_factors": self._identify_high_risk_factors(state),
                    "risk_mitigating_factors": self._identify_risk_mitigating_factors(state),
                    "anomalies_detected": user_anomalies,
                    "similar_case_fraud_rate": similar_cases_fraud_rate
                }
            }
            state.investigation_summary.update(llm_metadata)

        except Exception as e:
            state.errors.append(f"Error in synthesis step: {str(e)}")
            state.investigation_summary = {"error": str(e)}

        return state

    def _recommendation_step(self, state: InvestigationState) -> InvestigationState:
        """Step 10: Generate final recommendation"""
        try:
            state.current_step = "recommendation"

            composite_score = state.investigation_summary.get("composite_risk_score", 50)
            risk_tier = state.investigation_summary.get("risk_tier", "MEDIUM RISK")

            # Determine recommended action based on risk tier
            escalation_flags = state.investigation_summary.get("escalation_flags", {})
            if composite_score >= 70 or any(escalation_flags.values()):
                recommended_action = "HIGH RISK ALERT - BLOCK TRANSACTION AND INITIATE INVESTIGATION"
                action_code = "BLOCK_AND_INVESTIGATE"
                confidence = min(0.9, 0.6 + max(composite_score - 70, 0) * 0.01)
            elif composite_score >= 30:
                recommended_action = "MEDIUM RISK ALERT - REQUEST ADDITIONAL VERIFICATION (2FA/OTP)"
                action_code = "STEP_UP_AUTH"
                confidence = min(0.8, 0.5 + (composite_score - 30) * 0.01)
            else:
                recommended_action = "LOW RISK - Allow transaction"
                action_code = "APPROVE"
                confidence = min(0.6, 0.3 + (composite_score * 0.005))  # 0.3-0.6 confidence

            # Adjust confidence based on data quality
            error_penalty = len(state.errors) * 0.05  # 5% penalty per error
            confidence = max(0.1, confidence - error_penalty)

            state.recommended_action = recommended_action
            state.action_code = action_code
            state.confidence_score = confidence

            # Add final summary
            state.investigation_summary["final_recommendation"] = {
                "action": recommended_action,
                "action_code": action_code,
                "confidence_score": confidence,
                "reasoning": self._generate_reasoning(state)
            }

        except Exception as e:
            state.errors.append(f"Error in recommendation step: {str(e)}")
            state.recommended_action = "ERROR - REQUIRES MANUAL REVIEW"
            state.confidence_score = 0.1

        return state

    def _llm_report_step(self, state: InvestigationState) -> InvestigationState:
        """Use DeepSeek only to phrase a completed deterministic investigation."""
        if self.report_generator is None:
            return state
        try:
            report = self.report_generator.generate_report(state)
            state.investigation_summary["llm_narrative"] = report
            state.investigation_summary["llm_model"] = self.report_generator.model
            state.investigation_summary["llm_provider"] = "deepseek"
            state.investigation_summary["final_recommendation"]["reasoning"] = report
        except Exception as error:
            state.errors.append(f"DeepSeek report generation failed: {error}")
        return state

    def _get_risk_tier(self, score: float) -> str:
        """Convert numerical score to risk tier - STANDARDIZED to match aggregator.py"""
        if score >= 70:
            return "HIGH RISK"
        elif score >= 30:
            return "MEDIUM RISK"
        else:
            return "LOW RISK"

    def _identify_high_risk_factors(self, state: InvestigationState) -> List[str]:
        """Identify high-risk factors from the investigation"""
        factors = []

        # Check rule analysis
        rule_summary = state.rule_analysis.get("summary", {})
        if rule_summary.get("final_rule_score", 0) >= 70:
            factors.append(f"High rule score: {rule_summary['final_rule_score']:.1f}/100")

        # Check similar cases
        similar_stats = state.similar_cases.get("statistics", {})
        if similar_stats.get("fraud_rate_among_similar", 0) >= 0.5:
            factors.append(f"High fraud rate in similar cases: {similar_stats['fraud_rate_among_similar']*100:.1f}%")

        # Check user anomalies
        user_anomalies = state.user_history.get("behavioral_analysis", {}).get("anomalies", [])
        if len(user_anomalies) >= 2:
            factors.append(f"Detected {len(user_anomalies)} unusual behaviors")

        # Check graph analysis
        graph_fraud_ring = state.graph_analysis.get("fraud_ring", {})
        if graph_fraud_ring.get("in_fraud_ring", False):
            factors.append("Account belongs to known fraud ring")

        # Check device sharing
        device_sharing = state.device_history.get("device_sharing_statistics", {})
        if device_sharing.get("high_sharing_ratio", 0) >= 0.5:
            factors.append(f"High device sharing ratio: {device_sharing['high_sharing_ratio']*100:.1f}%")

        # Check IP reputation
        ip_stats = state.ip_history.get("ip_reputation_statistics", {})
        if ip_stats.get("high_risk_ratio", 0) >= 0.4:
            factors.append(f"High-risk IP usage ratio: {ip_stats['high_risk_ratio']*100:.1f}%")

        return factors

    def _identify_risk_mitigating_factors(self, state: InvestigationState) -> List[str]:
        """Identify risk-mitigating factors from the investigation"""
        factors = []

        # Check for low scores in various areas
        risk_score = state.risk_scores.get("ml_risk_score", 50)
        if risk_score < 30:
            factors.append(f"Low ML model score: {risk_score:.1f}/100")

        rule_score = state.rule_analysis.get("summary", {}).get("final_rule_score", 0)
        if rule_score < 30:
            factors.append(f"Low rule score: {rule_score:.1f}/100")

        similar_fraud_rate = state.similar_cases.get("statistics", {}).get("fraud_rate_among_similar", 0)
        if similar_fraud_rate < 0.1:
            factors.append(f"Low fraud rate in similar cases: {similar_fraud_rate*100:.1f}%")

        return factors

    def _generate_reasoning(self, state: InvestigationState) -> str:
        """Generate human-readable reasoning for the recommendation"""
        reasoning_parts = [
            f"ANALYSIS OF INVESTIGATION PROGRESS FOR TRANSACTION {state.transaction_id}:",
            "",
            "RISK SCORE SUMMARY:",
            f"  - Composite risk score: {state.investigation_summary.get('composite_risk_score', 0):.1f}/100",
            f"  - Risk level: {state.investigation_summary.get('risk_tier', 'LOW RISK')}",
            ""
        ]

        # Add component scores
        components = state.investigation_summary.get("component_scores", {})
        if components:
            reasoning_parts.append("SCORES BY COMPONENT:")
            for component, score in components.items():
                reasoning_parts.append(f"  - {component.replace('_', ' ').title()}: {score:.1f}/100")
            reasoning_parts.append("")

        # Add key findings
        key_findings = state.investigation_summary.get("key_findings", {})
        if key_findings.get("high_risk_factors"):
            reasoning_parts.append("HIGH RISK FACTORS DETECTED:")
            for factor in key_findings["high_risk_factors"][:5]:  # Limit to top 5
                reasoning_parts.append(f"  - {factor}")
            reasoning_parts.append("")

        if key_findings.get("anomalies_detected"):
            reasoning_parts.append(f"DETECTED {key_findings.get('user_anomaly_count', 0)} UNUSUAL BEHAVIORS")
            reasoning_parts.append("")

        # Add similar cases info
        similar_stats = state.similar_cases.get("statistics", {})
        if similar_stats.get("total_similar_cases", 0) > 0:
            reasoning_parts.append(
                f"SIMILAR CASES: {similar_stats['total_similar_cases']} cases found, "
                f"of which {similar_stats.get('fraud_cases', 0)} are fraudulent "
                f"(rate: {similar_stats.get('fraud_rate_among_similar', 0)*100:.1f}%)"
            )
            reasoning_parts.append("")

        reasoning_parts.extend([
            "FINAL RECOMMENDATION:",
            f"  {state.recommended_action}",
            f"  Confidence level: {state.confidence_score:.1%}",
            "",
            f"Investigation completed at: {state.investigation_timestamp}"
        ])

        if state.errors:
            reasoning_parts.extend([
                "",
                "WARNING - ERRORS DETECTED DURING INVESTIGATION:",
                *[f"  - {error}" for error in state.errors]
            ])

        return "\n".join(reasoning_parts)

    def _state_to_dict(self, state: InvestigationState) -> Dict[str, Any]:
        """Convert InvestigationState to dictionary"""
        return {
            "transaction_id": state.transaction_id,
            "investigation_timestamp": state.investigation_timestamp,
            "risk_scores": state.risk_scores,
            "rule_analysis": state.rule_analysis,
            "graph_analysis": state.graph_analysis,
            "user_history": state.user_history,
            "transaction_history": state.transaction_history,
            "device_history": state.device_history,
            "ip_history": state.ip_history,
            "similar_cases": state.similar_cases,
            "investigation_summary": state.investigation_summary,
            "recommended_action": state.recommended_action,
            "action_code": getattr(state, 'action_code', ''),
            "confidence_score": state.confidence_score,
            "errors": state.errors,
            "current_step": state.current_step
        }
