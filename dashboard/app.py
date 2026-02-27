from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st


st.set_page_config(page_title="MindLift Experiment Dashboard", layout="wide")

st.title("MindLift Experiment Dashboard")

REPORTS_TABLES_DIR = Path("reports/tables")
TABLEAU_DIR = Path("data/processed/tableau")
TABLEAU_USER_LEVEL_PATH = TABLEAU_DIR / "mindlift_tableau_user_level.csv"

METRICS = [
    "activated_within_7d",
    "retained_d7",
    "retained_d30",
    "cancelled_30d",
    "time_to_first_match_hours",
    "support_tickets_30d",
]


@st.cache_data(show_spinner=False)
def _load_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def _load_analysis_outputs() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    ab = _load_csv(REPORTS_TABLES_DIR / "ab_results_v1.csv")
    power = _load_csv(REPORTS_TABLES_DIR / "power_mde.csv")
    cuped = _load_csv(REPORTS_TABLES_DIR / "cuped_results.csv")
    segments = _load_csv(REPORTS_TABLES_DIR / "segment_analysis.csv")
    return ab, power, cuped, segments


def _compute_fallback_ab(user_level: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict] = []
    for metric in METRICS:
        control = user_level.loc[user_level["assigned_variant"] == "control", metric].dropna()
        treatment = user_level.loc[user_level["assigned_variant"] == "treatment", metric].dropna()
        if control.empty or treatment.empty:
            continue
        c = float(control.mean())
        t = float(treatment.mean())
        rows.append(
            {
                "metric": metric,
                "control_mean": c,
                "treatment_mean": t,
                "effect_abs": t - c,
                "effect_rel": (t - c) / c if c != 0 else np.nan,
                "ci_low": np.nan,
                "ci_high": np.nan,
                "p_value": np.nan,
                "p_value_fdr": np.nan,
                "significant_fdr_05": False,
            }
        )
    return pd.DataFrame(rows)


def _compute_fallback_segments(user_level: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict] = []
    for dim in ["acquisition_channel", "device", "age_bucket"]:
        g = (
            user_level.groupby([dim, "assigned_variant"], as_index=False)["activated_within_7d"]
            .mean()
            .rename(columns={dim: "segment_value", "activated_within_7d": "activation_rate_7d"})
        )
        g["segment_dimension"] = dim
        rows.append(g)

    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()


def _compute_funnel(user_level: pd.DataFrame) -> pd.DataFrame:
    steps = [
        ("signup", lambda d: np.ones(len(d), dtype=int)),
        ("onboarding_started", lambda d: d["onboarding_started"].to_numpy()),
        ("onboarding_completed", lambda d: d["onboarding_completed"].to_numpy()),
        ("session_booked", lambda d: d["session_booked"].to_numpy()),
        ("activated_within_7d", lambda d: d["activated_within_7d"].to_numpy()),
    ]

    out = []
    for variant, vdf in user_level.groupby("assigned_variant"):
        n = len(vdf)
        for name, fn in steps:
            vals = fn(vdf)
            users = int(np.sum(vals)) if name != "signup" else n
            out.append(
                {
                    "assigned_variant": variant,
                    "step": name,
                    "users": users,
                    "rate_from_signup": users / n if n else np.nan,
                }
            )
    return pd.DataFrame(out)


def _compute_daily_activation(user_level: pd.DataFrame) -> pd.DataFrame:
    df = user_level.copy()
    df["signup_date"] = pd.to_datetime(df["signup_date"])
    return (
        df.groupby(["signup_date", "assigned_variant"], as_index=False)["activated_within_7d"]
        .mean()
        .rename(columns={"activated_within_7d": "activation_rate_7d"})
    )


def _load_user_level() -> pd.DataFrame:
    if not TABLEAU_USER_LEVEL_PATH.exists():
        return pd.DataFrame()
    df = _load_csv(TABLEAU_USER_LEVEL_PATH)
    if df.empty:
        return df
    if "signup_date" in df.columns:
        df["signup_date"] = pd.to_datetime(df["signup_date"], errors="coerce")
    return df


ab, power, cuped, segments = _load_analysis_outputs()
user_level = _load_user_level()

