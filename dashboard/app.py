from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st


st.set_page_config(page_title="MindLift Final Deliverable", page_icon="📊", layout="wide")

ROOT = Path(".")
TABLES_DIR = ROOT / "reports/tables"
FIGURES_DIR = ROOT / "reports/figures"
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
        ROOT / "reports/experiment_readout.md",
    ]
    missing = [str(p) for p in required if not p.exists()]
    return len(missing) == 0, missing


ok, missing_files = _required_files_exist()

st.title("MindLift Experimentation Platform: Final Deliverable")
st.caption("End-to-end product experimentation project walkthrough (Streamlit-only mode).")

if not ok:
    st.error("Dashboard artifacts are missing.")
    st.code("make final-deliverable", language="bash")
    st.write("Missing files:")
    for item in missing_files:
        st.write(f"- {item}")
    st.stop()

summary = _read_csv(TABLES_DIR / "dashboard_variant_summary.csv")
funnel = _read_csv(TABLES_DIR / "dashboard_funnel.csv")
daily = _read_csv(TABLES_DIR / "dashboard_daily_activation.csv")
segments = _read_csv(TABLES_DIR / "dashboard_segment_activation.csv")
quality = _read_csv(TABLES_DIR / "dashboard_data_quality.csv")

simulation_spec = _read_text(DOCS_DIR / "simulation_spec.md")
prereg = _read_text(DOCS_DIR / "preregistration.md")
resume_bullets = _read_text(DOCS_DIR / "resume_bullets.md")
readout = _read_text(ROOT / "reports/experiment_readout.md")
walkthrough = _read_text(ROOT / "reports/dashboard_walkthrough.md")

control = summary[summary["assigned_variant"] == "control"].iloc[0]
treatment = summary[summary["assigned_variant"] == "treatment"].iloc[0]
activation_lift_pp = 100 * (treatment["activation_rate_7d"] - control["activation_rate_7d"])

k1, k2, k3, k4 = st.columns(4)
k1.metric("Activation Lift", f"{activation_lift_pp:.2f} pp")
k2.metric("Control Activation", f"{100*control['activation_rate_7d']:.2f}%")
k3.metric("Treatment Activation", f"{100*treatment['activation_rate_7d']:.2f}%")
k4.metric("Users", f"{int(summary['users'].sum()):,}")

tab_overview, tab_results, tab_segments, tab_quality, tab_docs = st.tabs(
    [
        "Project Overview",
        "Experiment Results",
        "Segments",
        "Data Quality",
        "Documentation",
    ]
)

with tab_overview:
    st.subheader("Project Walkthrough")
    st.markdown(walkthrough or "Walkthrough file not found.")

    st.subheader("Variant Summary")
    st.dataframe(summary, use_container_width=True)

    fig_path = FIGURES_DIR / "dashboard_variant_summary.png"
    if fig_path.exists():
        st.image(str(fig_path), caption="Key rates by variant")

with tab_results:
    st.subheader("Funnel")
    funnel_wide = funnel.pivot(index="step", columns="assigned_variant", values="rate_from_signup")
    st.bar_chart(funnel_wide)

    fig_path = FIGURES_DIR / "dashboard_funnel.png"
    if fig_path.exists():
        st.image(str(fig_path), caption="Onboarding funnel by variant")

    st.subheader("Daily Activation Trend")
    daily_plot = daily.copy()
    daily_plot["signup_date"] = pd.to_datetime(daily_plot["signup_date"], errors="coerce")
    daily_wide = daily_plot.pivot(index="signup_date", columns="assigned_variant", values="activation_rate_7d")
    st.line_chart(daily_wide)

    fig_path = FIGURES_DIR / "dashboard_daily_activation.png"
    if fig_path.exists():
        st.image(str(fig_path), caption="Daily activation trend")

    st.subheader("Readout")
    st.markdown(readout or "Readout file not found.")

with tab_segments:
    st.subheader("Segment Analysis")
    dim = st.selectbox("Segment Dimension", sorted(segments["segment_dimension"].unique().tolist()))
    seg = segments[segments["segment_dimension"] == dim].copy()
    seg_chart = seg.pivot(index="segment_value", columns="assigned_variant", values="activation_rate_7d")
    st.bar_chart(seg_chart)
    st.dataframe(seg, use_container_width=True)

with tab_quality:
    st.subheader("Data Quality Checks")
    st.dataframe(quality, use_container_width=True)

with tab_docs:
    st.subheader("Simulation Spec")
    st.markdown(simulation_spec or "Missing docs/simulation_spec.md")

    st.subheader("Pre-Registration")
    st.markdown(prereg or "Missing docs/preregistration.md")

    st.subheader("Resume Bullets")
    st.markdown(resume_bullets or "Missing docs/resume_bullets.md")

st.divider()
st.subheader("One-Command Rebuild")
st.code("make final-deliverable", language="bash")
