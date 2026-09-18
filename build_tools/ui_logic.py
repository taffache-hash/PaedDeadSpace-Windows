"""Testable orchestration for the PaedDeadSpace Streamlit wrapper.

Scientific calculations are delegated to the installed audited
``paeddeadspace`` package. Presentation helpers only reformat or package
already-calculated core outputs.
"""

from __future__ import annotations

import math
import warnings
from typing import Any

import paeddeadspace as pds

MODEL_PLACEHOLDER = "Select a patient dead-space model"
MODEL_LABELS = (
    MODEL_PLACEHOLDER,
    "User-defined patient VD/VT",
    "Numa–Fletcher composite reference",
    "Pearsall benchmark (VD/VT 0.30)",
)
MODEL_LABEL_TO_KEY = {
    MODEL_LABELS[1]: "user_defined",
    MODEL_LABELS[2]: "numa_fletcher",
    MODEL_LABELS[3]: "pearsall",
}
MODEL_ALIASES = {
    "user_defined": "user_defined",
    "numa_fletcher": "numa_fletcher",
    "pearsall": "pearsall",
    **MODEL_LABEL_TO_KEY,
}

AGE_UNIT_PLACEHOLDER = "Select age unit"
AGE_UNITS = (
    AGE_UNIT_PLACEHOLDER,
    "days",
    "months",
    "years",
)

APPARATUS_QUALIFICATIONS = (
    "Measured/estimated functional dead space",
    "Manufacturer internal/geometric volume",
    "User estimate / uncertain",
)

BREAKDOWN_MESSAGE = (
    "One-compartment model breakdown: effective dead space approaches or "
    "exceeds tidal volume."
)


def vd_vt_fraction_to_percent(fraction: float) -> float:
    """Convert an already-calculated VD/VT fraction for display."""
    value = float(fraction)
    if not math.isfinite(value):
        raise ValueError("VD/VT fraction must be finite")
    return value * 100.0


def alveolar_ventilation_percent_change(
    current: float,
    baseline: float,
) -> float:
    """Return the descriptive percentage change between two core outputs."""
    current_value = float(current)
    baseline_value = float(baseline)
    if not math.isfinite(current_value) or not math.isfinite(baseline_value):
        raise ValueError("alveolar ventilation values must be finite")
    if baseline_value <= 0.0:
        raise ValueError("baseline alveolar ventilation must be positive")
    return (current_value / baseline_value - 1.0) * 100.0


def build_vt_composition_chart_data(
    state: dict[str, Any],
) -> tuple[tuple[str, float], ...]:
    """Package current core volume outputs for a stacked chart.

    No segment is calculated here. The helper verifies that the supplied core
    outputs describe one physical tidal volume before returning them.
    """
    vt_ml = float(state["vt_ml"])
    data = (
        ("Patient-only VD", float(state["patient_vd_ml"])),
        ("Apparatus VD", float(state["apparatus_vd_ml"])),
        ("Alveolar VT", float(state["alveolar_vt_ml"])),
    )
    values = tuple(value for _, value in data)
    if not math.isfinite(vt_ml) or vt_ml <= 0.0:
        raise ValueError("VT composition requires a positive finite VT")
    if any(not math.isfinite(value) or value < 0.0 for value in values):
        raise ValueError("VT composition segments must be finite and nonnegative")
    if not math.isclose(
        math.fsum(values),
        vt_ml,
        rel_tol=1e-12,
        abs_tol=1e-9,
    ):
        raise ValueError("VT composition segments do not sum to absolute VT")
    return data


def build_alveolar_ventilation_chart_data(
    baseline: float,
    current: float,
) -> tuple[tuple[str, float], ...]:
    """Package baseline and current core outputs for a comparison chart."""
    baseline_value = float(baseline)
    current_value = float(current)
    values = (baseline_value, current_value)
    if any(not math.isfinite(value) or value <= 0.0 for value in values):
        raise ValueError("alveolar ventilation chart values must be positive and finite")
    return (
        ("No added apparatus", baseline_value),
        ("Current", current_value),
    )


def _number(name: str, value: Any) -> float:
    if value is None or (isinstance(value, str) and not value.strip()):
        raise pds.InputValidationError(f"{name} is required")
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise pds.InputValidationError(f"{name} must be numeric") from exc
    if not math.isfinite(result):
        raise pds.InputValidationError(f"{name} must be finite")
    return result


