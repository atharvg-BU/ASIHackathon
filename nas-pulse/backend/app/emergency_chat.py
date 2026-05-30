from __future__ import annotations

import re
from typing import Any

from .emergency_geography import format_water_context, route_water_context
from .flight_rag import build_flight_rag_context, llm_config_status, maybe_generate_llm_answer
from .historical_case_matcher import get_top_case_matches
from .incident_context import build_incident_context, format_incident_context
from .session_memory import format_session_summary


PROHIBITED_PHRASES = ("the pilot should", "pilots should", "cockpit instruction")


def generate_emergency_chat_response(
    message: str,
    scenario_time: str,
    selected_flight: dict[str, Any] | None,
    simulation: dict[str, Any],
    optimization: dict[str, Any],
    scenario_tags: list[str],
    airports: list[dict[str, Any]] | None = None,
    session_memory: dict[str, Any] | None = None,
    unknown_flight_id: str | None = None,
) -> dict[str, Any]:
    lower = message.lower()
    event_tags = extract_message_tags(message)
    if session_memory and session_memory.get("event_type") == "bird_strike" and "bird_strike" not in event_tags:
        event_tags.append("bird_strike")
    if session_memory and session_memory.get("fuel_status") == "insufficient" and "insufficient_fuel" not in event_tags:
        event_tags.extend(["fuel_emergency", "insufficient_fuel", "diversion", "emergency_landing"])
        event_tags = sorted(set(event_tags))
    if _is_greeting(message):
        response = _flow_explanation(selected_flight)
        return {
            "intent": "greeting",
            "response": response,
            "historical_matches": [],
            "recommended_actions": [],
            "message_tags": [],
            "effective_scenario_tags": [],
            "route_water_context": None,
            "rag_context": {"query": message, "chunks": []},
            "llm_used": False,
            "llm_status": {**llm_config_status(), "used": False, "reason": "greeting handled locally"},
            "focused_flight_id": selected_flight["flight_id"] if selected_flight else None,
            "unknown_flight_id": None,
            "disclaimer": "Demo only - not for operational aviation use."
        }

    if event_tags:
        effective_tags = sorted(set(event_tags))
    else:
        effective_tags = sorted(set(scenario_tags or simulation.get("scenario_tags", [])))
    matches = get_top_case_matches({"scenario_tags": effective_tags}, k=3)

    if unknown_flight_id:
        response = _unknown_flight_response(unknown_flight_id, event_tags, matches, simulation)
        return {
            "intent": "unknown_flight",
            "response": response,
            "historical_matches": matches,
            "recommended_actions": [],
            "message_tags": event_tags,
            "effective_scenario_tags": effective_tags,
            "route_water_context": None,
            "rag_context": {"query": message, "chunks": []},
            "llm_used": False,
            "llm_status": {**llm_config_status(), "used": False, "reason": "unknown flight handled locally"},
            "focused_flight_id": None,
            "unknown_flight_id": unknown_flight_id,
            "disclaimer": "Demo only - not for operational aviation use."
        }

    actions = optimization.get("recommended_actions", [])
    relevant_actions = _relevant_actions(actions, selected_flight)
    water_context = route_water_context(selected_flight)
    incident_context = build_incident_context(message, selected_flight, airports or [], scenario_time)
    if incident_context and session_memory and session_memory.get("fuel_minutes"):
        incident_context["fuel_minutes"] = session_memory["fuel_minutes"]
    emergency_actions = _emergency_actions(event_tags, selected_flight, water_context, incident_context)
    rag_context = build_flight_rag_context(message, selected_flight, simulation, optimization, matches, emergency_actions, incident_context, session_memory)

    if any(token in lower for token in ["emergency", "urgent", "help", "failure", "fuel", "engine", "bird"]):
        intent = "emergency_triage"
        lead = _emergency_lead(event_tags)
    elif any(token in lower for token in ["history", "similar", "case", "happened"]):
        intent = "historical_analogy"
        lead = "Historical memory found the closest demo analogies below. Use them for explanation and playbook framing only."
    elif any(token in lower for token in ["option", "recommend", "best", "action", "reroute", "hold"]):
        intent = "best_options"
        lead = "Best current options are ranked by expected system delay reduction and downstream impact."
    else:
        intent = "situation_summary"
        lead = "Current NAS Pulse view combines weather, airspace capacity, aircraft reuse, and arrival-bank congestion."

    selected_summary = _flight_summary(selected_flight)
    action_set = emergency_actions if event_tags else emergency_actions + (relevant_actions or actions[:3])
    best_options = _format_actions(action_set)
    case_summary = _format_cases(matches)
    route_context = format_water_context(water_context)
    incident_summary = format_incident_context(incident_context)
    network = (
        f"At {scenario_time} UTC, simulation shows {simulation['direct_impact_count']} direct impacts, "
        f"{simulation['indirect_impact_count']} indirect impacts, and "
        f"{simulation['total_predicted_delay_before_optimization']} predicted delay minutes before optimization."
    )

    response = _conversation_response(
        message=message,
        lead=lead,
        network=network,
        selected_summary=selected_summary,
        route_context=route_context,
        action_set=action_set,
        matches=matches,
        best_options=best_options,
        case_summary=case_summary,
        incident_summary=incident_summary,
        session_memory=session_memory,
    )

    local_guardrail_reason = _local_guardrail_reason(message, event_tags, session_memory)
    if local_guardrail_reason:
        llm_response = None
        llm_status = {**llm_config_status(), "used": False, "reason": local_guardrail_reason}
    else:
        llm_response, llm_status = maybe_generate_llm_answer(message, rag_context)
    if llm_response:
        response = llm_response

    for phrase in PROHIBITED_PHRASES:
        response = response.replace(phrase, "the system should")

    return {
        "intent": intent,
        "response": response,
        "historical_matches": matches,
        "recommended_actions": action_set[:5],
        "message_tags": event_tags,
        "effective_scenario_tags": effective_tags,
        "route_water_context": water_context,
        "incident_context": incident_context,
        "rag_context": rag_context,
        "llm_used": bool(llm_response),
        "llm_status": llm_status,
        "focused_flight_id": selected_flight["flight_id"] if selected_flight else None,
        "session_memory": session_memory or {},
        "unknown_flight_id": None,
        "disclaimer": "Demo only - not for operational aviation use."
    }


