from __future__ import annotations


def build_trajectory_options(flight: dict) -> list[dict]:
    risk = flight.get("risk_level", "low")
    keep_delay = 55 if risk == "severe" else 35 if risk == "high" else 15
    return [
        {
            "flight_id": flight["flight_id"],
            "label": "Option A",
            "action_type": "KEEP_PLANNED_ROUTE",
            "expected_delay_minutes": keep_delay,
            "fuel_impact": "low",
            "residual_risk": risk,
            "explanation": "Baseline counterfactual with no intervention."
        },
        {
            "flight_id": flight["flight_id"],
            "label": "Option B",
            "action_type": "REROUTE_NORTH",
            "expected_delay_minutes": 18 if risk in {"high", "severe"} else 8,
            "fuel_impact": "medium",
            "residual_risk": "medium" if risk == "severe" else "low",
            "optimized_route_latlons": _north_route(flight["planned_route_latlons"]),
            "explanation": "Move traffic above the Chicago constraint through a northern corridor."
        },
        {
            "flight_id": flight["flight_id"],
            "label": "Option C",
            "action_type": "GROUND_HOLD",
            "expected_delay_minutes": 24 if not flight.get("is_airborne") else 32,
            "fuel_impact": "low",
            "residual_risk": "medium" if risk in {"high", "severe"} else "low",
            "explanation": "Absorb demand at the origin to reduce airborne holding and arrival bunching."
        },
    ]


def _north_route(route: list[list[float]]) -> list[list[float]]:
    if len(route) < 3:
        return route
    start, end = route[0], route[-1]
    mid_lon = (start[1] + end[1]) / 2
    return [start, [45.2, mid_lon], end]