def convert_age_to_years(age_value: Any, age_unit: str) -> float:
    """Convert an explicit age to years using the specified deterministic rules."""
    value = _number("age value", age_value)
    if value < 0.0:
        raise pds.InputValidationError("age value must be >= 0")
    if age_unit == "days":
        return value / 365.25
    if age_unit == "months":
        return value / 12.0
    if age_unit == "years":
        return value
    raise pds.InputValidationError(
        "select an age unit: days, months, or years"
    )


def get_vt_preset_values() -> tuple[float, ...]:
    """Read the public exploratory preset catalogue without selecting a value."""
    return tuple(item.value for item in pds.VT_PRESETS_ML_KG)


def _canonical_model_key(model_key: str | None) -> str:
    if model_key is None or model_key == MODEL_PLACEHOLDER:
        raise pds.InputValidationError(
            "select a patient dead-space model before calculating"
        )
    key = MODEL_ALIASES.get(str(model_key).strip())
    if key is None:
        raise pds.InputValidationError(
            "unsupported patient dead-space model; select one of the displayed modes"
        )
    return key


def _provenance_dict(provenance: Any | None) -> dict[str, Any] | None:
    if provenance is None:
        return None
    classification = getattr(provenance, "classification", None)
    if hasattr(classification, "value"):
        classification = classification.value
    return {
        "classification": classification,
        "source_id": getattr(provenance, "source_id", None),
        "citation": getattr(provenance, "citation", None),
        "context": getattr(provenance, "context", None),
        "doi": getattr(provenance, "doi", None),
        "evidence_sources": tuple(
            {
                "source_id": source.source_id,
                "citation": source.citation,
                "context": source.context,
                "doi": source.doi,
            }
            for source in getattr(provenance, "evidence_sources", ())
        ),
    }


def _find_equation_provenance(
    equations: tuple[Any, ...], token: str
) -> dict[str, Any] | None:
    token = token.lower()
    for equation in equations:
        if token in equation.equation_id.lower():
            result = _provenance_dict(equation.provenance)
            if result is not None:
                result["equation_id"] = equation.equation_id
            return result
    return None


def _pearsall_model_provenance() -> dict[str, Any] | None:
    """Present provenance for the patient-VD/VT benchmark without implying VCO2 use.

    PaedDeadSpace-Core v1.0.0 exposes Pearsall through the named benchmark equation
    collection, whose provenance also discusses the inherited Brody VCO2
    equation. This UI does not use VCO2. We reuse only the public citation,
    DOI and classification while describing the selected core model's actual
    patient-VD/VT semantics.
    """
    source = _find_equation_provenance(pds.BENCHMARK_EQUATIONS, "pearsall")
    if source is None:
        return None
    return {
        "classification": source.get("classification"),
        "source_id": "UI_VIEW_OF_PEARSALL_PATIENT_VD_VT_BENCHMARK",
        "citation": str(source.get("citation") or "").replace(
            "; Brody equation", ""
        ),
        "context": (
            "The selected Core mode is the named Pearsall patient "
            "physiologic VD/VT benchmark assumption of 0.30, with apparatus "
            "entered separately. The UI does not use the Brody VCO2 equation "
            "or calculate absolute PaCO2."
        ),
        "doi": source.get("doi"),
        "evidence_sources": (),
    }


def _build_model(
    model_key: str,
    user_patient_vd_vt: Any | None,
) -> tuple[Any, dict[str, str], dict[str, Any] | None]:
    if model_key == "user_defined":
        fraction = _number("patient VD/VT", user_patient_vd_vt)
        if not 0.0 <= fraction < 1.0:
            raise pds.InputValidationError("patient VD/VT must satisfy 0 <= value < 1")
        model = pds.UserDefinedPatientVdVt(fraction)
        metadata = {
            "name": MODEL_LABELS[1],
            "kind": "user-defined",
        }
        provenance = {
            "classification": pds.ParameterClassification.USER_DEFINED.value,
            "source_id": "UI_USER_DEFINED_PATIENT_VD_VT",
            "citation": "User-entered patient physiologic VD/VT",
            "context": (
                "Patient physiologic VD/VT supplied by the user; apparatus is "
                "explicitly excluded and entered separately."
            ),
            "doi": None,
            "evidence_sources": (),
        }
        return model, metadata, provenance

    if model_key == "numa_fletcher":
        model = pds.NumaFletcherCompositeReference()
        metadata = {
            "name": MODEL_LABELS[2],
            "kind": "assumption-model construction",
        }
        provenance = _provenance_dict(model.provenance)
        if provenance is None:
            provenance = _find_equation_provenance(
                pds.MODEL_CONSTRUCTION_EQUATIONS, "numa_fletcher"
            )
        return model, metadata, provenance

    model = pds.PearsallBenchmarkPatientDeadSpace()
    return (
        model,
        {"name": MODEL_LABELS[3], "kind": "benchmark only"},
        _pearsall_model_provenance(),
    )