def extract_candidate_flight_id(message: str) -> str | None:
    matches = sorted(set(re.findall(r"\b[A-Z]{2,4}\d{2,4}\b", message.upper())))
    return matches[0] if matches else None


def extract_flight_id(message: str, known_flight_ids: set[str]) -> str | None:
    tokens = set(re.findall(r"\b[A-Z]{2,4}\d{2,4}\b", message.upper()))
    matches = sorted(tokens & known_flight_ids)
    return matches[0] if matches else None


def extract_message_tags(message: str) -> list[str]:
    lower = message.lower()
    tags = set()
    if "bird" in lower or "strike" in lower:
        tags.update(["bird_strike", "departure_phase", "time_critical_decision", "emergency_landing"])
    if "engine" in lower:
        tags.update(["engine_failure", "emergency_landing", "priority_handling"])
    if "fuel" in lower:
        tags.update(["fuel_emergency", "diversion", "emergency_landing"])
    if any(phrase in lower for phrase in ["fuel wont", "fuel won't", "fuel will not", "not enough fuel", "insufficient fuel", "fuel low", "no fuel", "no fuell"]):
        tags.update(["fuel_emergency", "insufficient_fuel", "diversion", "emergency_landing"])
    if "water" in lower or "river" in lower or "ditch" in lower:
        tags.update(["water_ditching", "emergency_landing"])
    if any(word in lower for word in ["emergency", "urgent", "mayday"]):
        tags.update(["priority_handling", "time_critical_decision"])
    return sorted(tags)


def _is_greeting(message: str) -> bool:
    normalized = re.sub(r"[^a-z\s]", "", message.lower()).strip()
    return normalized in {"hi", "hello", "hey", "yo", "hiya", "howdy", "good morning", "good afternoon", "good evening"}


