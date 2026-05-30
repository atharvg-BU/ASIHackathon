from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from .data_loader import time_to_minutes
from .geometry import route_intersects_polygon


def active_between(item: dict[str, Any], scenario_time: str) -> bool:
    now = time_to_minutes(scenario_time)
    return time_to_minutes(item["start_time_utc"]) <= now <= time_to_minutes(item["end_time_utc"])


def classify_risk(score: float) -> str:
    if score < 0.25:
        return "low"
    if score < 0.50:
        return "medium"
    if score < 0.75:
        return "high"
    return "severe"


def compute_airport_congestion(flights: list[dict[str, Any]], airports: list[dict[str, Any]]) -> dict[str, Any]:
    airport_capacity = {a["airport_code"]: a["capacity_per_hour"] for a in airports}
    arrivals_by_hour: dict[str, Counter[int]] = defaultdict(Counter)
    for flight in flights:
        hour = time_to_minutes(flight["arrival_time_utc"]) // 60
        arrivals_by_hour[flight["destination"]][hour] += 1

    summary = {}
    for airport, counts in arrivals_by_hour.items():
        cap = max(airport_capacity.get(airport, 30), 1)
        peak_count = max(counts.values())
        load = min(1.0, peak_count / max(4, cap * 0.22))
        summary[airport] = {
            "peak_arrivals": peak_count,
            "capacity_per_hour": cap,
            "congestion_risk": round(load, 3),
            "status": "over-demand" if load > 0.85 else "watch" if load > 0.55 else "nominal",
        }
    return summary


def compute_delay_propagation_risk(flights: list[dict[str, Any]]) -> dict[str, float]:
    by_aircraft: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for flight in flights:
        by_aircraft[flight["aircraft_id"]].append(flight)
    scores = {f["flight_id"]: 0.0 for f in flights}
    for turns in by_aircraft.values():
        ordered = sorted(turns, key=lambda x: time_to_minutes(x["departure_time_utc"]))
        for idx, flight in enumerate(ordered):
            if idx < len(ordered) - 1:
                turn_gap = time_to_minutes(ordered[idx + 1]["departure_time_utc"]) - time_to_minutes(flight["arrival_time_utc"])
                scores[flight["flight_id"]] = max(scores[flight["flight_id"]], 0.75 if turn_gap < 45 else 0.45)
            if idx > 0:
                scores[flight["flight_id"]] = max(scores[flight["flight_id"]], 0.35)
    return scores


def score_flights(
    flights: list[dict[str, Any]],
    airports: list[dict[str, Any]],
    weather_cells: list[dict[str, Any]],
    constraints: list[dict[str, Any]],
    scenario_time: str = "14:30",
    enabled_weather_ids: list[str] | None = None,
    enabled_constraint_ids: list[str] | None = None,
) -> list[dict[str, Any]]:
    enabled_weather_ids = enabled_weather_ids or [w["id"] for w in weather_cells]
    enabled_constraint_ids = enabled_constraint_ids or [c["id"] for c in constraints]
    active_weather = [w for w in weather_cells if w["id"] in enabled_weather_ids and active_between(w, scenario_time)]
    active_constraints = [c for c in constraints if c["id"] in enabled_constraint_ids and active_between(c, scenario_time)]
    airport_summary = compute_airport_congestion(flights, airports)
    propagation = compute_delay_propagation_risk(flights)

    scored = []
    for flight in flights:
        route = flight["planned_route_latlons"]
        weather_hits = [w for w in active_weather if route_intersects_polygon(route, w["polygon"])]
        constraint_hits = [c for c in active_constraints if route_intersects_polygon(route, c["polygon"])]
        weather_risk = min(1.0, max([w["severity"] for w in weather_hits], default=0.0))
        airspace_risk = min(1.0, max([c.get("capacity_reduction_percent", 0) / 60 for c in constraint_hits], default=0.0))
        airport_congestion_risk = airport_summary.get(flight["destination"], {}).get("congestion_risk", 0.0)
        delay_propagation_risk = propagation[flight["flight_id"]]
        total = (
            0.40 * weather_risk
            + 0.25 * airspace_risk
            + 0.20 * delay_propagation_risk
            + 0.15 * airport_congestion_risk
        )
        scored.append(
            {
                **flight,
                "weather_risk": round(weather_risk, 3),
                "airspace_risk": round(airspace_risk, 3),
                "airport_congestion_risk": round(airport_congestion_risk, 3),
                "delay_propagation_risk": round(delay_propagation_risk, 3),
                "total_risk": round(min(total, 1.0), 3),
                "risk_level": classify_risk(total),
                "weather_hits": [w["id"] for w in weather_hits],
                "constraint_hits": [c["id"] for c in constraint_hits],
            }
        )
    return scored
