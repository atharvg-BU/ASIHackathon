from __future__ import annotations

from typing import Any

from .data_loader import load_historical_cases


def extract_scenario_tags(simulation_result: dict[str, Any] | None, selected_flight: dict[str, Any] | None = None) -> list[str]:
    tags = set((simulation_result or {}).get("scenario_tags", []))
    if selected_flight:
        if selected_flight.get("weather_risk", 0) > 0:
            tags.update(["convective_weather", "weather_hazard"])
        if selected_flight.get("airspace_risk", 0) > 0:
            tags.add("airspace_constraint")
        if selected_flight.get("airport_congestion_risk", 0) > 0.55:
            tags.add("airport_congestion")
        if selected_flight.get("delay_propagation_risk", 0) > 0.5:
            tags.add("delay_cascade")
    return sorted(tags)


def compute_case_similarity(scenario_tags: list[str], case_tags: list[str], case: dict[str, Any] | None = None) -> float:
    scenario = set(scenario_tags)
    historical = set(case_tags)
    if not scenario or not historical:
        return 0.0
    score = len(scenario & historical) / len(scenario | historical)
    primary = (case or {}).get("primary_event_type", "")
    if "convective_weather" in scenario and "convective_weather" in primary:
        score += 0.18
    trigger = (case or {}).get("trigger_conditions", {})
    if "airspace_constraint" in scenario and trigger.get("airspace_related"):
        score += 0.08
    if "weather_hazard" in scenario and trigger.get("weather_related"):
        score += 0.08
    return round(min(score, 1.0), 3)


def get_top_case_matches(scenario: dict[str, Any], k: int = 3) -> list[dict[str, Any]]:
    scenario_tags = scenario.get("scenario_tags", [])
    matches = []
    for case in load_historical_cases():
        score = compute_case_similarity(scenario_tags, case["tags"], case)
        matched_tags = sorted(set(scenario_tags) & set(case["tags"]))
        matches.append(
            {
                "case_id": case["case_id"],
                "case_name": case["case_name"],
                "similarity_score": score,
                "matched_tags": matched_tags,
                "situation_summary": case["situation_summary"],
                "system_lesson": case["system_lesson"],
                "how_nas_pulse_uses_it": case["how_nas_pulse_uses_it"],
            }
        )
    return sorted(matches, key=lambda item: item["similarity_score"], reverse=True)[:k]