def _flow_explanation(selected_flight: dict[str, Any] | None) -> str:
    focus = selected_flight["flight_id"] if selected_flight else "the focused flight"
    return (
        f"Hi. I’m the NAS Pulse emergency support chat, currently focused on {focus}.\n\n"
        "Here’s how information flows when you ask me something:\n"
        "1. I read your message for a flight ID and event type, like bird strike, fuel emergency, engine issue, reroute, or historical case.\n"
        "2. I retrieve the focused flight context: route, current simulated position, risk scores, water-body proximity, and network delay state.\n"
        "3. I compare the event tags against Historical Case Memory, then pull the closest cases and their lessons.\n"
        "4. I combine that with optimizer or emergency playbook options and explain the best high-level choice with reasons.\n\n"
        "You can try: `flag UAL777 bird strike`, `what is the best option for UAL777?`, or `what historical case is closest?`\n\n"
        "Demo only - not for operational aviation use."
    )


def _selected_flight_tags(flight: dict[str, Any] | None) -> list[str]:
    if not flight:
        return []
    tags = set()
    if flight.get("weather_risk", 0) > 0:
        tags.update(["weather_hazard", "convective_weather"])
    if flight.get("airspace_risk", 0) > 0:
        tags.add("airspace_constraint")
    if flight.get("delay_propagation_risk", 0) > 0.5:
        tags.add("delay_cascade")
    return sorted(tags)


def _unknown_flight_response(
    unknown_flight_id: str,
    event_tags: list[str],
    matches: list[dict[str, Any]],
    simulation: dict[str, Any],
) -> str:
    known_ids = sorted(f["flight_id"] for f in simulation.get("scored_flights", []))
    prefix = "".join(ch for ch in unknown_flight_id if ch.isalpha())
    suggestions = [flight_id for flight_id in known_ids if flight_id.startswith(prefix)][:6]
    suggestion_text = ", ".join(suggestions) if suggestions else ", ".join(known_ids[:6])
    case_summary = _format_cases(matches[:2])
    event_text = "bird-strike/emergency" if "bird_strike" in event_tags else "emergency"
    return (
        f"I could not find flight {unknown_flight_id} in the loaded NAS Pulse demo flight set, so I will not reuse another flight's route, "
        f"risk score, water-body context, or intervention plan for this {event_text} report.\n\n"
        f"Closest available flight IDs in this dataset: {suggestion_text}.\n\n"
        f"Historical memory for the reported event type, without flight-specific route context:\n{case_summary}\n\n"
        "Guardrail: historical analogy only - not operational aviation guidance. Select or type a valid loaded flight ID to retrieve flight-specific options."
    )