def _build_apparatus(
    dead_space_ml: float,
    name: str,
    qualification: str,
) -> tuple[tuple[pds.ApparatusComponent, ...], dict[str, Any], dict[str, Any] | None]:
    if dead_space_ml < 0.0:
        raise pds.InputValidationError("apparatus dead space must be >= 0")
    if qualification not in APPARATUS_QUALIFICATIONS:
        raise pds.InputValidationError("select a valid apparatus qualification")

    normalized_name = str(name or "").strip() or "User-entered apparatus"
    metadata = {
        "name": normalized_name,
        "dead_space_ml": dead_space_ml,
        "qualification": qualification,
        "component_constructed": dead_space_ml > 0.0,
    }
    if dead_space_ml == 0.0:
        return (), metadata, None

    provenance = pds.Provenance(
        classification=pds.ParameterClassification.USER_DEFINED,
        source_id="UI_USER_ENTERED_APPARATUS",
        citation="User-entered apparatus dead-space value",
        context=(
            f"The user qualified this entry as: {qualification}. The UI does "
            "not convert geometric/internal volume into functional dead space."
        ),
    )
    component = pds.ApparatusComponent(
        name=normalized_name,
        dead_space_ml=dead_space_ml,
        active=True,
        provenance=provenance,
        qualification=qualification,
    )
    return (component,), metadata, _provenance_dict(provenance)


def _state_dict(state: pds.VentilationState) -> dict[str, float | None]:
    return {
        "vt_ml": state.vt_ml,
        "patient_vd_ml": state.patient_vd_ml_excluding_apparatus,
        "apparatus_vd_ml": state.apparatus_vd_ml,
        "total_vd_ml": state.total_vd_ml,
        "total_vd_vt": state.total_vd_vt,
        "alveolar_vt_ml": state.alveolar_vt_ml,
        "alveolar_ve_ml_min": state.alveolar_ve_ml_min,
        "apparatus_dead_space_percent_vt": state.apparatus_dead_space_percent_vt,
        "vt_to_apparatus_dead_space_ratio": (
            state.vt_to_apparatus_dead_space_ratio
        ),
        "patient_airway_dead_space_ml": state.patient_airway_dead_space_ml,
        "patient_alveolar_tidal_volume_ml": (
            state.patient_alveolar_tidal_volume_ml
        ),
        "patient_alveolar_dead_space_ml": state.patient_alveolar_dead_space_ml,
    }


def _deduplicated_domain_warnings(
    records: list[warnings.WarningMessage],
) -> tuple[str, ...]:
    result: list[str] = []
    seen: set[str] = set()
    for record in records:
        if issubclass(record.category, pds.SourceDomainWarning):
            text = str(record.message)
            if text not in seen:
                seen.add(text)
                result.append(text)
    return tuple(result)


