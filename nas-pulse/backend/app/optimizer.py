from __future__ import annotations

from typing import Any

from .cascade_simulator import simulate_delay_cascade
from .trajectory_builder import build_trajectory_options


def optimize_interventions(
    flights: list[dict[str, Any]],
    airports: list[dict[str, Any]],
    weather_cells: list[dict[str, Any]],
    constraints: list[dict[str, Any]],
    scenario_time: str,
    max_interventions: int = 20,
) -> dict[str, Any]:
    before = simulate_delay_cascade(
        flights,
        airports,
        weather_cells,
        constraints,
        scenario_time,
        [w["id"] for w in weather_cells],
        [c["id"] for c in constraints],
    )
    high_risk = [f for f in before["scored_flights"] if f["risk_level"] in {"high", "severe"}]
    high_risk.sort(key=lambda f: f["total_risk"] * f["passenger_count"] * _downstream_count(before, f["flight_id"]), reverse=True)

    interventions = []
    trajectory_options = {}
    delay_saved = 0
    for flight in high_risk[:max_interventions]:
        action_type = _preferred_action(flight, scenario_time)
        expected = _expected_delay_reduction(flight, action_type)
        delay_saved += expected
        interventions.append(
            {
                "flight_id": flight["flight_id"],
                "action_type": action_type,
                "expected_delay_reduction_minutes": expected,
                "system_impact_score": round(flight["total_risk"] * flight["passenger_count"] * _downstream_count(before, flight["flight_id"]), 2),
                "explanation": _action_explanation(action_type),
            }
        )
        trajectory_options[flight["flight_id"]] = build_trajectory_options(flight)

    before_delay = before["total_predicted_delay_before_optimization"]
    after_delay = max(0, before_delay - delay_saved)
    before_high = len(high_risk)
    after_high = max(0, before_high - len(interventions))
    delay_reduction = round((before_delay - after_delay) / before_delay * 100, 1) if before_delay else 0
    congestion_reduction = round(min(52.0, len(interventions) * 2.5), 1)

    return {
        "recommended_actions": interventions,
        "before_metrics": {
            "total_delay_minutes": before_delay,
            "average_risk": _average_risk(before["scored_flights"]),
            "high_risk_flights": before_high,
            "congestion_level": _congestion_level(before["airport_congestion_summary"]),
            "interventions_used": 0,
        },
        "after_metrics": {
            "total_delay_minutes": after_delay,
            "average_risk": max(0, round(_average_risk(before["scored_flights"]) - len(interventions) * 0.015, 3)),
            "high_risk_flights": after_high,
            "congestion_level": "watch" if after_high else "nominal",
            "interventions_used": len(interventions),
        },
        "delay_reduction_percentage": delay_reduction,
        "congestion_reduction_percentage": congestion_reduction,
        "trajectory_options": trajectory_options,
        "simulation": before,
    }


def _downstream_count(simulation: dict[str, Any], flight_id: str) -> int:
    edges = simulation["delay_cascade_graph"]["edges"]
    return max(1, sum(1 for e in edges if e["source"] == flight_id) + 1)


def _preferred_action(flight: dict[str, Any], scenario_time: str) -> str:
    departed = flight["departure_time_utc"] <= scenario_time
    if not departed:
        return "GROUND_HOLD"
    if flight["weather_risk"] >= 0.7:
        return "REROUTE_NORTH"
    if flight["airspace_risk"] >= 0.5:
        return "ALTITUDE_SHIFT"
    return "SPEED_ADJUSTMENT"


def _expected_delay_reduction(flight: dict[str, Any], action_type: str) -> int:
    base = 20 + int(flight["total_risk"] * 35)
    return base + {"GROUND_HOLD": 6, "REROUTE_NORTH": 11, "REROUTE_SOUTH": 8, "ALTITUDE_SHIFT": 5, "SPEED_ADJUSTMENT": 3}.get(action_type, 0)


def _action_explanation(action_type: str) -> str:
    return {
        "GROUND_HOLD": "Delay departure at origin to meter demand before the constrained corridor.",
        "REROUTE_NORTH": "Shift around the Chicago weather polygon using a northern corridor.",
        "REROUTE_SOUTH": "Shift around the weather polygon using a southern corridor.",
        "ALTITUDE_SHIFT": "Move demand to a less constrained altitude band where possible.",
        "SPEED_ADJUSTMENT": "Adjust cruise speed slightly to reduce arrival bunching.",
    }[action_type]


def _average_risk(flights: list[dict[str, Any]]) -> float:
    return round(sum(f["total_risk"] for f in flights) / max(len(flights), 1), 3)


def _congestion_level(summary: dict[str, Any]) -> str:
    if any(v["status"] == "over-demand" for v in summary.values()):
        return "over-demand"
    if any(v["status"] == "watch" for v in summary.values()):
        return "watch"
    return "nominal"
