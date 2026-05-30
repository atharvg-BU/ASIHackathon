from __future__ import annotations

from typing import Any

from .historical_case_matcher import get_top_case_matches


def generate_briefing(
    scenario_time: str,
    simulation: dict[str, Any],
    optimization: dict[str, Any] | None = None,
    selected_flight_id: str | None = None,
) -> dict[str, Any]:
    direct = simulation["direct_impact_count"]
    indirect = simulation["indirect_impact_count"]
    before_delay = simulation["total_predicted_delay_before_optimization"]
    impacted = simulation["impacted_flights"]
    top_flight = selected_flight_id or (impacted[0]["flight_id"] if impacted else "the selected flight")
    actions = optimization["recommended_actions"] if optimization else []
    action_summary = _summarize_actions(actions)
    matches = get_top_case_matches({"scenario_tags": simulation.get("scenario_tags", [])}, k=1)
    historical_sentence = ""
    if matches:
        case = matches[0]
        lesson = case["system_lesson"].split(".")[0].lower()
        historical_sentence = (
            f" Historical case memory found similar patterns in {case['case_name']}, "
            f"suggesting the system should prioritize {lesson}."
        )

    if optimization:
        after = optimization["after_metrics"]["total_delay_minutes"]
        reduction = optimization["delay_reduction_percentage"]
        text = (
            f"Convective weather is reducing usable capacity through the Chicago corridor around {scenario_time} UTC. "
            f"NAS Pulse estimates {before_delay} minutes of network delay before intervention, with {direct} direct "
            f"and {indirect} indirect impacts. The minimum-intervention plan uses {len(actions)} actions ({action_summary}) "
            f"and reduces predicted delay to {after} minutes, a {reduction}% improvement. For {top_flight}, dispatchers may "
            f"consider the route and timing options shown in the trajectory panel as demo-level decision support."
            f"{historical_sentence} Demo only - not for operational aviation use."
        )
    else:
        text = (
            f"At {scenario_time} UTC, the Chicago corridor scenario shows {direct} directly impacted flights and "
            f"{indirect} downstream impacts, with {before_delay} predicted delay minutes before optimization. "
            f"For {top_flight}, the system should prioritize network delay reduction, congestion monitoring, and high-level "
            f"reroute or ground-hold tradeoffs rather than flight-by-flight isolation."
            f"{historical_sentence} Demo only - not for operational aviation use."
        )
    return {"briefing": text, "historical_case_match": matches[0] if matches else None}


def _summarize_actions(actions: list[dict[str, Any]]) -> str:
    if not actions:
        return "no actions selected"
    counts: dict[str, int] = {}
    for action in actions:
        counts[action["action_type"]] = counts.get(action["action_type"], 0) + 1
    return ", ".join(f"{count} {name.lower().replace('_', ' ')}" for name, count in counts.items())
