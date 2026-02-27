from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st


st.set_page_config(page_title="MindLift Final Deliverable", page_icon="📊", layout="wide")

ROOT = Path(".")
TABLES_DIR = ROOT / "reports/tables"
DOCS_DIR = ROOT / "docs"


@st.cache_data(show_spinner=False)
def _read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


@st.cache_data(show_spinner=False)
def _read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def _required_files_exist() -> tuple[bool, list[str]]:
    required = [
        TABLES_DIR / "dashboard_variant_summary.csv",
        TABLES_DIR / "dashboard_funnel.csv",
        TABLES_DIR / "dashboard_daily_activation.csv",
        TABLES_DIR / "dashboard_segment_activation.csv",
        TABLES_DIR / "dashboard_data_quality.csv",
        TABLES_DIR / "dashboard_metric_dictionary.csv",
        TABLES_DIR / "dashboard_workflow_steps.csv",
        TABLES_DIR / "dashboard_final_recommendation.csv",
        ROOT / "reports/experiment_readout.md",
        ROOT / "reports/dashboard_walkthrough.md",
    ]
    missing = [str(p) for p in required if not p.exists()]
    return len(missing) == 0, missing


ok, missing_files = _required_files_exist()

st.title("MindLift Onboarding Experiment")
st.subheader("Client-Facing Results Dashboard")
st.markdown(
    """
This dashboard explains the full experiment in plain language, from question to recommendation.

Use this page to quickly understand:
- what we tested,
- how success was measured,
- what the results say,
- and what action to take next.
"""
)

if not ok:
    st.error("Dashboard artifacts are missing.")
    st.markdown("Run the full build command:")
    st.code("make final-deliverable", language="bash")
    st.markdown("Missing files:")
    for item in missing_files:
        st.write(f"- {item}")
    st.stop()

summary = _read_csv(TABLES_DIR / "dashboard_variant_summary.csv")
funnel = _read_csv(TABLES_DIR / "dashboard_funnel.csv")
daily = _read_csv(TABLES_DIR / "dashboard_daily_activation.csv")
segments = _read_csv(TABLES_DIR / "dashboard_segment_activation.csv")
quality = _read_csv(TABLES_DIR / "dashboard_data_quality.csv")
metric_dict = _read_csv(TABLES_DIR / "dashboard_metric_dictionary.csv")
workflow = _read_csv(TABLES_DIR / "dashboard_workflow_steps.csv")
recommendation = _read_csv(TABLES_DIR / "dashboard_final_recommendation.csv")

simulation_spec = _read_text(DOCS_DIR / "simulation_spec.md")
prereg = _read_text(DOCS_DIR / "preregistration.md")
readout = _read_text(ROOT / "reports/experiment_readout.md")
walkthrough = _read_text(ROOT / "reports/dashboard_walkthrough.md")

control = summary[summary["assigned_variant"] == "control"].iloc[0]
treatment = summary[summary["assigned_variant"] == "treatment"].iloc[0]
activation_lift_pp = 100 * (treatment["activation_rate_7d"] - control["activation_rate_7d"])

st.divider()
st.header("1) What Was Tested")
st.markdown(
    """
**Business question:** Does the redesigned onboarding flow improve early activation for new users?

**Experiment design:** 50/50 A/B assignment at signup.
- `control`: old onboarding
- `treatment`: redesigned onboarding

**Primary success metric:** 7-Day Activation Rate

**Safety guardrails:** cancellation rate, match latency, and support ticket volume.
"""
)

st.subheader("Metric Dictionary")
st.caption("Each metric includes what it means, why it matters, and which direction is better.")
st.dataframe(metric_dict, use_container_width=True)

st.divider()
st.header("2) How The Analysis Was Built")
st.markdown("This is the end-to-end workflow used to go from event logs to a decision.")
st.dataframe(workflow.sort_values("step_order"), use_container_width=True)

st.divider()
st.header("3) Headline Results")
st.markdown(
    """
These headline KPIs compare treatment against control at the user level.
The key number is **Activation Lift**: treatment activation minus control activation.
"""
)

k1, k2, k3, k4 = st.columns(4)
k1.metric("Activation Lift", f"{activation_lift_pp:.2f} pp")
k2.metric("Control Activation", f"{100*control['activation_rate_7d']:.2f}%")
k3.metric("Treatment Activation", f"{100*treatment['activation_rate_7d']:.2f}%")
k4.metric("Total Users", f"{int(summary['users'].sum()):,}")

