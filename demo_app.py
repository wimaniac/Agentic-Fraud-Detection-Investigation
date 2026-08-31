"""Public, synthetic-only Streamlit demo for SentinelAI.

This module intentionally does not load production data, model artifacts, API
keys, databases, or external LLMs. Scores and evidence are precomputed demo
scenarios for product exploration only.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st


DEMO_CASES: dict[str, dict[str, object]] = {
    "Fraud-like — account takeover": {
        "transaction_id": "DEMO-F-001",
        "label": "Synthetic fraud-like scenario",
        "risk_score": 92.4,
        "risk_tier": "HIGH",
        "action": "Hold and escalate",
        "summary": "A new device and high-risk IP attempted an unusually large overseas payment shortly after rapid account activity.",
        "signals": [
            ("Amount vs account baseline", "8.7× normal", "high"),
            ("Device familiarity", "New device", "high"),
            ("IP reputation", "High-risk network", "high"),
            ("Velocity", "7 transactions in one hour", "medium"),
        ],
    },
    "Fraud-like — coordinated account ring": {
        "transaction_id": "DEMO-F-002",
        "label": "Synthetic fraud-like scenario",
        "risk_score": 83.1,
        "risk_tier": "HIGH",
        "action": "Hold and investigate",
        "summary": "The transaction shares device and network relationships with a suspicious cluster and has unusual cross-border behaviour.",
        "signals": [
            ("Graph relationship", "Shared device/IP pattern", "high"),
            ("Cross-border behaviour", "Unusual for this account", "medium"),
            ("Transaction timing", "Outside normal pattern", "medium"),
            ("Authentication", "No second factor", "medium"),
        ],
    },
    "Legitimate-like — routine purchase": {
        "transaction_id": "DEMO-L-001",
        "label": "Synthetic legitimate-like scenario",
        "risk_score": 8.6,
        "risk_tier": "LOW",
        "action": "Allow",
        "summary": "A small purchase comes from a known device, familiar network, and the account's usual spending window.",
        "signals": [
            ("Amount vs account baseline", "0.8× normal", "low"),
            ("Device familiarity", "Known device", "low"),
            ("IP reputation", "Low-risk network", "low"),
            ("Velocity", "Normal", "low"),
        ],
    },
    "Review-needed — unusual but plausible": {
        "transaction_id": "DEMO-M-001",
        "label": "Synthetic ambiguous scenario",
        "risk_score": 54.7,
        "risk_tier": "MEDIUM",
        "action": "Request review",
        "summary": "The amount is higher than normal and the location is new, but the device is known and second-factor authentication succeeded.",
        "signals": [
            ("Amount vs account baseline", "3.1× normal", "medium"),
            ("Location", "New country", "medium"),
            ("Device familiarity", "Known device", "low"),
            ("Authentication", "Second factor completed", "low"),
        ],
    },
}

TIER_COLOUR = {"LOW": "green", "MEDIUM": "orange", "HIGH": "red"}


def initialise_state() -> None:
    """Set per-browser state used only during the current demo session."""
    st.session_state.setdefault("demo_feedback", None)


st.set_page_config(page_title="SentinelAI demo", page_icon=":material/shield:", layout="wide")
initialise_state()

st.title("SentinelAI fraud investigation demo")
st.caption("Explore synthetic examples of evidence-led fraud review. No real customer, transaction, or feedback data is shown or stored.")
st.warning(
    "Demo only: scores and evidence below are precomputed scenarios, not live fraud decisions. "
    "Do not use this page for financial decisions.",
    icon=":material/info:",
)

with st.sidebar:
    st.subheader("Choose a scenario")
    case_name = st.selectbox("Synthetic transaction", list(DEMO_CASES), key="demo_case")
    st.caption("The production application is intentionally kept separate from this public demo.")

case = DEMO_CASES[case_name]
score = float(case["risk_score"])
tier = str(case["risk_tier"])

metrics = st.columns(4)
metrics[0].metric("Demo transaction", case["transaction_id"], border=True)
metrics[1].metric("Risk score", f"{score:.1f}/100", border=True)
metrics[2].metric("Risk tier", tier, border=True)
metrics[3].metric("Suggested action", case["action"], border=True)

st.subheader("Scenario summary")
st.write(case["summary"])
st.caption(f":{TIER_COLOUR[tier]}[{case['label']}]")

st.subheader("Evidence to review")
evidence = pd.DataFrame(case["signals"], columns=["Signal", "Observation", "Illustrative impact"])
st.dataframe(evidence, hide_index=True)
st.caption("In the real system, evidence helps human review. It does not linearly alter the calibrated ML risk score.")

with st.container(border=True):
    st.subheader("Try the reviewer experience")
    st.write("What would you do with this scenario? Your answer stays only in this browser session and is not submitted anywhere.")
    with st.form("demo_reviewer_feedback"):
        decision = st.segmented_control(
            "Your decision",
            ["Allow", "Hold for review", "Block / investigate"],
            selection_mode="single",
        )
        note = st.text_area(
            "Why? (optional)",
            placeholder="For example: I would verify the device and merchant before releasing the transaction.",
        )
        submitted = st.form_submit_button("Save my demo response", type="primary", icon=":material/rate_review:")
    if submitted:
        st.session_state.demo_feedback = {"decision": decision, "note": note}

if st.session_state.demo_feedback:
    response = st.session_state.demo_feedback
    if response["decision"]:
        st.success(f"Demo response recorded locally for this session: {response['decision']}.")
    else:
        st.info("Choose a decision to complete the demo response.")

st.subheader("Suggested ways to explore")
exploration_prompts = st.pills(
    "Explore prompts",
    [
        "Compare the two fraud-like cases",
        "Find the evidence that lowers risk",
        "Decide what additional information you need",
    ],
    selection_mode="multi",
    label_visibility="collapsed",
)
if exploration_prompts:
    st.info("Try this next: " + " • ".join(exploration_prompts), icon=":material/lightbulb:")
st.markdown(
    "Questions or feedback about the demo? Use the repository's issue tracker. "
    "Please do not include personal, account, device, IP, or transaction data."
)
