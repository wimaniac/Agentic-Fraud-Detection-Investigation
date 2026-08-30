"""Phase 7 Streamlit human-review UI."""
from pathlib import Path

import pandas as pd
import streamlit as st

from src.human_review import FeedbackDecision, HumanFeedbackRepository
from src.investigation import InvestigationAgent


PROJECT_ROOT = Path(__file__).parent
DATA_DIR = PROJECT_ROOT / "data" / "processed" / "fraud_1m_processed"

st.set_page_config(page_title="SentinelAI human review", page_icon=":material/fact_check:", layout="wide")


@st.cache_data(ttl="15m", max_entries=1)
def load_transactions() -> pd.DataFrame:
    return pd.read_parquet(DATA_DIR / "transactions_clean.parquet")


@st.cache_resource
def get_repository() -> HumanFeedbackRepository:
    return HumanFeedbackRepository(PROJECT_ROOT / "data" / "feedback" / "human_feedback.sqlite")


@st.cache_resource
def get_agent() -> InvestigationAgent:
    return InvestigationAgent(data_dir=str(DATA_DIR))


st.session_state.setdefault("investigation_result", None)
st.session_state.setdefault("reviewed_transaction_id", None)

st.title("Human review")
st.caption("Phase 7 — reviewer quyết định; model chỉ cung cấp evidence và recommendation.")

repository = get_repository()
history = repository.list_feedback()
with st.container(horizontal=True):
    st.metric("Feedback records", len(history), border=True)
    st.metric("Confirmed fraud", int((history.get("decision") == FeedbackDecision.CONFIRM_FRAUD.value).sum()) if not history.empty else 0, border=True)
    st.metric("Need more information", int((history.get("decision") == FeedbackDecision.NEED_MORE_INFORMATION.value).sum()) if not history.empty else 0, border=True)

with st.sidebar:
    reviewer_id = st.text_input("Reviewer ID", key="reviewer_id", persist_state="session")
    transaction_id = st.text_input("Transaction ID", placeholder="Ví dụ: TX00000001", key="transaction_id")
    run_investigation = st.button("Run deterministic investigation", type="primary", icon=":material/manage_search:")

if run_investigation:
    transactions = load_transactions()
    matches = transactions[transactions["transaction_id"] == transaction_id.strip()]
    if matches.empty:
        st.error("Không tìm thấy transaction ID.")
    else:
        with st.spinner("Đang chạy risk scoring và 7 investigation tools..."):
            st.session_state.investigation_result = get_agent().investigate_transaction(matches.iloc[0])
            st.session_state.reviewed_transaction_id = transaction_id.strip()

result = st.session_state.investigation_result
if result is None:
    st.info("Nhập Transaction ID ở sidebar, sau đó chạy investigation để bắt đầu review.")
else:
    summary = result.get("investigation_summary", {})
    recommendation = summary.get("final_recommendation", {})
    with st.container(horizontal=True):
        st.metric("Risk score", f"{summary.get('composite_risk_score', 0):.1f}/100", border=True)
        st.metric("Risk tier", summary.get("risk_tier", "N/A"), border=True)
        st.metric("System action", recommendation.get("action_code", "N/A"), border=True)

    st.subheader("Investigation report")
    st.write(recommendation.get("reasoning", "No report available."))
    st.subheader("Model and graph evidence")
    model_evidence = summary.get("model_explanation") or {}
    if model_evidence.get("available"):
        st.caption(
            "TreeSHAP diễn giải ảnh hưởng lên raw margin của XGBoost nền; "
            "không thay đổi Risk Score, tier hoặc system action."
        )
        positive, negative = st.columns(2)
        with positive:
            st.markdown("**Factors increasing model risk**")
            st.dataframe(pd.DataFrame(model_evidence.get("top_positive_drivers", [])), hide_index=True)
        with negative:
            st.markdown("**Factors reducing model risk**")
            st.dataframe(pd.DataFrame(model_evidence.get("top_negative_drivers", [])), hide_index=True)
        with st.expander("Global feature importance"):
            st.dataframe(pd.DataFrame(model_evidence.get("global_feature_importance", [])), hide_index=True)
    else:
        st.info(f"Model explanation unavailable: {model_evidence.get('reason', 'not generated')}")

    graph_evidence = summary.get("graph_evidence") or {}
    with st.expander("Graph evidence (investigation only)"):
        st.caption("Graph evidence does not affect the model score or automatic policy.")
        st.json(graph_evidence)

    with st.expander("Structured evidence"):
        st.json({
            "rule_analysis": result.get("rule_analysis", {}),
            "graph_analysis": result.get("graph_analysis", {}),
            "user_history": result.get("user_history", {}),
            "device_history": result.get("device_history", {}),
            "ip_history": result.get("ip_history", {}),
            "similar_cases": result.get("similar_cases", {}),
        })

    st.subheader("Reviewer decision")
    with st.form("human_feedback"):
        decision = st.segmented_control(
            "Decision",
            options=[item.value for item in FeedbackDecision],
            format_func=lambda value: value.replace("_", " ").title(),
            selection_mode="single",
        )
        notes = st.text_area("Review notes", placeholder="Bắt buộc khi cần thêm thông tin.")
        submitted = st.form_submit_button("Save feedback", type="primary", icon=":material/save:")
    if submitted:
        try:
            record = repository.record_feedback(
                transaction_id=st.session_state.reviewed_transaction_id,
                reviewer_id=reviewer_id,
                decision=decision,
                notes=notes,
                investigation_snapshot=result,
            )
            st.success(f"Saved feedback {record['feedback_id']}")
            st.session_state.investigation_result = None
        except (TypeError, ValueError) as error:
            st.error(str(error))

st.subheader("Feedback dataset")
dataset = repository.export_feedback_dataset()
st.dataframe(dataset.drop(columns=["investigation_snapshot"], errors="ignore"), hide_index=True)
st.download_button(
    "Download feedback dataset",
    data=dataset.to_csv(index=False).encode("utf-8"),
    file_name="human_feedback_dataset.csv",
    mime="text/csv",
    icon=":material/download:",
)
