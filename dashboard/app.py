from __future__ import annotations

import os
import sys
from pathlib import Path

import pandas as pd
import streamlit as st


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

st.set_page_config(page_title="MindLift Experiment Workflow", page_icon="📊", layout="wide")

TABLES_DIR = ROOT / "reports/tables"
DOCS_DIR = ROOT / "docs"
RAW_DIR = ROOT / "data/raw"


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


def _required_raw_files_exist() -> tuple[bool, list[str]]:
    required = [
        RAW_DIR / "dim_users.csv",
        RAW_DIR / "fact_events.csv",
        RAW_DIR / "fact_matches.csv",
        RAW_DIR / "fact_cancellations.csv",
        RAW_DIR / "fact_support_tickets.csv",
    ]
    missing = [str(p) for p in required if not p.exists()]
    return len(missing) == 0, missing


def _generate_raw_data_if_needed() -> None:
    raw_ok, _ = _required_raw_files_exist()
    if raw_ok:
        return

    from src.data_gen.generate_data import SimulationConfig, simulate_data

    n_users = int(os.getenv("STREAMLIT_AUTO_N_USERS", "75000"))
    seed = int(os.getenv("STREAMLIT_AUTO_SEED", "42"))
    cfg = SimulationConfig(n_users=n_users, seed=seed, output_dir=RAW_DIR)
    frames = simulate_data(cfg)
    cfg.output_dir.mkdir(parents=True, exist_ok=True)
    for table_name, df in frames.items():
        df.to_csv(cfg.output_dir / f"{table_name}.csv", index=False)


def _build_dashboard_artifacts() -> None:
    from src.analysis.build_dashboard_bundle import main as build_dashboard_bundle_main

    _generate_raw_data_if_needed()
    build_dashboard_bundle_main()
    _read_csv.clear()
    _read_text.clear()


ok, missing_files = _required_files_exist()

st.title("MindLift Experiment Workflow Project")
st.subheader("End-to-End Product Analytics + Experimentation")
st.markdown(
    """
I built this project as an end-to-end analytics workflow for a **subscription mental health app** called MindLift.
The full goal is to show how I go from raw event data to a final product decision.

The core project question is:
**Does a redesigned onboarding flow help new users reach activation, while keeping user experience guardrails healthy?**

**Important context:** every dataset here is **synthetic** (no real user or patient data).
I generated this data so the project can be public, reproducible from a fresh clone, and still realistic enough to
practice production-style analytics (seasonality, noisy events, duplicates, missing fields, and rollout noncompliance).

Why onboarding is the focus:
- It is the first high-impact moment in the user journey.
- Better onboarding can improve both activation and downstream retention.
- Poor onboarding changes can increase friction, so guardrails are required.
"""
)

if not ok:
    with st.spinner("Preparing dashboard artifacts for first load..."):
        try:
            _build_dashboard_artifacts()
            ok, missing_files = _required_files_exist()
        except Exception as exc:
            st.error("Dashboard artifacts are missing and automatic build failed.")
            st.markdown("Run the full build command locally and redeploy:")
            st.code("make final-deliverable", language="bash")
            st.exception(exc)
            st.stop()

if not ok:
    st.error("Dashboard artifacts are still missing after automatic build.")
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
readout = _read_text(ROOT / "reports/experiment_readout.md")
walkthrough = _read_text(ROOT / "reports/dashboard_walkthrough.md")

control = summary[summary["assigned_variant"] == "control"].iloc[0]
treatment = summary[summary["assigned_variant"] == "treatment"].iloc[0]
activation_lift_pp = 100 * (treatment["activation_rate_7d"] - control["activation_rate_7d"])

st.divider()
st.header("Glossary (Plain Language)")
glossary = pd.DataFrame(
    [
        {"term": "KPI", "meaning": "Key Performance Indicator: a metric used to judge whether the product goal improved."},
        {"term": "Control", "meaning": "Users who saw the original onboarding flow."},
        {"term": "Treatment", "meaning": "Users who saw the redesigned onboarding flow."},
        {"term": "Activation", "meaning": "A user completes onboarding and books first session within 7 days."},
        {"term": "Activation Lift", "meaning": "Treatment activation rate minus control activation rate (in percentage points)."},
        {"term": "Funnel", "meaning": "Step-by-step conversion path from signup to activation."},
        {"term": "Guardrail", "meaning": "Safety metric that should not worsen while chasing growth."},
    ]
)
st.dataframe(glossary, use_container_width=True)

st.divider()
st.header("Step 1: Experiment Design and Metric Definitions")
st.markdown(
    """
In this project, I simulate an A/B onboarding experiment:
- **Control** = old onboarding
- **Treatment** = redesigned onboarding

I evaluate success with a primary KPI and guardrails so the result is balanced, not growth-at-any-cost.
"""
)
st.subheader("Metric Definitions")
st.caption("Each metric below includes what it means, why it matters, and desired direction.")
st.dataframe(metric_dict, use_container_width=True)

st.divider()
st.header("Step 2: Workflow and Tools Used")
st.markdown(
    """
This table shows how I built the project end-to-end.
Each step connects technical work to a business purpose.
"""
)
workflow_display = workflow.rename(
    columns={
        "step_order": "Order",
        "step": "Workflow Step",
        "tools_used": "Tools Used",
        "description": "What I Did",
        "project_purpose": "Why This Step Matters",
    }
)
st.dataframe(workflow_display.sort_values("Order"), use_container_width=True)

