from __future__ import annotations

from importlib.metadata import version

import matplotlib.pyplot as plt
import streamlit as st

from ui_logic import (
    AGE_UNITS,
    APPARATUS_QUALIFICATIONS,
    MODEL_LABELS,
    MODEL_LABEL_TO_KEY,
    alveolar_ventilation_percent_change,
    build_alveolar_ventilation_chart_data,
    build_vt_composition_chart_data,
    compute_case,
    get_vt_preset_values,
    get_williams_term_infant_reference,
    vd_vt_fraction_to_percent,
)


UI_LABEL = "PaedDeadSpace UI v1.0.0"

st.set_page_config(page_title="PaedDeadSpace", layout="wide")

st.title("PaedDeadSpace")
st.caption("pediatric apparatus dead-space explorer")
st.sidebar.markdown("### PaedDeadSpace")
st.sidebar.caption("Version 1.0.0")
st.sidebar.caption("Core: PaedDeadSpace v1.0.0")
st.warning(
    "Educational/exploratory software only — not patient-specific clinical "
    "decision support."
)
st.info(
    "Calculations are performed locally using the installed audited scientific "
    "core. This UI does not call an external API."
)


def clear_stored_result() -> None:
    st.session_state.pop("case_result", None)


def format_number(value: float, digits: int = 2) -> str:
    return f"{value:,.{digits}f}"


def render_provenance_entry(entry: dict[str, object] | None) -> None:
    if not entry:
        return
    if entry.get("classification"):
        st.write(f"**Classification:** {entry['classification']}")
    if entry.get("source_id"):
        st.write(f"**Source ID:** {entry['source_id']}")
    if entry.get("citation"):
        st.write(f"**Citation:** {entry['citation']}")
    if entry.get("context"):
        st.write(f"**Context:** {entry['context']}")
    if entry.get("doi"):
        st.write(f"**DOI:** {entry['doi']}")
    evidence_sources = entry.get("evidence_sources", ())
    if evidence_sources:
        st.write("**Component evidence sources:**")
        for source in evidence_sources:
            st.write(f"- {source['citation']}")
            st.caption(str(source["context"]))
            if source.get("doi"):
                st.caption(f"DOI: {source['doi']}")


def model_presentation(model: dict[str, object]) -> str:
    name = str(model.get("name", "Unavailable"))
    if "Numa" in name:
        return "Numa–Fletcher — reference / sensitivity construction"
    if "Pearsall" in name:
        return "Pearsall benchmark — benchmark only"
    if "User-defined" in name:
        return "User-defined patient physiologic VD/VT"
    return name


def render_model_banner(result: dict[str, object]) -> None:
    model = result.get("model", {})
    st.subheader(f"Patient dead-space model: {model_presentation(model)}")


def render_case_summary(result: dict[str, object]) -> None:
    inputs = result["inputs"]
    state = result["state"]
    apparatus = result["apparatus"]
    model = result["model"]
    age_value = format_number(inputs["age_value"])
    age_unit = inputs["age_unit"]
    summary = (
        f"**Weight:** {format_number(inputs['weight_kg'])} kg  |  "
        f"**Age:** {age_value} {age_unit}  |  "
        f"**VT:** {format_number(state['vt_ml'])} mL "
        f"({format_number(inputs['vt_ml_kg'])} mL/kg)  |  "
        f"**RR:** {format_number(inputs['rr_bpm'])} breaths/min  |  "
        f"**Model:** {model_presentation(model)}  |  "
        f"**Apparatus DS:** {format_number(apparatus['dead_space_ml'])} mL"
    )
    st.markdown(summary)


def _contrast_text_color(facecolor: tuple[float, float, float, float]) -> str:
    r, g, b, _ = facecolor
    luminance = 0.2126 * r + 0.7152 * g + 0.0722 * b
    return "black" if luminance > 0.58 else "white"


def _transparent_axes(figure, axis) -> None:
    figure.patch.set_alpha(0.0)
    axis.set_facecolor("none")
    axis.axis("off")


