"""Streamlit Visualization Dashboard for mama health Patient Journey Analytics."""

import os
import pickle

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DAGSTER_STORAGE = os.environ.get("DAGSTER_STORAGE_PATH", "dagster_storage")

ASSET_NAMES = [
    "patient_journey_analytics_summary",
    "symptom_cooccurrence_mapping",
    "emotional_state_events",
    "emotional_journey_phases",
    "symptom_to_diagnosis_timeline",
    "treatment_phase_duration",
]

SANKEY_NODES = [
    "Symptom Onset",
    "Diagnosis",
    "Treatment Initiated",
    "Treatment Changed",
    "Treatment Stopped",
    "Ongoing Management",
]

# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------


def list_partitions(asset_name: str) -> list[str]:
    """Return sorted YYYY-MM-DD partition keys available on disk for *asset_name*."""
    path = os.path.join(DAGSTER_STORAGE, asset_name)
    if not os.path.isdir(path):
        return []
    return sorted(
        [f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))]
    )


@st.cache_data(ttl=60)
def load_asset(asset_name: str, partition: str):
    """Load a pickle file written by FilesystemIOManager."""
    path = os.path.join(DAGSTER_STORAGE, asset_name, partition)
    if not os.path.exists(path):
        return None
    with open(path, "rb") as f:
        return pickle.load(f)


def available_partitions() -> list[str]:
    """Union of all partitions found across the primary assets."""
    seen: set[str] = set()
    for asset in ASSET_NAMES:
        seen.update(list_partitions(asset))
    return sorted(seen)


# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="mama health — Patient Journey Analytics",
    page_icon="🏥",
    layout="wide",
)

st.title("🏥 mama health — Patient Journey Analytics")

# ---------------------------------------------------------------------------
# Sidebar — partition selector
# ---------------------------------------------------------------------------

with st.sidebar:
    st.header("Data Selection")

    partitions = available_partitions()

    if not partitions:
        st.warning(
            "No partitions found in `dagster_storage/`. "
            "Run the Dagster pipeline first, then refresh."
        )
        selected_partition = None
    else:
        selected_partition = st.selectbox(
            "Partition (date)",
            options=partitions,
            index=len(partitions) - 1,  # default to latest
        )

    if st.button("🔄 Refresh data"):
        st.cache_data.clear()
        st.rerun()

    st.divider()
    st.caption(f"Storage path: `{DAGSTER_STORAGE}`")
    if selected_partition:
        st.caption(f"Selected partition: `{selected_partition}`")

# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------

tab_overview, tab_cooccurrence, tab_sentiment, tab_pathway = st.tabs(
    ["📊 Overview", "🧬 Symptom Co-occurrence", "💬 Sentiment Timeline", "🗺️ Patient Pathway"]
)

# ---------------------------------------------------------------------------
# Tab 1 — Overview
# ---------------------------------------------------------------------------

with tab_overview:
    st.header("Pipeline Overview")

    if not selected_partition:
        st.info("Run the Dagster pipeline to populate data, then select a partition in the sidebar.")
        st.stop()

    summary = load_asset("patient_journey_analytics_summary", selected_partition)

    if summary is None:
        st.info(
            f"No data for partition **{selected_partition}**. "
            "Materialise this partition in the Dagster UI and refresh."
        )
    else:
        # KPI cards
        col1, col2, col3, col4 = st.columns(4)

        total_events = summary.get("total_events", 0)
        unique_symptoms = summary.get("unique_symptoms", 0)
        unique_medications = summary.get("unique_medications", 0)
        avg_confidence = summary.get("avg_confidence", 0.0)

        col1.metric("Total Events", f"{total_events:,}")
        col2.metric("Unique Symptoms", f"{unique_symptoms:,}")
        col3.metric("Unique Medications", f"{unique_medications:,}")
        col4.metric("Avg Confidence", f"{avg_confidence:.2f}")

        # Key findings
        st.subheader("Key Findings")
        key_findings = summary.get("key_findings", summary)
        st.json(key_findings)

# ---------------------------------------------------------------------------
# Tab 2 — Symptom Co-occurrence Heatmap
# ---------------------------------------------------------------------------