st.divider()
st.header("Step 3: Headline Experiment Results")
st.markdown(
    """
These KPIs compare treatment vs control across the full user population.
The primary number to read first is **Activation Lift**.
"""
)

k1, k2, k3, k4 = st.columns(4)
k1.markdown("**Activation Lift**<sup>?</sup>", unsafe_allow_html=True)
k1.caption("Difference between treatment activation and control activation (percentage points).")
k1.metric(" ", f"{activation_lift_pp:.2f} pp")

k2.markdown("**Control Activation**<sup>?</sup>", unsafe_allow_html=True)
k2.caption("Activation rate for users who saw the original onboarding.")
k2.metric(" ", f"{100*control['activation_rate_7d']:.2f}%")

k3.markdown("**Treatment Activation**<sup>?</sup>", unsafe_allow_html=True)
k3.caption("Activation rate for users who saw the redesigned onboarding.")
k3.metric(" ", f"{100*treatment['activation_rate_7d']:.2f}%")

k4.markdown("**Total Users**<sup>?</sup>", unsafe_allow_html=True)
k4.caption("Total synthetic users included in the experiment dataset.")
k4.metric(" ", f"{int(summary['users'].sum()):,}")

st.subheader("Detailed KPI Table")
st.caption("Use this table to inspect primary, secondary, and guardrail metrics side-by-side.")
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
st.header("Step 4: Conversion Behavior (Funnel + Time Trend)")

st.subheader("Onboarding Funnel")
st.markdown(
    """
This chart shows how users progress from signup to activation.
If treatment remains higher across later steps, onboarding redesign likely improves conversion flow.
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

st.subheader("Activation Trend Over Time")
st.markdown(
    """
This trend shows whether treatment lift appears consistently across signup dates
instead of being caused by one short period.
"""
)
daily_plot = daily.copy()
daily_plot["signup_date"] = pd.to_datetime(daily_plot["signup_date"], errors="coerce")
daily_wide = daily_plot.pivot(index="signup_date", columns="assigned_variant", values="activation_rate_7d")
st.line_chart(daily_wide)

st.divider()
st.header("Step 5: Segment Diagnostics")
st.markdown(
    """
Segment analysis helps identify where treatment impact is strongest.
I use this to understand if the effect is broad or concentrated in specific user groups.
"""
)

dim = st.selectbox("Choose Segment Dimension", sorted(segments["segment_dimension"].unique().tolist()))
seg = segments[segments["segment_dimension"] == dim].copy()
seg_chart = seg.pivot(index="segment_value", columns="assigned_variant", values="activation_rate_7d")
st.bar_chart(seg_chart)

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
st.header("Step 6: Data Quality and Realism Validation")
st.markdown(
    """
Before trusting results, I validate that the synthetic data behaves like a realistic product event pipeline.
This includes duplicates, noncompliance, and plausible conversion levels.
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
st.header("Step 7: Final Decision and Action Plan")
st.markdown(
    """
This section converts analysis into a product decision.
I use primary-lift evidence + guardrail tolerances to determine the rollout path.
"""
)

row = recommendation.iloc[0]
st.subheader("Decision")
st.success(row["decision"])

st.markdown("**Reasoning**")
st.write(row["rationale"])

st.markdown("**Action Plan**")
st.write(row["action_plan"])

st.subheader("Decision Diagnostics")
st.markdown(
    """
Diagnostic metrics below explain why the recommendation was selected.
Each row is a simple, business-readable check against rollout safety.
"""
)
diag = pd.DataFrame(
    [
        {"Metric": "Activation lift (percentage points)", "Value": row["activation_lift_pp"]},
        {"Metric": "Cancellation delta (percentage points)", "Value": row["cancellation_delta_pp"]},
        {"Metric": "Match latency delta (hours)", "Value": row["match_latency_delta_hours"]},
        {"Metric": "Support ticket delta (tickets per user)", "Value": row["support_ticket_delta"]},
        {
            "Metric": "Cancellation guardrail within tolerance",
            "Value": bool(row["guardrail_cancellation_within_tolerance"]),
        },
        {
            "Metric": "Latency guardrail within tolerance",
            "Value": bool(row["guardrail_latency_within_tolerance"]),
        },
        {
            "Metric": "Support guardrail within tolerance",
            "Value": bool(row["guardrail_support_within_tolerance"]),
        },
    ]
)
st.dataframe(diag, use_container_width=True)

st.divider()
st.header("Step 8: Technical Appendix")
st.markdown(
    """
This appendix contains the full technical documentation used to build and validate the project.
"""
)

with st.expander("Simulation Specification", expanded=False):
    st.markdown(simulation_spec or "Missing docs/simulation_spec.md")

with st.expander("Experiment Readout", expanded=False):
    st.markdown(readout or "Missing reports/experiment_readout.md")

with st.expander("Dashboard Walkthrough Notes", expanded=False):
    st.markdown(walkthrough or "Missing reports/dashboard_walkthrough.md")

st.divider()
st.subheader("Run This Project")
st.code("make final-deliverable", language="bash")