def render_vt_composition(state: dict[str, object]) -> None:
    data = build_vt_composition_chart_data(state)
    st.subheader("Current tidal-volume composition")

    figure, axis = plt.subplots(figsize=(10, 1.05))
    _transparent_axes(figure, axis)
    left = 0.0
    for label, value_ml in data:
        bars = axis.barh([0], [value_ml], left=left, height=0.62, label=label)
        patch = bars.patches[0]
        if value_ml > 0:
            axis.text(
                left + value_ml / 2.0,
                0,
                f"{label}\n{format_number(value_ml)} mL",
                ha="center",
                va="center",
                fontsize=9,
                fontweight="bold",
                color=_contrast_text_color(patch.get_facecolor()),
                clip_on=True,
            )
        left += value_ml
    axis.set_xlim(0.0, float(state["vt_ml"]))
    axis.set_ylim(-0.55, 0.55)
    figure.tight_layout(pad=0.15)
    st.pyplot(figure, width="stretch")
    plt.close(figure)

    values = " | ".join(
        f"{label}: {format_number(value_ml)} mL" for label, value_ml in data
    )
    st.caption(
        f"{values}. These are model-derived components of the same current "
        "tidal-volume output; they are not independently measured segments."
    )


def render_alveolar_ventilation_chart(result: dict[str, object]) -> None:
    state = result["state"]
    comparison = result["comparison"]
    data = build_alveolar_ventilation_chart_data(
        comparison["baseline_alveolar_ve_ml_min"],
        state["alveolar_ve_ml_min"],
    )

    st.subheader("Alveolar ventilation: no added apparatus vs current")
    labels = [label for label, _ in data]
    values = [value for _, value in data]
    figure, axis = plt.subplots(figsize=(10, 1.65))
    _transparent_axes(figure, axis)
    bars = axis.barh([1, 0], values, height=0.55)
    maximum = max(values) if values else 1.0
    axis.set_xlim(0.0, maximum * 1.03)
    axis.set_ylim(-0.55, 1.55)

    for y, label, value, patch in zip([1, 0], labels, values, bars.patches):
        text_color = _contrast_text_color(patch.get_facecolor())
        axis.text(
            min(value * 0.03, maximum * 0.015),
            y,
            f"{label}  •  {format_number(value)} mL/min",
            ha="left",
            va="center",
            fontsize=9,
            fontweight="bold",
            color=text_color,
            clip_on=True,
        )

    figure.tight_layout(pad=0.15)
    st.pyplot(figure, width="stretch")
    plt.close(figure)

    change = alveolar_ventilation_percent_change(
        current=state["alveolar_ve_ml_min"],
        baseline=comparison["baseline_alveolar_ve_ml_min"],
    )
    st.metric(
        "Change vs no-added-apparatus baseline",
        f"{format_number(change)}%",
    )
    st.caption(
        "This comparison is descriptive and is not a clinical target or an "
        "additional physiological model."
    )


