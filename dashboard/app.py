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

st.title("MindLift Experimentation Platform")
st.subheader("Final Deliverable Dashboard")
st.markdown(
    """
This dashboard is a complete walkthrough of the project from data generation to experiment decision.

Use it as an internal-style readout for stakeholders who need to understand:
- what the experiment was,
- how metrics were defined,
- what results were observed,
- and what action is recommended.
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
st.header("1) Experiment Context")
st.markdown(
    """
**Business question:** Does redesigned onboarding improve activation for new users?

**Experiment design:** 50/50 A/B assignment at signup.
- `control`: old onboarding
- `treatment`: redesigned onboarding

**Primary metric:** `activated_within_7d`

**Guardrails:** cancellation rate, match latency, support tickets.
"""
)

st.subheader("Metric Dictionary")
st.caption("Each metric used below includes its formal definition and desired direction.")
st.dataframe(metric_dict, use_container_width=True)

st.divider()
st.header("2) End-to-End Workflow")
st.markdown("This is the exact workflow implemented in the project pipeline.")
st.dataframe(workflow.sort_values("step_order"), use_container_width=True)

st.divider()
st.header("3) Topline Results")
st.markdown(
    """
These KPIs compare treatment against control at the user level.
The most important value is **Activation Lift** (treatment minus control).
"""
)

k1, k2, k3, k4 = st.columns(4)
k1.metric("Activation Lift", f"{activation_lift_pp:.2f} pp")
k2.metric("Control Activation", f"{100*control['activation_rate_7d']:.2f}%")
k3.metric("Treatment Activation", f"{100*treatment['activation_rate_7d']:.2f}%")
k4.metric("Total Users", f"{int(summary['users'].sum()):,}")

st.subheader("Variant Summary Table")
st.caption("Interpretation: compare each row to determine treatment impact on primary, secondary, and guardrail metrics.")
st.dataframe(summary, use_container_width=True)

st.divider()
st.header("4) Funnel and Retention Dynamics")

st.subheader("Onboarding Funnel")
st.markdown(
    """
This chart shows progression from signup through activation.
A wider gap in later funnel steps indicates treatment impact in onboarding completion and booking.
"""
)
funnel_wide = funnel.pivot(index="step", columns="assigned_variant", values="rate_from_signup")
st.bar_chart(funnel_wide)

st.subheader("Daily Activation Trend")
st.markdown(
    """
This time-series checks whether treatment effect is stable over signup cohorts and not driven by a single day.
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
Segment views help identify where the treatment performs best.
Use this to guide targeted rollout messaging or UX prioritization.
"""
)

dim = st.selectbox("Segment Dimension", sorted(segments["segment_dimension"].unique().tolist()))
seg = segments[segments["segment_dimension"] == dim].copy()
seg_chart = seg.pivot(index="segment_value", columns="assigned_variant", values="activation_rate_7d")
st.bar_chart(seg_chart)
st.caption("Segment table with user counts and activation rates by variant.")
st.dataframe(seg, use_container_width=True)

st.divider()
st.header("6) Data Quality and Realism Checks")
st.markdown(
    """
These checks validate that the synthetic dataset behaves like a realistic event pipeline
(duplicates, noncompliance, plausible activation range).
"""
)
st.dataframe(quality, use_container_width=True)

st.divider()
st.header("7) Final Recommendation and Action")
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
        {"metric": "Activation lift (pp)", "value": row["activation_lift_pp"]},
        {"metric": "Cancellation delta (pp)", "value": row["cancellation_delta_pp"]},
        {"metric": "Match latency delta (hours)", "value": row["match_latency_delta_hours"]},
        {"metric": "Support ticket delta", "value": row["support_ticket_delta"]},
    ]
)
st.dataframe(diag, use_container_width=True)

st.divider()
st.header("8) Documentation Appendix")

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