with tab_cooccurrence:
    st.header("Symptom Co-occurrence Heatmap")

    if not selected_partition:
        st.info("Select a partition in the sidebar.")
        st.stop()

    cooccurrence = load_asset("symptom_cooccurrence_mapping", selected_partition)

    if cooccurrence is None:
        st.info(
            f"No co-occurrence data for partition **{selected_partition}**. "
            "Run the analytics pipeline and refresh."
        )
    else:
        # cooccurrence_pairs = {(symptom_a, symptom_b): count, ...}
        pairs: dict = {}
        if isinstance(cooccurrence, dict):
            pairs = cooccurrence.get("cooccurrence_pairs", cooccurrence)

        if not pairs:
            st.info("Co-occurrence data is empty for this partition.")
        else:
            # Take top-20 pairs by count
            sorted_pairs = sorted(pairs.items(), key=lambda x: x[1], reverse=True)[:20]

            # Build symmetric set of symptom labels (truncated)
            symptoms: set[str] = set()
            for (a, b), _ in sorted_pairs:
                symptoms.add(str(a)[:30])
                symptoms.add(str(b)[:30])
            symptom_list = sorted(symptoms)

            # Build matrix
            matrix = pd.DataFrame(0, index=symptom_list, columns=symptom_list)
            for (a, b), count in sorted_pairs:
                a_trunc = str(a)[:30]
                b_trunc = str(b)[:30]
                if a_trunc in matrix.index and b_trunc in matrix.columns:
                    matrix.loc[a_trunc, b_trunc] = count
                    matrix.loc[b_trunc, a_trunc] = count

            fig = px.imshow(
                matrix,
                zmin=0,
                color_continuous_scale="Blues",
                title=f"Symptom Co-occurrence — {selected_partition}",
                labels={"color": "Co-occurrences"},
                aspect="auto",
            )
            fig.update_layout(height=600)
            st.plotly_chart(fig, use_container_width=True)

            with st.expander("Raw co-occurrence pairs"):
                rows = [
                    {"Symptom A": str(a)[:50], "Symptom B": str(b)[:50], "Count": count}
                    for (a, b), count in sorted_pairs
                ]
                st.dataframe(pd.DataFrame(rows), use_container_width=True)

# ---------------------------------------------------------------------------
# Tab 3 — Sentiment Timeline
# ---------------------------------------------------------------------------

with tab_sentiment:
    st.header("Sentiment Timeline")

    if not selected_partition:
        st.info("Select a partition in the sidebar.")
        st.stop()

    events = load_asset("emotional_state_events", selected_partition)
    phases = load_asset("emotional_journey_phases", selected_partition)

    no_events = events is None or (isinstance(events, list) and len(events) == 0)
    no_phases = phases is None

    if no_events and no_phases:
        st.info(
            f"No sentiment data for partition **{selected_partition}**. "
            "Run the analytics pipeline and refresh."
        )
    else:
        # --- Scatter: confidence over time by sentiment ---
        if not no_events:
            st.subheader("Emotional Events Over Time")
            rows = []
            for ev in events:
                if isinstance(ev, dict):
                    rows.append(
                        {
                            "posted_at": ev.get("posted_at") or ev.get("timestamp_posted"),
                            "sentiment": ev.get("sentiment", "neutral"),
                            "confidence": float(ev.get("confidence", 0.5)),
                            "mentioned_entity": ev.get("mentioned_entity", ""),
                        }
                    )
            if rows:
                df_events = pd.DataFrame(rows)
                df_events["posted_at"] = pd.to_datetime(
                    df_events["posted_at"], errors="coerce"
                )
                df_events = df_events.dropna(subset=["posted_at"])

                if not df_events.empty:
                    fig_scatter = px.scatter(
                        df_events,
                        x="posted_at",
                        y="confidence",
                        color="sentiment",
                        hover_data=["mentioned_entity"],
                        color_discrete_map={
                            "positive": "#2ecc71",
                            "neutral": "#3498db",
                            "negative": "#e74c3c",
                        },
                        title="Sentiment Confidence by Event Time",
                        labels={
                            "posted_at": "Date Posted",
                            "confidence": "Extraction Confidence",
                            "sentiment": "Sentiment",
                        },
                    )
                    st.plotly_chart(fig_scatter, use_container_width=True)
                else:
                    st.info("Events present but timestamps could not be parsed.")
            else:
                st.info("Event list is empty or has unexpected format.")

        # --- Bar: phase distribution ---
        if not no_phases:
            st.subheader("Emotional Journey Phase Distribution")
            phase_dist: dict = {}
            if isinstance(phases, dict):
                phase_dist = phases.get("phase_distribution", {})

            if phase_dist:
                df_phases = pd.DataFrame(
                    list(phase_dist.items()), columns=["Phase", "Count"]
                ).sort_values("Count", ascending=False)

                fig_bar = px.bar(
                    df_phases,
                    x="Phase",
                    y="Count",
                    color="Phase",
                    title="Events per Journey Phase",
                    labels={"Count": "Event Count"},
                )
                fig_bar.update_layout(showlegend=False)
                st.plotly_chart(fig_bar, use_container_width=True)
            else:
                st.info("No phase distribution data available.")

