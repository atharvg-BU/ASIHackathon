from __future__ import annotations

import math
from typing import Any


WATER_BODIES = [
    {"name": "San Francisco Bay", "type": "bay", "lat": 37.65, "lon": -122.35},
    {"name": "Pacific Ocean near San Francisco", "type": "coastal water", "lat": 37.62, "lon": -122.48},
    {"name": "Lake Michigan", "type": "great lake", "lat": 42.2, "lon": -87.2},
    {"name": "Mississippi River near Quad Cities", "type": "river", "lat": 41.5, "lon": -90.6},
    {"name": "Ohio River corridor", "type": "river", "lat": 39.1, "lon": -84.7},
    {"name": "Potomac River near Washington", "type": "river", "lat": 38.85, "lon": -77.05},
    {"name": "Chesapeake Bay", "type": "bay", "lat": 38.6, "lon": -76.3},
    {"name": "Hudson River / New York Harbor", "type": "river/harbor", "lat": 40.72, "lon": -74.02},
    {"name": "Atlantic Ocean near New York", "type": "coastal water", "lat": 40.45, "lon": -73.7},
    {"name": "Lake Erie", "type": "great lake", "lat": 41.8, "lon": -81.2},
]

OPEN_AREA_CANDIDATES = [
    {"name": "Utah/Nevada open desert highway corridor", "type": "open road corridor", "lat": 39.4, "lon": -113.6},
    {"name": "Bonneville Salt Flats open-area corridor", "type": "open flat terrain", "lat": 40.8, "lon": -113.8},
    {"name": "Eastern Colorado plains highway corridor", "type": "open road corridor", "lat": 39.5, "lon": -103.5},
    {"name": "Mojave Desert open highway corridor", "type": "open road corridor", "lat": 35.0, "lon": -116.0},
]


def route_water_context(flight: dict[str, Any] | None, max_nm: float = 80.0) -> dict[str, Any] | None:
    if not flight:
        return None
    route = flight.get("planned_route_latlons", [])
    if not route:
        return None
    candidates = []
    for water in WATER_BODIES:
        nearest = min(_haversine_nm(point[0], point[1], water["lat"], water["lon"]) for point in route)
        if nearest <= max_nm:
            candidates.append({**water, "distance_nm": round(nearest, 1)})
    candidates.sort(key=lambda item: item["distance_nm"])
    return {
        "flight_id": flight["flight_id"],
        "nearby_water_bodies": candidates[:4],
        "note": "Route proximity is a coarse demo heuristic based on planned waypoints, not terrain analysis or landing guidance."
    }


def nearby_water_bodies(lat: float, lon: float, max_nm: float = 80.0) -> list[dict[str, Any]]:
    candidates = []
    for water in WATER_BODIES:
        distance = _haversine_nm(lat, lon, water["lat"], water["lon"])
        if distance <= max_nm:
            candidates.append({**water, "distance_nm": round(distance, 1)})
    return sorted(candidates, key=lambda item: item["distance_nm"])[:4]


def nearby_open_areas(lat: float, lon: float, max_nm: float = 120.0) -> list[dict[str, Any]]:
    candidates = []
    for area in OPEN_AREA_CANDIDATES:
        distance = _haversine_nm(lat, lon, area["lat"], area["lon"])
        if distance <= max_nm:
            candidates.append({**area, "distance_nm": round(distance, 1)})
    return sorted(candidates, key=lambda item: item["distance_nm"])[:4]


def format_water_context(context: dict[str, Any] | None) -> str:
    if not context or not context["nearby_water_bodies"]:
        return (
            "Route water-body context: no major demo water body is within the coarse route threshold. "
            "The system should prioritize suitable airport/diversion and corridor-clearing context rather than assuming a water option."
        )
    lines = [
        "Route water-body context: the planned route has coarse proximity to these water features. "
        "Surface them as situational context only, not as landing recommendations."
    ]
    for water in context["nearby_water_bodies"]:
        lines.append(f"- {water['name']} ({water['type']}), approx {water['distance_nm']} NM from a planned waypoint")
    return "\n".join(lines)


def haversine_nm(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius_nm = 3440.065
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return radius_nm * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _haversine_nm(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    return haversine_nm(lat1, lon1, lat2, lon2)
