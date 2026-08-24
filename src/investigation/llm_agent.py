"""DeepSeek tool-calling orchestration for a fraud investigation.

The model may select investigation tools and write a report, but it never
calculates a risk score, changes a tier, or decides the transaction policy.
"""
from __future__ import annotations

import json
from typing import Any, Callable, Dict, List


class DeepSeekInvestigationAgent:
    """Run bounded, auditable DeepSeek function-calling over investigation tools."""

    MAX_TOOL_CALLS = 8

    def __init__(self, workflow: Any, model: str = "deepseek-v4-flash") -> None:
        try:
            from openai import OpenAI
        except ImportError as error:  # pragma: no cover - deployment dependency
            raise RuntimeError(
                "Install the 'openai' package (used as the DeepSeek-compatible API client) "
                "to enable the DeepSeek investigation agent"
            ) from error

        import os
        self.workflow = workflow
        self.model = model
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            raise RuntimeError("DEEPSEEK_API_KEY is required to enable the DeepSeek investigation agent")
        self.client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")

    @staticmethod
    def _tool_definition(name: str, description: str) -> Dict[str, Any]:
        return {
            "type": "function",
            "name": name,
            "description": description,
            "strict": True,
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
                "additionalProperties": False,
            },
        }

    def _tool_registry(self, state: Any) -> Dict[str, Callable[[], Dict[str, Any]]]:
        def account_id() -> Any:
            return state.transaction_data.get("account_id")

        def transaction_id() -> Any:
            return state.transaction_id

        def reference_timestamp() -> Any:
            return state.transaction_data.get("timestamp")

        def rule_analysis() -> Dict[str, Any]:
            state.rule_analysis = self.workflow.rule_tool.analyze_transaction(
                state.transaction_data, state.accounts_data, state.edges_data
            )
            return state.rule_analysis

        def graph_analysis() -> Dict[str, Any]:
            state.graph_analysis = self.workflow.graph_tool.investigate_entity(account_id())
            return state.graph_analysis

        def user_history() -> Dict[str, Any]:
            state.user_history = self.workflow.user_tool.investigate_user(account_id(), state.transaction_data)
            return state.user_history

        def transaction_history() -> Dict[str, Any]:
            state.transaction_history = self.workflow.transaction_tool.investigate_transaction(
                transaction_id(), include_similar=False
            )
            return state.transaction_history

        def device_history() -> Dict[str, Any]:
            state.device_history = self.workflow.device_tool.get_device_sharing_patterns(
                account_id(), days_back=60, reference_timestamp=reference_timestamp()
            )
            return state.device_history

        def ip_history() -> Dict[str, Any]:
            state.ip_history = self.workflow.ip_tool.get_ip_reputation_trends(
                account_id(), days_back=60, reference_timestamp=reference_timestamp()
            )
            return state.ip_history

        def similar_cases() -> Dict[str, Any]:
            state.similar_cases = self.workflow.similar_tool.investigate_similar_cases(state.transaction_data)
            return state.similar_cases

        return {
            "analyze_rules": rule_analysis,
            "query_graph_evidence": graph_analysis,
            "get_user_history": user_history,
            "get_transaction_history": transaction_history,
            "get_device_history": device_history,
            "get_ip_history": ip_history,
            "find_similar_cases": similar_cases,
        }

    def investigate(self, state: Any) -> Any:
        """Let DeepSeek select tools, then save an evidence-grounded narrative."""
        registry = self._tool_registry(state)
        tools = [
            self._tool_definition(name, description)
            for name, description in {
                "analyze_rules": "Retrieve deterministic rule-engine findings.",
                "query_graph_evidence": "Retrieve graph relationships and fraud-ring evidence for human review.",
                "get_user_history": "Retrieve the account's historical behaviour as of this transaction.",
                "get_transaction_history": "Retrieve transaction-level historical patterns.",
                "get_device_history": "Retrieve shared-device evidence as of this transaction.",
                "get_ip_history": "Retrieve IP-reputation evidence as of this transaction.",
                "find_similar_cases": "Retrieve historical similar cases and their known outcomes.",
            }.items()
        ]
        risk = state.risk_scores
        instructions = """You are a fraud-investigation assistant. The calibrated ML risk score and
policy are produced by deterministic code and are authoritative. Use tools only to gather
evidence. Do not invent facts, calculate a new score, change a tier, or recommend automatic
approval/blocking. Graph fraud labels are investigation evidence only, never a model input.
Call only the tools needed; after tools finish, write a concise Vietnamese analyst narrative
that cites only returned evidence and clearly identifies missing data."""
        initial_input = (
            f"Investigate transaction {state.transaction_id}. Calibrated ML score: "
            f"{risk.get('ml_risk_score')} / 100; tier: {risk.get('risk_tier')}. "
            "Decide which evidence tools to call, then provide the analyst narrative."
        )
        conversation: List[Any] = [{"role": "user", "content": initial_input}]
        response = self.client.responses.create(
            model=self.model,
            instructions=instructions,
            input=conversation,
            tools=tools,
            parallel_tool_calls=False,
        )
        calls_made = 0
        while calls_made < self.MAX_TOOL_CALLS:
            calls = [item for item in response.output if item.type == "function_call"]
            if not calls:
                break
            outputs: List[Dict[str, str]] = []
            for call in calls:
                calls_made += 1
                try:
                    result = registry[call.name]()
                except Exception as error:
                    result = {"error": f"Tool {call.name} failed: {error}"}
                outputs.append({
                    "type": "function_call_output",
                    "call_id": call.call_id,
                    "output": json.dumps(result, default=str),
                })
            # The DeepSeek Responses API is stateless, so replay its function
            # calls and our tool outputs rather than using previous_response_id.
            conversation.extend(response.output)
            conversation.extend(outputs)
            response = self.client.responses.create(
                model=self.model,
                instructions=instructions,
                input=conversation,
                tools=tools,
                parallel_tool_calls=False,
            )

        if calls_made >= self.MAX_TOOL_CALLS:
            state.errors.append("DeepSeek investigation reached the maximum permitted tool calls")
        state.investigation_summary["llm_narrative"] = response.output_text
        state.investigation_summary["llm_model"] = self.model
        state.investigation_summary["llm_provider"] = "deepseek"
        state.investigation_summary["llm_tool_calls"] = calls_made
        return state