# ---------------------------------------------------------------------------
# Tab 4 — Patient Pathway Sankey
# ---------------------------------------------------------------------------

with tab_pathway:
    st.header("Patient Pathway")

    if not selected_partition:
        st.info("Select a partition in the sidebar.")
        st.stop()

    timeline = load_asset("symptom_to_diagnosis_timeline", selected_partition)
    treatment = load_asset("treatment_phase_duration", selected_partition)

    no_timeline = timeline is None or (isinstance(timeline, list) and len(timeline) == 0)
    no_treatment = treatment is None or (isinstance(treatment, list) and len(treatment) == 0)

    if no_timeline and no_treatment:
        st.info(
            f"No pathway data for partition **{selected_partition}**. "
            "Run the analytics pipeline and refresh."
        )
    else:
        node_index = {name: i for i, name in enumerate(SANKEY_NODES)}

        # Build links
        link_source: list[int] = []
        link_target: list[int] = []
        link_value: list[int] = []

        # Symptom Onset → Diagnosis
        if not no_timeline:
            count = len(timeline) if isinstance(timeline, list) else 1
            if count > 0:
                link_source.append(node_index["Symptom Onset"])
                link_target.append(node_index["Diagnosis"])
                link_value.append(count)

        # Diagnosis → Treatment Initiated
        if not no_treatment:
            count = len(treatment) if isinstance(treatment, list) else 1
            if count > 0:
                link_source.append(node_index["Diagnosis"])
                link_target.append(node_index["Treatment Initiated"])
                link_value.append(count)

            # Treatment Initiated → terminal nodes (from next_event field)
            next_event_counts: dict[str, int] = {}
            if isinstance(treatment, list):
                for entry in treatment:
                    if isinstance(entry, dict):
                        ne = entry.get("next_event", "").lower()
                        if "stop" in ne or "discontinu" in ne:
                            key = "Treatment Stopped"
                        elif "chang" in ne or "switch" in ne:
                            key = "Treatment Changed"
                        else:
                            key = "Ongoing Management"
                        next_event_counts[key] = next_event_counts.get(key, 0) + 1

            if not next_event_counts:
                # Fallback: all treatments lead to Ongoing Management
                total = len(treatment) if isinstance(treatment, list) else 1
                next_event_counts["Ongoing Management"] = total

            for terminal, cnt in next_event_counts.items():
                if terminal in node_index and cnt > 0:
                    link_source.append(node_index["Treatment Initiated"])
                    link_target.append(node_index[terminal])
                    link_value.append(cnt)

        if not link_value:
            st.info("Insufficient data to render the Sankey diagram.")
        else:
            fig_sankey = go.Figure(
                go.Sankey(
                    arrangement="snap",
                    node=dict(
                        pad=15,
                        thickness=20,
                        label=SANKEY_NODES,
                        color=[
                            "#3498db",
                            "#e67e22",
                            "#2ecc71",
                            "#e74c3c",
                            "#95a5a6",
                            "#9b59b6",
                        ],
                    ),
                    link=dict(
                        source=link_source,
                        target=link_target,
                        value=link_value,
                    ),
                )
            )
            fig_sankey.update_layout(
                title_text=f"Patient Care Pathway — {selected_partition}",
                font_size=13,
                height=500,
            )
            st.plotly_chart(fig_sankey, use_container_width=True)

        # Supporting tables
        if not no_timeline and isinstance(timeline, list) and timeline:
            with st.expander("Symptom-to-Diagnosis Timeline data"):
                st.dataframe(pd.DataFrame(timeline), use_container_width=True)

        if not no_treatment and isinstance(treatment, list) and treatment:
            with st.expander("Treatment Phase Duration data"):
                st.dataframe(pd.DataFrame(treatment), use_container_width=True)