def _conversation_response(
    message: str,
    lead: str,
    network: str,
    selected_summary: str,
    route_context: str,
    action_set: list[dict[str, Any]],
    matches: list[dict[str, Any]],
    best_options: str,
    case_summary: str,
    incident_summary: str,
    session_memory: dict[str, Any] | None,
) -> str:
    best = _best_choice(action_set)
    best_label = _action_label(best["action_type"]) if best else "Run optimizer"
    nearest = _nearest_from_incident_summary(incident_summary)
    alternatives = _format_alternatives(action_set)
    water = _water_from_incident_summary(incident_summary)
    open_area = _open_area_from_incident_summary(incident_summary)
    last_resort_case = _last_resort_case_line(matches)

    if _asks_about_water(message):
        return (
            "I can’t recommend a water landing. In this demo, water is last-resort situational context only.\n\n"
            f"Nearest airports: {nearest}.\n\n"
            "If fuel/endurance cannot reach any airport, keep Traffic Conflict Scan active and surface non-airport context for awareness only:\n"
            f"Water nearby: {water.rstrip('.')}.\n"
            f"Open/road area nearby: {open_area.rstrip('.')}.\n"
            f"{last_resort_case}\n\n"
            "I need exact endurance, altitude, glide/performance state, and terrain/obstacle data before narrowing this further.\n\n"
            "Demo only - not for operational aviation use."
        )

    if best and best["action_type"] == "FUEL_ALTERNATE_REVIEW":
        fuel_minutes = _extract_fuel_minutes(best)
        reachable = _reachable_airports(best, fuel_minutes)
        if fuel_minutes and not reachable:
            return (
                f"Got it: about {fuel_minutes} minutes of fuel/endurance.\n\n"
                f"Nearest airports: {nearest}.\n"
                "In this demo estimate, none of those look reachable inside that window.\n\n"
                "Next best path: keep Traffic Conflict Scan active, then surface last-resort area awareness.\n"
                f"Water nearby: {water.rstrip('.')}.\n"
                f"Open/road area nearby: {open_area.rstrip('.')}.\n"
                f"{last_resort_case}\n\n"
                "I still need exact endurance, altitude, glide/performance state, and terrain/obstacle data before narrowing this further.\n\n"
                "Demo only - not for operational aviation use."
            )
        return (
            "Understood. I’m treating fuel/endurance as insufficient or unknown, so I won’t pick an airport just because it is closest.\n\n"
            f"Nearest airports: {nearest}.\n\n"
            "Best next step: Fuel-Constrained Alternate Review.\n"
            "Give exact usable endurance/fuel minutes so the system can filter which airports are actually reachable.\n\n"
            "Decision flow:\n"
            "1. Remove airports outside the fuel/endurance window.\n"
            "2. Compare remaining alternates by distance, congestion, and corridor constraints.\n"
            "3. Keep traffic-conflict scanning active around the incident point.\n"
            f"4. If no airport is reachable, surface last-resort context only: water - {water.rstrip('.')}; open/road area - {open_area.rstrip('.')}.\n\n"
            f"Alternatives: {alternatives}.\n\n"
            "Demo only - not for operational aviation use."
        )

    return (
        "Got it. I’ll keep this focused.\n\n"
        f"Nearest airports I see: {nearest}.\n\n"
        f"Best first step: {best_label}.\n"
        "Before picking a return or diversion path, I need fuel/endurance from the crew/dispatcher context.\n\n"
        "Decision flow:\n"
        "1. If fuel/endurance supports it, evaluate heading back toward the nearest suitable departure-side airport.\n"
        "2. If not, compare the closest alternates by distance, congestion, and corridor constraints.\n"
        "3. Keep a traffic-conflict scan active around the incident point while the airport choice is being reviewed.\n\n"
        f"Alternatives: {alternatives}.\n\n"
        "Demo only - not for operational aviation use."
    )


def _nearest_from_incident_summary(summary: str) -> str:
    marker = "Nearest demo airports:"
    if marker not in summary:
        return "nearest airport data unavailable"
    tail = summary.split(marker, 1)[1]
    return tail.split(". Nearby water context:", 1)[0].strip()


def _water_from_incident_summary(summary: str) -> str:
    marker = "Nearby water context:"
    if marker not in summary:
        return "no nearby water-body context available"
    return summary.split(marker, 1)[1].split(". Open-area context:", 1)[0].strip()


def _open_area_from_incident_summary(summary: str) -> str:
    marker = "Open-area context:"
    if marker not in summary:
        return "no open-area context available"
    return summary.split(marker, 1)[1].strip()


def _asks_about_water(message: str) -> bool:
    lower = message.lower()
    return "water" in lower or "river" in lower or "ditch" in lower


def _local_guardrail_reason(
    message: str,
    event_tags: list[str],
    session_memory: dict[str, Any] | None,
) -> str | None:
    if _asks_about_water(message):
        return "local guardrail: water landing question"
    if "insufficient_fuel" in event_tags:
        return "local guardrail: insufficient fuel requires range filtering"
    if session_memory and session_memory.get("fuel_status") == "insufficient":
        return "local guardrail: insufficient fuel requires range filtering"
    return None


def _format_alternatives(actions: list[dict[str, Any]]) -> str:
    labels = [_action_label(action["action_type"]) for action in actions[:4]]
    return ", ".join(labels) if labels else "none ranked yet"