if ab.empty and not user_level.empty:
    ab = _compute_fallback_ab(user_level)
    segments = _compute_fallback_segments(user_level)
    st.caption(
        "Data source: fallback mode from data/processed/tableau/mindlift_tableau_user_level.csv "
        "(no confidence intervals/p-values in this mode)."
    )
else:
    st.caption("Data source: reports/tables outputs from full analysis pipeline.")

if ab.empty:
    st.error(
        "No dashboard data found. Run one of these first:\n"
        "- make tableau-export  (fast, no Postgres needed)\n"
        "- make pipeline         (full warehouse+analysis path)"
    )
    st.stop()

primary = ab[ab["metric"] == "activated_within_7d"]
if primary.empty:
    st.error("Primary metric row missing in A/B results.")
    st.stop()
primary = primary.iloc[0]

k1, k2, k3, k4 = st.columns(4)
k1.metric("Activation Lift (abs)", f"{100 * primary['effect_abs']:.2f} pp")
k2.metric("Control Activation", f"{100 * primary['control_mean']:.2f}%")
k3.metric("Treatment Activation", f"{100 * primary['treatment_mean']:.2f}%")
if pd.notna(primary.get("p_value", np.nan)):
    k4.metric("Primary p-value", f"{primary['p_value']:.4f}")
else:
    k4.metric("Primary p-value", "N/A (fallback mode)")

if not power.empty:
    mde_col1, mde_col2 = st.columns(2)
    mde_col1.metric("Observed MDE", f"{100 * power.iloc[0]['observed_mde_abs']:.2f} pp")
    mde_col2.metric("n/group for +1pp", f"{int(power.iloc[0]['required_n_per_group_for_1pp_lift']):,}")

st.subheader("A/B Metric Summary")
summary_cols = [
    "metric",
    "control_mean",
    "treatment_mean",
    "effect_abs",
    "effect_rel",
    "ci_low",
    "ci_high",
    "p_value",
    "p_value_fdr",
    "significant_fdr_05",
]
avail_cols = [c for c in summary_cols if c in ab.columns]
st.dataframe(ab[avail_cols], use_container_width=True)

chart_df = ab.set_index("metric")[["effect_abs"]].sort_values("effect_abs")
st.subheader("Effect Size by Metric")
st.bar_chart(chart_df)

if not user_level.empty:
    st.subheader("Funnel by Variant")
    funnel = _compute_funnel(user_level)
    funnel_wide = funnel.pivot(index="step", columns="assigned_variant", values="rate_from_signup")
    st.bar_chart(funnel_wide)

    st.subheader("Daily Activation Trend")
    daily = _compute_daily_activation(user_level)
    daily_wide = daily.pivot(index="signup_date", columns="assigned_variant", values="activation_rate_7d")
    st.line_chart(daily_wide)

if not cuped.empty:
    st.subheader("CUPED Variance Reduction")
    st.dataframe(cuped[["metric", "variance_reduction_pct", "theta"]], use_container_width=True)
    st.bar_chart(cuped.set_index("metric")[["variance_reduction_pct"]])

if not segments.empty:
    st.subheader("Segment Analysis")
    if {"segment_dimension", "segment_value", "assigned_variant", "activation_rate_7d"}.issubset(segments.columns):
        dim = st.selectbox("Segment dimension", sorted(segments["segment_dimension"].unique().tolist()))
        seg_df = segments[segments["segment_dimension"] == dim].copy()
        seg_chart = seg_df.pivot(index="segment_value", columns="assigned_variant", values="activation_rate_7d")
        st.bar_chart(seg_chart)
        st.dataframe(seg_df, use_container_width=True)
    else:
        dim = st.selectbox("Segment dimension", sorted(segments["segment_dimension"].unique().tolist()))
        seg_df = segments[segments["segment_dimension"] == dim].copy()
        st.dataframe(seg_df, use_container_width=True)

st.subheader("Run Commands")
st.code(
    "\n".join(
        [
            "make tableau-export   # fast path, no Postgres",
            "make dashboard        # launch this app",
            "make pipeline         # full warehouse + analysis path",
        ]
    ),
    language="bash",
)
