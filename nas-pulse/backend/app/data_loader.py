from __future__ import annotations

import csv
import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any


APP_FILE = Path(__file__).resolve()
DATA_DIR = APP_FILE.parents[1] / "data"
APP_PARENTS = list(APP_FILE.parents)
PROJECT_ROOT = next((parent for parent in APP_PARENTS if (parent / "hackathon_data_bundle").exists()), APP_PARENTS[-1])
DEFAULT_BUNDLE_SNAPSHOT = "asked_at_2025-06-10T17:00:00Z/routes.json"

AIRLINE_NAMES = {
    "AAL": "American",
    "ASA": "Alaska",
    "DAL": "Delta",
    "FFT": "Frontier",
    "JBU": "JetBlue",
    "NKS": "Spirit",
    "RPA": "Republic",
    "SKW": "SkyWest",
    "SWA": "Southwest",
    "UAL": "United",
}


def _read_json(name: str) -> Any:
    with (DATA_DIR / name).open("r", encoding="utf-8") as f:
        return json.load(f)


def load_airports() -> list[dict[str, Any]]:
    with (DATA_DIR / "airports.csv").open("r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for row in rows:
        row["lat"] = float(row["lat"])
        row["lon"] = float(row["lon"])
        row["capacity_per_hour"] = int(row["capacity_per_hour"])
    return rows


def load_demo_flights() -> list[dict[str, Any]]:
    with (DATA_DIR / "flights.csv").open("r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for row in rows:
        row["planned_altitude"] = int(row["planned_altitude"])
        row["planned_speed"] = int(row["planned_speed"])
        row["passenger_count"] = int(row["passenger_count"])
        row["priority_score"] = float(row["priority_score"])
        row["planned_route_latlons"] = json.loads(row["planned_route_latlons"])
        row["is_airborne"] = _time_to_minutes(row["departure_time_utc"]) <= 14 * 60 + 30
        row["data_source"] = "nas_pulse_demo"
    return rows


def load_flights() -> list[dict[str, Any]]:
    demo = load_demo_flights()
    airports = load_airports()
    return demo + load_bundle_route_flights(
        tuple((a["airport_code"], a["name"], a["lat"], a["lon"], a["capacity_per_hour"]) for a in airports),
        frozenset(flight["flight_id"] for flight in demo),
    )


@lru_cache(maxsize=1)
def load_bundle_route_flights(
    airports: tuple[tuple[str, str, float, float, int], ...] | list[dict[str, Any]],
    existing_ids: frozenset[str] | set[str] = frozenset(),
) -> list[dict[str, Any]]:
    airport_rows = _normalize_airport_rows(airports)
    known_airports = {airport["airport_code"] for airport in airport_rows}
    bundle_dir = _bundle_dir()
    route_file = bundle_dir / os.getenv("BUNDLE_ROUTES_FILE", DEFAULT_BUNDLE_SNAPSHOT)
    if not route_file.exists():
        return []

    with route_file.open("r", encoding="utf-8") as f:
        snapshot = json.load(f)

    limit = int(os.getenv("BUNDLE_FLIGHT_LIMIT", "180"))
    flights = []
    used_ids = set(existing_ids)
    for idx, record in enumerate(snapshot.get("flights", [])):
        origin = _iata_from_icao(record.get("origin_airport_icao", ""))
        destination = _iata_from_icao(record.get("destination_airport_icao", ""))
        if origin not in known_airports or destination not in known_airports:
            continue
        if len(record.get("lats", [])) < 2 or len(record.get("lats", [])) != len(record.get("lons", [])):
            continue

        departure = _iso_time_hhmm(record["take_off_time"])
        arrival = _iso_time_hhmm(record["scheduled_landing_time"])
        if not _inside_demo_bundle_window(departure, arrival):
            continue

        flight_number = record["flight_number"].upper()
        flight_id = _unique_flight_id(flight_number, origin, destination, departure, used_ids)
        used_ids.add(flight_id)
        prefix = _airline_prefix(flight_number)
        route = [
            [round(float(lat), 4), round(float(lon), 4)]
            for lat, lon in zip(record["lats"], record["lons"])
        ]
        flights.append(
            {
                "flight_id": flight_id,
                "airline": AIRLINE_NAMES.get(prefix, prefix or "Bundle flight"),
                "origin": origin,
                "destination": destination,
                "departure_time_utc": departure,
                "arrival_time_utc": arrival,
                "aircraft_id": f"BUNDLE-{flight_id}-{idx}",
                "planned_altitude": int(record.get("cruise_altitude_ft") or 36000),
                "planned_speed": int(record.get("cruise_speed_kt") or 450),
                "passenger_count": _estimated_passenger_count(prefix),
                "priority_score": _priority_score(prefix, origin, destination),
                "planned_route_latlons": route,
                "is_airborne": bool(record.get("is_airborne")),
                "data_source": "hackathon_data_bundle",
                "route_snapshot_asked_at": snapshot.get("asked_at"),
                "route_unique_key": f"{flight_number}|{record['take_off_time']}|{record['origin_airport_icao']}",
                "data_note": "Route, times, altitude, speed, and airborne status come from hackathon_data_bundle; passenger count is demo-estimated.",
            }
        )
        if len(flights) >= limit:
            break
    return flights


def load_weather_cells() -> list[dict[str, Any]]:
    return _read_json("weather_cells.json")


def load_constraints() -> list[dict[str, Any]]:
    return _read_json("airspace_constraints.json")


def load_playbooks() -> list[dict[str, Any]]:
    return _read_json("playbooks.json")


def load_historical_cases() -> list[dict[str, Any]]:
    return _read_json("historical_cases.json")


@lru_cache(maxsize=1)
def load_scenario() -> dict[str, Any]:
    airports = load_airports()
    flights = load_demo_flights() + load_bundle_route_flights(
        tuple((a["airport_code"], a["name"], a["lat"], a["lon"], a["capacity_per_hour"]) for a in airports),
        frozenset(f["flight_id"] for f in load_demo_flights()),
    )
    return {
        "airports": airports,
        "flights": flights,
        "weather_cells": load_weather_cells(),
        "constraints": load_constraints(),
        "playbooks": load_playbooks(),
        "historical_cases": load_historical_cases(),
        "bundle_requirements": {
            "routes": "hackathon_data_bundle snapshots use ISO UTC times, ICAO airport codes, lats/lons arrays, cruise altitude, speed, and is_airborne.",
            "weather": "Weather strips are 256x358 NPZ matrices for refc and retop; demo uses simplified polygons derived from the Chicago corridor scenario.",
            "sectors": "Synthetic sectors are GeoJSON altitude-band polygons with capacity; demo uses simplified airspace constraints and airport capacities."
        }
    }


def get_flight(flight_id: str) -> dict[str, Any] | None:
    return next((f for f in load_flights() if f["flight_id"] == flight_id), None)


def _time_to_minutes(value: str) -> int:
    hh, mm = value.split(":")
    return int(hh) * 60 + int(mm)


def time_to_minutes(value: str) -> int:
    return _time_to_minutes(value)


def _bundle_dir() -> Path:
    configured = os.getenv("HACKATHON_DATA_BUNDLE_DIR")
    if configured:
        return Path(configured)
    return PROJECT_ROOT / "hackathon_data_bundle"


def _normalize_airport_rows(rows: tuple[tuple[str, str, float, float, int], ...] | list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not rows:
        return []
    first = rows[0]
    if isinstance(first, dict):
        return list(rows)  # type: ignore[arg-type]
    return [
        {
            "airport_code": code,
            "name": name,
            "lat": lat,
            "lon": lon,
            "capacity_per_hour": capacity,
        }
        for code, name, lat, lon, capacity in rows  # type: ignore[misc]
    ]


def _iata_from_icao(value: str) -> str:
    value = value.upper()
    return value[1:] if len(value) == 4 and value.startswith("K") else value


def _iso_time_hhmm(value: str) -> str:
    return value[11:16]


def _inside_demo_bundle_window(departure: str, arrival: str) -> bool:
    dep = _time_to_minutes(departure)
    arr = _time_to_minutes(arrival)
    return 15 * 60 <= dep <= 18 * 60 + 30 and arr >= dep


def _airline_prefix(flight_number: str) -> str:
    return "".join(ch for ch in flight_number if ch.isalpha())


def _unique_flight_id(flight_number: str, origin: str, destination: str, departure: str, used_ids: set[str]) -> str:
    if flight_number not in used_ids:
        return flight_number
    suffix = departure.replace(":", "")
    candidate = f"{flight_number}_{origin}{destination}_{suffix}"
    counter = 2
    while candidate in used_ids:
        candidate = f"{flight_number}_{origin}{destination}_{suffix}_{counter}"
        counter += 1
    return candidate


def _estimated_passenger_count(prefix: str) -> int:
    if prefix in {"EJA", "NJE", "VJA"}:
        return 8
    if prefix in {"RPA", "SKW", "EDV", "ENY"}:
        return 76
    if prefix in {"FDX", "UPS"}:
        return 0
    return 165


def _priority_score(prefix: str, origin: str, destination: str) -> float:
    hub_bonus = 0.08 if origin in {"JFK", "ORD", "ATL", "DFW", "DEN", "LAX", "SFO"} or destination in {"JFK", "ORD", "ATL", "DFW", "DEN", "LAX", "SFO"} else 0.0
    carrier_bonus = 0.06 if prefix in {"AAL", "DAL", "UAL", "SWA"} else 0.0
    return round(min(0.92, 0.58 + hub_bonus + carrier_bonus), 2)
