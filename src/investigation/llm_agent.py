"""DeepSeek report generation for completed fraud investigations.

All risk decisions and data tools are deterministic; DeepSeek only turns their
completed JSON evidence into a human-readable report for a reviewer.
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict

from dotenv import load_dotenv


class DeepSeekReportGenerator:
    """Generate an evidence-grounded report without access to investigation tools."""

    def __init__(self, model: str = "deepseek-v4-flash") -> None:
        try:
            from openai import OpenAI
        except ImportError as error:  # pragma: no cover - deployment dependency
            raise RuntimeError(
                "Install the 'openai' package (used as the DeepSeek-compatible API client) "
                "to enable DeepSeek report generation"
            ) from error

        load_dotenv()
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            raise RuntimeError("DEEPSEEK_API_KEY is required to enable DeepSeek report generation")
        self.model = model
        self.client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")

    @staticmethod
    def _evidence_payload(state: Any) -> Dict[str, Any]:
        """Expose completed facts only; never raw dataframes or callable tools."""
        return {
            "transaction_id": state.transaction_id,
            "risk_score": state.risk_scores,
            "rule_analysis": state.rule_analysis,
            "graph_analysis": state.graph_analysis,
            "user_history": state.user_history,
            "transaction_history": state.transaction_history,
            "device_history": state.device_history,
            "ip_history": state.ip_history,
            "similar_cases": state.similar_cases,
            "investigation_summary": state.investigation_summary,
            "deterministic_recommendation": {
                "action": state.recommended_action,
                "confidence_score": state.confidence_score,
            },
        }

    def generate_report(self, state: Any) -> str:
        """Return a Vietnamese report based exclusively on deterministic evidence."""
        evidence = json.dumps(self._evidence_payload(state), default=str, ensure_ascii=False)
        instructions = """Bạn là trợ lý viết báo cáo điều tra gian lận cho Human Reviewer.
Chỉ diễn đạt lại dữ kiện trong JSON được cung cấp; không suy đoán, không thêm số liệu,
không tính lại Risk Score và không thay đổi risk tier hoặc deterministic recommendation.
Nếu evidence thiếu hoặc có lỗi, nêu rõ là thiếu dữ liệu. Viết tiếng Việt, ngắn gọn,
với các mục: Executive Summary, Evidence nổi bật, Hạn chế dữ liệu, và Quyết định hệ thống.
Quyết định hệ thống phải giữ nguyên action và confidence từ JSON."""
        response = self.client.responses.create(
            model=self.model,
            instructions=instructions,
            input=evidence,
            max_output_tokens=1200,
        )
        report = response.output_text.strip()
        if not report:
            raise RuntimeError("DeepSeek returned an empty investigation report")
        return report
