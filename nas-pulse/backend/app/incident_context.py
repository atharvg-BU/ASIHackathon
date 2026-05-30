from __future__ import annotations

import re
from typing import Any

from .emergency_geography import WATER_BODIES, haversine_nm, nearby_open_areas, nearby_water_bodies
from .live_simulator import build_live_flight_state


PLACE_ALIASES = {
    "chicago": (41.8781, -87.6298, "Chicago area"),
    "san francisco": (37.7749, -122.4194, "San Francisco area"),
    "washington": (38.9072, -77.0369, "Washington DC area"),
    "denver": (39.7392, -104.9903, "Denver area"),
    "new york": (40.7128, -74.0060, "New York area"),
}


def build_incident_context(
    message: str,
    selected_flight: dict[str, Any] | None,
    airports: list[dict[str, Any]],
    scenario_time: str,
) -> dict[str, Any] | None:
    if not selected_flight:
        return None
    point = _incident_point_from_message(message, airports)
    source = "message"
    if not point:
        live = build_live_flight_state(selected_flight, scenario_time)
        lat, lon = live["current_position"]
        point = {"lat": lat, "lon": lon, "label": f"simulated current position at {scenario_time} UTC"}
        source = "live_simulation"

    nearest_airports = _nearest_airports(point["lat"], point["lon"], airports)
    waters = nearby_water_bodies(point["lat"], point["lon"], 100.0)
    open_areas = nearby_open_areas(point["lat"], point["lon"], 160.0)
    return {
        "source": source,
        "label": point["label"],
        "lat": round(point["lat"], 4),
        "lon": round(point["lon"], 4),
        "nearest_airports": nearest_airports[:5],
        "nearby_water_bodies": waters,
        "nearby_open_areas": open_areas,
        "route_phase": _route_phase(selected_flight, scenario_time),
        "note": "Incident location is a demo estimate from the message or simulated aircraft position."
    }


def format_incident_context(context: dict[str, Any] | None) -> str:
    if not context:
        return "Incident location context is unavailable because no focused flight is loaded."
    airports = ", ".join(
        f"{item['airport_code']} ({item['distance_nm']} NM)" for item in context["nearest_airports"][:3]
    ) or "none in demo set"
    waters = ", ".join(
        f"{item['name']} ({item['distance_nm']} NM)" for item in context["nearby_water_bodies"][:3]
    ) or "no nearby major demo water feature"
    open_areas = ", ".join(
        f"{item['name']} ({item['distance_nm']} NM)" for item in context.get("nearby_open_areas", [])[:3]
    ) or "no nearby open-area candidate in demo set"
    return (
        f"Incident location: {context['label']} [{context['source']}], approx "
        f"{context['lat']}, {context['lon']}. Route phase: {context['route_phase']}. "
        f"Nearest demo airports: {airports}. Nearby water context: {waters}. Open-area context: {open_areas}."
    )


def _incident_point_from_message(message: str, airports: list[dict[str, Any]]) -> dict[str, Any] | None:
    upper = message.upper()
    for airport in airports:
        code = airport["airport_code"]
        if re.search(rf"\b{re.escape(code)}\b", upper):
            return {"lat": airport["lat"], "lon": airport["lon"], "label": f"near {code}"}
    lower = message.lower()
    for phrase, (lat, lon, label) in PLACE_ALIASES.items():
        if phrase in lower:
            return {"lat": lat, "lon": lon, "label": label}
    for water in WATER_BODIES:
        if water["name"].lower().split(" near ")[0] in lower:
            return {"lat": water["lat"], "lon": water["lon"], "label": water["name"]}
    return None


def _nearest_airports(lat: float, lon: float, airports: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ranked = []
    for airport in airports:
        ranked.append(
            {
                "airport_code": airport["airport_code"],
                "name": airport["name"],
                "distance_nm": round(haversine_nm(lat, lon, airport["lat"], airport["lon"]), 1),
                "capacity_per_hour": airport["capacity_per_hour"],
            }
        )
    return sorted(ranked, key=lambda item: item["distance_nm"])


def _route_phase(flight: dict[str, Any], scenario_time: str) -> str:
    live = build_live_flight_state(flight, scenario_time)
    progress = live["progress"]
    if progress < 0.18:
        return "departure / early enroute"
    if progress > 0.82:
        return "arrival / late enroute"
    return "enroute"