def render_result(result: dict[str, object]) -> None:
    st.header("RESULTS")

    for warning_text in result.get("warnings", ()):
        st.warning(str(warning_text))

    status = result["status"]
    if status == "validation_error":
        st.error(f"Input validation error: {result['error']}")
        return

    render_model_banner(result)

    if status == "model_breakdown":
        st.error(
            "One-compartment model breakdown: effective dead space approaches "
            "or exceeds tidal volume."
        )
        st.caption(
            "This is a mathematical one-compartment boundary, not a clinical "
            "threshold. No respiratory-rate estimate is produced in this state."
        )
        partial = result.get("partial", {})
        labels = (
            ("vt_ml", "Absolute VT", "mL"),
            ("patient_vd_ml", "Patient-only VD", "mL"),
            ("apparatus_vd_ml", "Apparatus VD", "mL"),
            ("total_vd_ml", "Patient + apparatus VD", "mL"),
        )
        columns = st.columns(4)
        for column, (key, label, unit) in zip(columns, labels):
            if key in partial:
                column.metric(label, f"{format_number(partial[key])} {unit}")
        st.caption(f"Core detail: {result['detail']}")
        st.info(
            "Composition and alveolar-ventilation charts are not drawn because "
            "their segments would be misleading in this nonphysical model state."
        )
    else:
        render_case_summary(result)
        state = result["state"]
        comparison = result["comparison"]

        st.divider()
        st.subheader("VOLUMES")
        volume_metrics = (
            ("Absolute VT", f"{format_number(state['vt_ml'])} mL"),
            ("Patient-only VD", f"{format_number(state['patient_vd_ml'])} mL"),
            ("Apparatus VD", f"{format_number(state['apparatus_vd_ml'])} mL"),
            ("Total VD", f"{format_number(state['total_vd_ml'])} mL"),
            ("Alveolar VT", f"{format_number(state['alveolar_vt_ml'])} mL"),
        )
        columns = st.columns(5)
        for column, (label, value) in zip(columns, volume_metrics):
            column.metric(label, value)

        if state["patient_airway_dead_space_ml"] is not None:
            st.markdown("**Numa–Fletcher component outputs**")
            st.caption(
                "Reference / sensitivity construction. Components are derived "
                "model outputs and apparatus remains excluded from patient-only VD."
            )
            columns = st.columns(4)
            component_metrics = (
                (
                    "Intrathoracic component",
                    state["patient_airway_dead_space_ml"],
                ),
                (
                    "Alveolar tidal volume used by composite",
                    state["patient_alveolar_tidal_volume_ml"],
                ),
                (
                    "Alveolar component",
                    state["patient_alveolar_dead_space_ml"],
                ),
                ("Patient-only total", state["patient_vd_ml"]),
            )
            for column, (label, value) in zip(columns, component_metrics):
                column.metric(label, f"{format_number(value)} mL")

        render_vt_composition(state)

        st.divider()
        st.subheader("VENTILATION")
        fraction = state["total_vd_vt"]
        ventilation_metrics = (
            ("Total VD/VT — fraction", format_number(fraction, 3)),
            (
                "Total VD/VT — percentage",
                f"{format_number(vd_vt_fraction_to_percent(fraction), 1)}%",
            ),
            (
                "Alveolar minute ventilation",
                f"{format_number(state['alveolar_ve_ml_min'])} mL/min",
            ),
            (
                "Baseline alveolar minute ventilation",
                f"{format_number(comparison['baseline_alveolar_ve_ml_min'])} mL/min",
            ),
            (
                "Current / baseline alveolar ventilation",
                format_number(
                    comparison["current_to_baseline_alveolar_ve_ratio"], 3
                ),
            ),
        )
        columns = st.columns(5)
        for column, (label, value) in zip(columns, ventilation_metrics):
            column.metric(label, value)
        st.caption(
            "The VD/VT fraction and percentage are the same quantity shown in "
            "two forms, not independent outputs."
        )
        render_alveolar_ventilation_chart(result)

        st.divider()
        st.subheader("APPARATUS EFFECT")
        effect_metrics = (
            (
                "Apparatus DS / VT",
                f"{format_number(state['apparatus_dead_space_percent_vt'])}%",
            ),
            (
                "Relative CO₂ burden",
                format_number(comparison["relative_co2_burden"], 3),
            ),
            (
                "RR required to preserve baseline alveolar ventilation",
                f"{format_number(comparison['rr_required_bpm'])} breaths/min",
            ),
            ("RR multiplier", format_number(comparison["rr_multiplier"], 3)),
        )
        columns = st.columns(4)
        for column, (label, value) in zip(columns, effect_metrics):
            column.metric(label, value)
        st.info(
            "Under the current fixed-VCO₂ one-compartment assumptions, the RR "
            "multiplier and relative CO₂ burden are algebraically identical. "
            "They are not independent evidence. No absolute PaCO₂ is calculated."
        )

    apparatus = result.get("apparatus", {})
    provenance = result.get("provenance", {})
    with st.expander("Sources & provenance", expanded=False):
        model = result.get("model", {})
        st.write(f"**Selected model:** {model.get('name', 'Unavailable')}")
        st.write(f"**Model type:** {model.get('kind', 'Unavailable')}")
        render_provenance_entry(provenance.get("model"))
        st.divider()
        st.write("**Apparatus is entered separately from patient VD.**")
        st.write(f"**Apparatus name:** {apparatus.get('name', 'Unavailable')}")
        st.write(
            f"**Apparatus qualification:** "
            f"{apparatus.get('qualification', 'Unavailable')}"
        )
        st.write(
            "**Apparatus component constructed:** "
            f"{'yes' if apparatus.get('component_constructed') else 'no'}"
        )
        render_provenance_entry(provenance.get("apparatus"))


stored_result = st.session_state.get("case_result")
inputs_expanded = not stored_result or stored_result.get("status") == "validation_error"