def _extract_fuel_minutes(action: dict[str, Any]) -> int | None:
    return action.get("fuel_minutes")


def _reachable_airports(action: dict[str, Any], fuel_minutes: int | None) -> list[dict[str, Any]]:
    if not fuel_minutes:
        return action.get("nearest_airports", [])
    speed_kt = action.get("planned_speed", 450)
    range_nm = speed_kt * fuel_minutes / 60
    return [airport for airport in action.get("nearest_airports", []) if airport["distance_nm"] <= range_nm]


def _last_resort_case_line(matches: list[dict[str, Any]]) -> str:
    for match in matches:
        if match.get("case_id") == "OPEN_AREA_ROAD_FORCED_LANDING_PATTERN":
            return f"Historical pattern: {match['case_name']} - open/road areas are last-resort context only."
    return "Historical pattern: road/open-area forced-landing analogies are last-resort context only."


def _best_choice(actions: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not actions:
        return None
    priority = {
        "FUEL_ALTERNATE_REVIEW": 0,
        "NEAREST_AIRPORT_REVIEW": 0,
        "TRAFFIC_CONFLICT_SCAN": 1,
        "AIRPORT_READINESS_ALERT": 2,
        "PROTECTED_CORRIDOR_REVIEW": 3,
        "WATER_BODY_CONTEXT": 4,
    }
    return sorted(actions, key=lambda action: priority.get(action["action_type"], 10))[0]


def _action_label(action_type: str) -> str:
    labels = {
        "TRAFFIC_CONFLICT_SCAN": "Traffic Conflict Scan",
        "FUEL_ALTERNATE_REVIEW": "Fuel-Constrained Alternate Review",
        "NEAREST_AIRPORT_REVIEW": "Nearest Suitable Airport Review",
        "AIRPORT_READINESS_ALERT": "Airport Readiness Alert",
        "PROTECTED_CORRIDOR_REVIEW": "Protected Corridor Review",
        "WATER_BODY_CONTEXT": "Water-Body Context",
    }
    return labels.get(action_type, action_type.replace("_", " ").title())


def _emergency_lead(event_tags: list[str]) -> str:
    if "bird_strike" in event_tags:
        return (
            "Bird-strike emergency-support view: keep this as dispatch-level decision support. "
            "The system should prioritize nearest suitable diversion awareness, protected corridor options, "
            "airport readiness coordination, and traffic deconfliction around the affected route."
        )
    return (
        "Emergency-support view: keep this as dispatch-level decision support. "
        "The system should prioritize stabilizing network demand, identifying reachable alternates or protected corridors, "
        "and reducing conflicting traffic around the affected route."
    )


def _relevant_actions(actions: list[dict[str, Any]], selected_flight: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not selected_flight:
        return actions[:3]
    matches = [a for a in actions if a["flight_id"] == selected_flight["flight_id"]]
    return matches or actions[:3]


def _emergency_actions(
    event_tags: list[str],
    selected_flight: dict[str, Any] | None,
    water_context: dict[str, Any] | None,
    incident_context: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    if not selected_flight or not event_tags:
        return []
    flight_id = selected_flight["flight_id"]
    nearest = (incident_context or {}).get("nearest_airports", [])
    nearest_text = ", ".join(f"{a['airport_code']} ({a['distance_nm']} NM)" for a in nearest[:3]) or "nearest demo airports"
    incident_label = (incident_context or {}).get("label", "the estimated incident point")
    actions = []
    if "fuel_emergency" in event_tags or "insufficient_fuel" in event_tags:
        fuel_minutes = (incident_context or {}).get("fuel_minutes") or None
        actions.extend(
            [
                {
                    "flight_id": flight_id,
                    "action_type": "FUEL_ALTERNATE_REVIEW",
                    "expected_delay_reduction_minutes": 0,
                    "nearest_airports": nearest,
                    "planned_speed": selected_flight.get("planned_speed", 450),
                    "fuel_minutes": (incident_context or {}).get("fuel_minutes"),
                    "explanation": (
                        f"Filter {nearest_text} by the available fuel/endurance window first; if return is not feasible, rank the closest suitable alternates."
                    )
                },
                {
                    "flight_id": flight_id,
                    "action_type": "TRAFFIC_CONFLICT_SCAN",
                    "expected_delay_reduction_minutes": 0,
                    "explanation": (
                        f"Scan traffic around {incident_label} so the selected alternate path can be protected from added conflicts."
                    )
                },
                {
                    "flight_id": flight_id,
                    "action_type": "AIRPORT_READINESS_ALERT",
                    "expected_delay_reduction_minutes": 0,
                    "explanation": (
                        f"Prepare the candidate receiving-airport context for {nearest_text} and monitor runway/arrival-bank congestion."
                    )
                },
            ]
        )
    if "bird_strike" in event_tags:
        actions.extend(
            [
                {
                    "flight_id": flight_id,
                    "action_type": "NEAREST_AIRPORT_REVIEW",
                    "expected_delay_reduction_minutes": 0,
                    "explanation": (
                        f"Start by comparing {nearest_text} because the incident point is {incident_label}; proximity and airport/corridor constraints matter more than normal delay optimization."
                    )
                },
                {
                    "flight_id": flight_id,
                    "action_type": "TRAFFIC_CONFLICT_SCAN",
                    "expected_delay_reduction_minutes": 0,
                    "explanation": (
                        f"At the same time, scan traffic around {incident_label} and reduce conflicts so controllers have a cleaner path "
                        "for whichever airport review outcome is selected."
                    )
                },
                {
                    "flight_id": flight_id,
                    "action_type": "AIRPORT_READINESS_ALERT",
                    "expected_delay_reduction_minutes": 0,
                    "explanation": (
                        f"Prepare the candidate receiving-airport context for {nearest_text} and monitor runway/arrival-bank congestion."
                    )
                },
                {
                    "flight_id": flight_id,
                    "action_type": "PROTECTED_CORRIDOR_REVIEW",
                    "expected_delay_reduction_minutes": 0,
                    "explanation": (
                        "Review a simplified protected corridor around the affected route so other network interventions do not add conflicts."
                    )
                },
            ]
        )
        if water_context and water_context["nearby_water_bodies"]:
            actions.append(
                {
                    "flight_id": flight_id,
                    "action_type": "WATER_BODY_CONTEXT",
                    "expected_delay_reduction_minutes": 0,
                    "explanation": "Show nearby water features as historical analogy context only, not as landing recommendations."
                }
            )
    return actions


def _flight_summary(flight: dict[str, Any] | None) -> str:
    if not flight:
        return "No specific flight is selected. Recommendations are network-level."
    return (
        f"Selected flight {flight['flight_id']} runs {flight['origin']}-{flight['destination']} with "
        f"{flight.get('risk_level', 'unknown')} risk, weather risk {flight.get('weather_risk', 0)}, "
        f"airspace risk {flight.get('airspace_risk', 0)}, and propagation risk {flight.get('delay_propagation_risk', 0)}."
    )


def _format_actions(actions: list[dict[str, Any]]) -> str:
    if not actions:
        return "- No intervention is currently ranked. Run the optimizer for action options."
    lines = []
    for action in actions[:4]:
        delay = action.get("expected_delay_reduction_minutes", 0)
        impact = f"{delay} min expected delay reduction" if delay else "emergency support"
        lines.append(
            f"- {action['flight_id']}: {_action_label(action['action_type'])} "
            f"({impact}). {action['explanation']}"
        )
    return "\n".join(lines)


def _format_cases(matches: list[dict[str, Any]]) -> str:
    if not matches:
        return "- No historical case match available."
    lines = []
    for match in matches[:3]:
        tags = ", ".join(match["matched_tags"]) or "pattern-level match"
        lines.append(
            f"- {match['case_name']} ({round(match['similarity_score'] * 100)}%): "
            f"{match['system_lesson']} Matched tags: {tags}."
        )
    return "\n".join(lines)