def compute_case(
    weight_kg: Any,
    age_value: Any,
    age_unit: str,
    vt_ml_kg: Any,
    rr_bpm: Any,
    model_key: str | None,
    user_patient_vd_vt: Any | None = None,
    apparatus_ds_ml: Any = 0.0,
    apparatus_name: str = "User-entered apparatus",
    apparatus_qualification: str = "User estimate / uncertain",
) -> dict[str, Any]:
    """Build and compare current and zero-apparatus states through the core."""
    caught: list[warnings.WarningMessage] = []
    partial: dict[str, float] = {}
    apparatus_components: tuple[pds.ApparatusComponent, ...] = ()
    apparatus_metadata: dict[str, Any] = {}
    model_metadata: dict[str, str] = {}
    model_provenance: dict[str, Any] | None = None
    apparatus_provenance: dict[str, Any] | None = None

    try:
        canonical_model = _canonical_model_key(model_key)
        weight = _number("weight", weight_kg)
        entered_age = _number("age value", age_value)
        age_years = convert_age_to_years(entered_age, age_unit)
        vt_per_kg = _number("VT", vt_ml_kg)
        rr = _number("RR", rr_bpm)
        apparatus_value = _number("apparatus dead space", apparatus_ds_ml)

        model, model_metadata, model_provenance = _build_model(
            canonical_model, user_patient_vd_vt
        )
        (
            apparatus_components,
            apparatus_metadata,
            apparatus_provenance,
        ) = _build_apparatus(
            apparatus_value,
            apparatus_name,
            apparatus_qualification,
        )

        inputs = pds.VentilationInputs(
            weight_kg=weight,
            age_years=age_years,
            rr_bpm=rr,
            vt_ml_kg=vt_per_kg,
        )

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always", pds.SourceDomainWarning)

            vt_ml = pds.calculate_tidal_volume_ml(weight, vt_ml_kg=vt_per_kg)
            partial["vt_ml"] = vt_ml
            partial["apparatus_vd_ml"] = pds.apparatus_stack_dead_space_ml(
                apparatus_components
            )

            if isinstance(model, pds.NumaFletcherCompositeReference):
                components = pds.numa_fletcher_composite_reference(
                    weight_kg=weight,
                    age_years=age_years,
                    vt_ml=vt_ml,
                )
                patient_vd_ml = components.patient_vd_ml_excluding_apparatus
            else:
                patient_vd_ml = pds.patient_dead_space_excluding_apparatus_ml(
                    vt_ml,
                    model,
                    weight_kg=weight,
                    age_years=age_years,
                )
            partial["patient_vd_ml"] = patient_vd_ml
            partial["total_vd_ml"] = pds.total_dead_space_ml(
                patient_vd_ml, partial["apparatus_vd_ml"]
            )

            current = pds.calculate_ventilation(
                inputs,
                model,
                apparatus_components,
            )
            baseline = pds.calculate_ventilation(inputs, model, ())
            burden = pds.relative_co2_burden(
                baseline.alveolar_ve_ml_min,
                current.alveolar_ve_ml_min,
            )
            required_rr = pds.rr_required_to_preserve_alveolar_ventilation(
                baseline.alveolar_ve_ml_min,
                current.vt_ml,
                current.total_vd_ml,
            )
            rr_multiplier = required_rr / inputs.rr_bpm

        result: dict[str, Any] = {
            "status": "ok",
            "inputs": {
                "weight_kg": weight,
                "age_value": entered_age,
                "age_unit": age_unit,
                "age_years": age_years,
                "vt_ml_kg": vt_per_kg,
                "rr_bpm": rr,
            },
            "model": model_metadata,
            "apparatus": apparatus_metadata,
            "apparatus_components": apparatus_components,
            "state": _state_dict(current),
            "baseline_state": _state_dict(baseline),
            "comparison": {
                "baseline_alveolar_ve_ml_min": baseline.alveolar_ve_ml_min,
                "current_to_baseline_alveolar_ve_ratio": (
                    current.alveolar_ve_ml_min / baseline.alveolar_ve_ml_min
                ),
                "relative_co2_burden": burden,
                "rr_required_bpm": required_rr,
                "rr_multiplier": rr_multiplier,
            },
            "provenance": {
                "model": model_provenance,
                "apparatus": apparatus_provenance,
            },
        }
    except pds.NonPhysicalStateError as exc:
        result = {
            "status": "model_breakdown",
            "message": BREAKDOWN_MESSAGE,
            "detail": str(exc),
            "partial": partial,
            "model": model_metadata,
            "apparatus": apparatus_metadata,
            "apparatus_components": apparatus_components,
            "provenance": {
                "model": model_provenance,
                "apparatus": apparatus_provenance,
            },
        }
    except pds.InputValidationError as exc:
        result = {
            "status": "validation_error",
            "error": str(exc),
        }

    result["warnings"] = _deduplicated_domain_warnings(caught)
    return result


def get_williams_term_infant_reference() -> dict[str, Any]:
    """Return display data read from the core's non-computational profile."""
    profile = pds.WILLIAMS_TERM_INFANT_REFERENCE_PROFILE
    fields = (
        ("Physiologic dead space", profile.physiologic_dead_space_ml_kg),
        ("Total anatomical dead space", profile.total_anatomical_dead_space_ml_kg),
        ("Apparatus dead space", profile.apparatus_dead_space_ml_kg),
        (
            "Anatomical minus apparatus dead space",
            profile.anatomical_minus_apparatus_dead_space_ml_kg,
        ),
        ("Alveolar dead space", profile.alveolar_dead_space_ml_kg),
        ("VT", profile.tidal_volume_ml_kg),
        ("VD/VT", profile.dead_space_tidal_volume_ratio),
        ("Alveolar ventilation", profile.alveolar_ventilation_ml_kg_min),
    )
    return {
        "kind": "descriptive_reference_only",
        "accepted_as_computational_model": False,
        "interpretation": profile.interpretation,
        "values": {
            label: {
                "median": interval.median,
                "iqr": interval.iqr,
                "unit": interval.unit,
            }
            for label, interval in fields
        },
        "provenance": _provenance_dict(profile.provenance),
    }