with st.expander("Case inputs", expanded=inputs_expanded):
    st.markdown("**Patient dead-space model**")
    model_label = st.selectbox(
        "Patient dead-space model",
        MODEL_LABELS,
        index=0,
        key="patient_model_label",
        on_change=clear_stored_result,
    )
    model_key = MODEL_LABEL_TO_KEY.get(model_label)

    if model_key == "user_defined":
        st.caption(
            "Enter patient physiologic VD/VT only. It excludes apparatus, which "
            "must be entered separately below."
        )
    elif model_key == "numa_fletcher":
        st.info(
            "Reference / sensitivity construction, not a universal or healthy "
            "default. Apparatus dead space remains separate."
        )
    elif model_key == "pearsall":
        st.info(
            "Benchmark only: patient VD/VT = 0.30, excluding apparatus. The core "
            "will warn when inputs are outside the named benchmark context."
        )

    with st.form("case_form"):
        st.markdown("**Patient and ventilation**")
        col1, col2, col3 = st.columns(3)
        with col1:
            weight_kg = st.text_input("Weight, kg", value="")
            age_value = st.text_input("Age value", value="")
        with col2:
            age_unit = st.selectbox("Age unit", AGE_UNITS, index=0)
            vt_ml_kg = st.text_input("VT, mL/kg", value="")
        with col3:
            rr_bpm = st.text_input("RR, breaths/min", value="")
            presets = "/".join(f"{value:g}" for value in get_vt_preset_values())
            st.caption(
                "Exploratory core presets: "
                f"{presets} mL/kg. None is preselected or auto-filled."
            )

        user_patient_vd_vt = None
        if model_key == "user_defined":
            user_patient_vd_vt = st.text_input(
                "Patient VD/VT (0 ≤ value < 1)",
                value="",
            )
            st.caption(
                "Patient physiologic VD/VT only; exclude all ETT, connector, "
                "sensor, filter, circuit, and other apparatus dead space."
            )

        st.markdown("**Apparatus**")
        app_col1, app_col2, app_col3 = st.columns(3)
        with app_col1:
            apparatus_ds_ml = st.number_input(
                "Total apparatus dead space, mL",
                min_value=0.0,
                value=0.0,
                step=1.0,
            )
        with app_col2:
            apparatus_name = st.text_input(
                "Short optional name",
                value="User-entered apparatus",
            )
        with app_col3:
            apparatus_qualification = st.selectbox(
                "Qualification",
                APPARATUS_QUALIFICATIONS,
                index=2,
            )
        st.caption(
            "Manufacturer internal/geometric volume is not silently converted "
            "to measured or estimated functional dead space."
        )

        submitted = st.form_submit_button("Calculate", type="primary")

if submitted:
    st.session_state["case_result"] = compute_case(
        weight_kg=weight_kg,
        age_value=age_value,
        age_unit=age_unit,
        vt_ml_kg=vt_ml_kg,
        rr_bpm=rr_bpm,
        model_key=model_key,
        user_patient_vd_vt=user_patient_vd_vt,
        apparatus_ds_ml=apparatus_ds_ml,
        apparatus_name=apparatus_name,
        apparatus_qualification=apparatus_qualification,
    )
    st.rerun()

stored_result = st.session_state.get("case_result")
if stored_result:
    render_result(stored_result)

reference = get_williams_term_infant_reference()
with st.expander("Term-infant descriptive reference (Williams et al.)", expanded=False):
    st.warning(
        "Descriptive cohort reference only. This is not a computational "
        "dead-space mode and is never auto-applied to the current case."
    )
    st.write(
        "Controls were term infants without underlying respiratory disease but "
        "were invasively ventilated for poor perinatal adaptation."
    )
    st.write(
        "Group medians and IQRs must not be algebraically combined into an "
        "individual patient default."
    )
    for label, interval in reference["values"].items():
        st.write(
            f"**{label}:** {interval['median']:g} {interval['unit']} "
            f"(IQR {interval['iqr'][0]:g}–{interval['iqr'][1]:g})"
        )
    st.divider()
    render_provenance_entry(reference["provenance"])

try:
    core_version = version("paeddeadspace")
except Exception:
    core_version = "version unavailable"

with st.expander("Software version & runtime", expanded=False):
    st.write(f"**Installed paeddeadspace package:** {core_version}")
    st.write(f"**UI:** {UI_LABEL}")
    st.write("**Runtime:** calculations are local; no external API is used.")

with st.expander("About / Citation", expanded=False):
    st.write("**PaedDeadSpace: Pediatric Apparatus Dead-Space Explorer — UI**")
    st.write("Version: **v1.0.0**")
    st.write("Author: **Paolo Taffache** (ORCID: 0009-0002-8806-9733)")
    st.write("License: **MIT**")
    st.write("Core repository: https://github.com/taffache-hash/PaedDeadSpace-Core")
    st.write("UI repository: https://github.com/taffache-hash/PaedDeadSpace-UI")
    st.write("Preferred project citation: PaedDeadSpace-Core Zenodo DOI (pending first archived release).")
    st.warning("For educational and research use only. Not intended for clinical decision-making or patient-specific treatment recommendations.")
