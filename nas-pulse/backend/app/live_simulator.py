from __future__ import annotations

from typing import Any

from .data_loader import time_to_minutes
from .emergency_geography import route_water_context


def build_live_flight_state(flight: dict[str, Any], scenario_time: str) -> dict[str, Any]:
    dep = time_to_minutes(flight["departure_time_utc"])
    arr = time_to_minutes(flight["arrival_time_utc"])
    now = time_to_minutes(scenario_time)
    duration = max(arr - dep, 1)
    progress = min(1.0, max(0.0, (now - dep) / duration))
    position = _interpolate_route(flight["planned_route_latlons"], progress)
    status = "scheduled"
    if dep <= now <= arr:
        status = "airborne"
    elif now > arr:
        status = "arrived"
    return {
        "flight_id": flight["flight_id"],
        "scenario_time": scenario_time,
        "status": status,
        "progress": round(progress, 3),
        "current_position": position,
        "minutes_since_departure": max(0, now - dep),
        "minutes_to_arrival": max(0, arr - now),
        "flight": flight,
        "water_context": route_water_context(flight),
    }


def _interpolate_route(route: list[list[float]], progress: float) -> list[float]:
    if not route:
        return [0, 0]
    if len(route) == 1:
        return route[0]
    scaled = progress * (len(route) - 1)
    idx = min(int(scaled), len(route) - 2)
    local = scaled - idx
    a = route[idx]
    b = route[idx + 1]
    return [
        round(a[0] + (b[0] - a[0]) * local, 4),
        round(a[1] + (b[1] - a[1]) * local, 4),
    ]