st.subheader("Variant Summary Table")
st.caption("Interpretation: compare treatment vs control across growth metrics and guardrails.")
summary_display = summary.rename(
    columns={
        "assigned_variant": "Variant",
        "users": "Users",
        "activation_rate_7d": "Activation Rate (7D)",
        "retention_rate_d7": "Retention Rate (D7)",
        "retention_rate_d30": "Retention Rate (D30)",
        "cancellation_rate_30d": "Cancellation Rate (30D)",
        "avg_match_latency_hours": "Avg Match Latency (hrs)",
        "support_tickets_per_user": "Support Tickets per User (30D)",
        "noncompliance_rate": "Noncompliance Rate",
    }
)
st.dataframe(summary_display, use_container_width=True)

st.divider()
st.header("4) Behavior Through The Funnel")

st.subheader("Onboarding Funnel")
st.markdown(
    """
This chart tracks user drop-off from signup to activation.
If treatment bars stay higher in later steps, the redesign is improving completion and booking behavior.
"""
)
funnel_wide = funnel.pivot(index="step", columns="assigned_variant", values="rate_from_signup")
funnel_wide = funnel_wide.rename(
    index={
        "signup": "Signup",
        "onboarding_started": "Onboarding Started",
        "onboarding_completed": "Onboarding Completed",
        "session_booked": "Session Booked",
        "activated_within_7d": "Activated Within 7 Days",
    }
)
st.bar_chart(funnel_wide)

st.subheader("Daily Activation Trend")
st.markdown(
    """
This trend checks whether the lift is stable over time instead of being driven by a narrow date window.
"""
)
daily_plot = daily.copy()
daily_plot["signup_date"] = pd.to_datetime(daily_plot["signup_date"], errors="coerce")
daily_wide = daily_plot.pivot(index="signup_date", columns="assigned_variant", values="activation_rate_7d")
st.line_chart(daily_wide)

st.divider()
st.header("5) Segment Analysis")
st.markdown(
    """
This section shows where the treatment performs best across user segments.
Use this to guide rollout prioritization and messaging strategy.
"""
)

dim = st.selectbox("Segment Dimension", sorted(segments["segment_dimension"].unique().tolist()))
seg = segments[segments["segment_dimension"] == dim].copy()
seg_chart = seg.pivot(index="segment_value", columns="assigned_variant", values="activation_rate_7d")
st.bar_chart(seg_chart)
st.caption("Segment table with user counts and activation rates by variant.")
seg_display = seg.rename(
    columns={
        "segment_dimension": "Segment Type",
        "segment_value": "Segment Value",
        "assigned_variant": "Variant",
        "users": "Users",
        "activation_rate_7d": "Activation Rate (7D)",
    }
)
st.dataframe(seg_display, use_container_width=True)

st.divider()
st.header("6) Data Quality Checks")
st.markdown(
    """
These checks confirm the simulation behaves like a realistic event pipeline
(for example duplicates and imperfect treatment exposure).
"""
)
quality_display = quality.copy()
quality_display["check"] = quality_display["check"].map(
    {
        "users": "Total simulated users",
        "events_raw": "Total raw events",
        "duplicate_event_rate": "Duplicate event rate",
        "noncompliance_rate": "Noncompliance rate",
        "activation_rate_7d": "Overall activation rate (7D)",
    }
).fillna(quality_display["check"])
quality_display = quality_display.rename(columns={"check": "Check", "value": "Value"})
st.dataframe(quality_display, use_container_width=True)

st.divider()
st.header("7) Recommendation and Next Action")
row = recommendation.iloc[0]

st.subheader("Decision")
st.success(row["decision"])

st.markdown("**Why this decision?**")
st.write(row["rationale"])

st.markdown("**Recommended action plan**")
st.write(row["action_plan"])

st.markdown("**Decision diagnostics**")
diag = pd.DataFrame(
    [
        {"Metric": "Activation lift (percentage points)", "Value": row["activation_lift_pp"]},
        {"Metric": "Cancellation delta (percentage points)", "Value": row["cancellation_delta_pp"]},
        {"Metric": "Match latency delta (hours)", "Value": row["match_latency_delta_hours"]},
        {"Metric": "Support ticket delta (tickets per user)", "Value": row["support_ticket_delta"]},
    ]
)
st.dataframe(diag, use_container_width=True)

st.divider()
st.header("8) Methodology Appendix")
st.markdown(
    """
The sections below contain full technical documentation for auditability and reproducibility.
The main dashboard above is intentionally business-first; this appendix provides implementation detail.
"""
)

with st.expander("Simulation Specification", expanded=False):
    st.markdown(simulation_spec or "Missing docs/simulation_spec.md")

with st.expander("Pre-Registration Plan", expanded=False):
    st.markdown(prereg or "Missing docs/preregistration.md")

with st.expander("Experiment Readout", expanded=False):
    st.markdown(readout or "Missing reports/experiment_readout.md")

with st.expander("Dashboard Walkthrough Notes", expanded=False):
    st.markdown(walkthrough or "Missing reports/dashboard_walkthrough.md")

st.divider()
st.subheader("One-Command Rebuild")
st.code("make final-deliverable", language="bash")
