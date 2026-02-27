from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st


st.set_page_config(page_title="MindLift Experiment Dashboard", layout="wide")

st.title("MindLift Experiment Dashboard")
st.caption("Auto-generated from analysis outputs in reports/tables")

TABLES_DIR = Path("reports/tables")


def _load_csv(name: str) -> pd.DataFrame:
    path = TABLES_DIR / name
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


ab = _load_csv("ab_results_v1.csv")
power = _load_csv("power_mde.csv")
cuped = _load_csv("cuped_results.csv")
segments = _load_csv("segment_analysis.csv")

if ab.empty:
    st.warning("No analysis tables found. Run: make analyze && make report")
    st.stop()

left, right = st.columns(2)
with left:
    primary = ab[ab["metric"] == "activated_within_7d"].iloc[0]
    st.metric("Activation Lift (abs)", f"{100*primary['effect_abs']:.2f} pp")
    st.metric("Primary p-value", f"{primary['p_value']:.4f}")

with right:
    if not power.empty:
        row = power.iloc[0]
        st.metric("Observed MDE", f"{100*row['observed_mde_abs']:.2f} pp")
        st.metric("n/group for +1pp", f"{int(row['required_n_per_group_for_1pp_lift']):,}")

st.subheader("A/B Metric Summary")
show_cols = [
    "metric",
    "control_mean",
    "treatment_mean",
    "effect_abs",
    "ci_low",
    "ci_high",
    "p_value",
    "p_value_fdr",
    "significant_fdr_05",
]
st.dataframe(ab[show_cols], use_container_width=True)

st.subheader("Effect Size by Metric")
chart_df = ab.set_index("metric")[["effect_abs"]]
st.bar_chart(chart_df)

if not cuped.empty:
    st.subheader("CUPED Variance Reduction")
    st.dataframe(cuped[["metric", "variance_reduction_pct", "theta"]], use_container_width=True)
    st.bar_chart(cuped.set_index("metric")[["variance_reduction_pct"]])

if not segments.empty:
    st.subheader("Pre-Registered Segment Analysis")
    dim = st.selectbox("Segment dimension", sorted(segments["segment_dimension"].unique().tolist()))
    seg_df = segments[segments["segment_dimension"] == dim].copy()
    st.dataframe(seg_df, use_container_width=True)

st.subheader("How to refresh")
st.code("make pipeline", language="bash")
