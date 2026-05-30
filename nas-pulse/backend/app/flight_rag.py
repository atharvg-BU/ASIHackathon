from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from typing import Any

from .emergency_geography import format_water_context, route_water_context


def build_flight_rag_context(
    message: str,
    selected_flight: dict[str, Any] | None,
    simulation: dict[str, Any],
    optimization: dict[str, Any],
    matches: list[dict[str, Any]],
    emergency_actions: list[dict[str, Any]],
    incident_context: dict[str, Any] | None = None,
    session_memory: dict[str, Any] | None = None,
) -> dict[str, Any]:
    chunks = []
    if session_memory:
        chunks.append(
            {
                "id": "session:memory",
                "title": "Current chat session memory",
                "text": json.dumps(session_memory, ensure_ascii=True),
            }
        )
    if selected_flight:
        chunks.append(
            {
                "id": f"flight:{selected_flight['flight_id']}",
                "title": f"{selected_flight['flight_id']} flight profile",
                "text": (
                    f"{selected_flight['flight_id']} operates {selected_flight['origin']} to {selected_flight['destination']} "
                    f"departing {selected_flight['departure_time_utc']} UTC and arriving {selected_flight['arrival_time_utc']} UTC. "
                    f"Aircraft {selected_flight['aircraft_id']}, altitude {selected_flight['planned_altitude']} ft, "
                    f"speed {selected_flight['planned_speed']} kt, passengers {selected_flight['passenger_count']}."
                ),
            }
        )
        chunks.append(
            {
                "id": f"risk:{selected_flight['flight_id']}",
                "title": f"{selected_flight['flight_id']} computed risk",
                "text": (
                    f"Risk level {selected_flight.get('risk_level')}, total risk {selected_flight.get('total_risk')}, "
                    f"weather risk {selected_flight.get('weather_risk')}, airspace risk {selected_flight.get('airspace_risk')}, "
                    f"airport congestion risk {selected_flight.get('airport_congestion_risk')}, "
                    f"delay propagation risk {selected_flight.get('delay_propagation_risk')}."
                ),
            }
        )
        chunks.append(
            {
                "id": f"route:{selected_flight['flight_id']}",
                "title": f"{selected_flight['flight_id']} route and water context",
                "text": format_water_context(route_water_context(selected_flight)),
            }
        )
    if incident_context:
        nearest = ", ".join(
            f"{item['airport_code']} {item['distance_nm']} NM" for item in incident_context["nearest_airports"][:4]
        )
        water = ", ".join(
            f"{item['name']} {item['distance_nm']} NM" for item in incident_context["nearby_water_bodies"][:4]
        ) or "none nearby in demo set"
        open_areas = ", ".join(
            f"{item['name']} {item['distance_nm']} NM" for item in incident_context.get("nearby_open_areas", [])[:4]
        ) or "none nearby in demo set"
        chunks.append(
            {
                "id": "incident:location",
                "title": "Incident location context",
                "text": (
                    f"Incident location source {incident_context['source']}: {incident_context['label']} at "
                    f"{incident_context['lat']}, {incident_context['lon']}. Route phase: {incident_context['route_phase']}. "
                    f"Nearest demo airports: {nearest}. Nearby water context: {water}. "
                    f"Open-area context: {open_areas}. "
                    "This is situational context only, not landing guidance."
                ),
            }
        )

    chunks.append(
        {
            "id": "network:simulation",
            "title": "Network simulation state",
            "text": (
                f"Simulation has {simulation['direct_impact_count']} direct impacts, "
                f"{simulation['indirect_impact_count']} indirect impacts, and "
                f"{simulation['total_predicted_delay_before_optimization']} predicted delay minutes before optimization."
            ),
        }
    )

    for idx, action in enumerate(emergency_actions + optimization.get("recommended_actions", [])[:4]):
        chunks.append(
            {
                "id": f"action:{idx}",
                "title": f"Action option {idx + 1}",
                "text": (
                    f"{action['flight_id']} {action['action_type']}: "
                    f"{action.get('explanation', '')} Expected delay reduction "
                    f"{action.get('expected_delay_reduction_minutes', 0)} minutes."
                ),
            }
        )

    for match in matches:
        chunks.append(
            {
                "id": f"case:{match['case_id']}",
                "title": match["case_name"],
                "text": (
                    f"Similarity {match['similarity_score']}. Matched tags: {', '.join(match['matched_tags'])}. "
                    f"What happened: {match['situation_summary']} System lesson: {match['system_lesson']}"
                ),
            }
        )

    return {"query": message, "chunks": chunks[:12]}


def llm_config_status() -> dict[str, Any]:
    enabled = os.getenv("USE_LLM_CHAT", "").lower() in {"1", "true", "yes"}
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    return {
        "enabled": enabled,
        "provider": "anthropic",
        "model": os.getenv("ANTHROPIC_MODEL", "claude-opus-4-1-20250805"),
        "api_key_present": bool(api_key),
        "api_key_preview": f"{api_key[:10]}...{api_key[-4:]}" if len(api_key) > 16 else "",
    }


def maybe_generate_llm_answer(message: str, context: dict[str, Any]) -> tuple[str | None, dict[str, Any]]:
    status = llm_config_status()
    if os.getenv("USE_LLM_CHAT", "").lower() not in {"1", "true", "yes"}:
        return None, {**status, "used": False, "reason": "USE_LLM_CHAT is not enabled"}
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return None, {**status, "used": False, "reason": "ANTHROPIC_API_KEY is missing"}

    prompt = (
        "You are NAS Pulse, a calm conversational emergency support copilot for airspace controllers in a hackathon demo. "
        "Use only the retrieved context. Your job is to reason out loud at a high level, choose the best system-level option, "
        "and explain why it is preferred over the alternatives. Be concise, human, and reassuring.\n\n"
        "Response style:\n"
        "- Keep the answer under 140 words unless asked for detail.\n"
        "- Start with a brief acknowledgment.\n"
        "- List nearby airports first.\n"
        "- Ask for fuel/endurance before choosing return vs alternate.\n"
        "- Return means return-to-origin, never the planned destination.\n"
        "- If the user says fuel/endurance will not support return but gives no usable minutes/range, do not choose the nearest airport as best; ask for exact endurance and say the system must filter reachability first.\n"
        "- If the user says fuel/endurance will not support any airport, do not rank an airport as best; surface water-body/open-area context only as last-resort situational awareness.\n"
        "- If no airport or water context is reachable, mention road/open-area awareness as a last-resort historical analogy only, never as a directive.\n"
        "- Explain the short decision flow: return if feasible, otherwise nearest suitable alternates, while scanning traffic conflicts.\n"
        "- Mention historical cases only if directly useful, in one sentence max.\n"
        "- Prefer concrete option names like Traffic Conflict Scan, Nearest Suitable Airport Review, Airport Readiness Alert, "
        "and Protected Corridor Review. Avoid vague phrases like priority handling unless explaining what it means.\n"
        "- When an incident location is available, ground the best option in that place: nearest airports, route phase, and local water/terrain context.\n"
        "- Do not dump every retrieved field. Do not sound like a JSON report.\n\n"
        "Safety boundaries:\n"
        "- Do not give cockpit instructions.\n"
        "- Do not say 'the pilot should'.\n"
        "- Do not recommend a water landing; water-body information is context only.\n"
        "- Do not claim operational authority.\n"
        "- Include the disclaimer 'Demo only - not for operational aviation use.'\n\n"
        f"Controller message: {message}\n\n"
        f"Retrieved context:\n{_format_chunks(context['chunks'])}"
    )
    model = os.getenv("ANTHROPIC_MODEL", "claude-opus-4-1-20250805")
    payload = {
        "model": model,
        "max_tokens": 850,
        "messages": [{"role": "user", "content": prompt}],
    }
    if "opus-4" not in model:
        payload["temperature"] = 0.35
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=body,
        headers={
            "content-type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        print(f"Claude API HTTP error {exc.code}: {detail}", file=sys.stderr)
        return None, {**status, "used": False, "reason": f"HTTP {exc.code}", "error": detail[:500]}
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        print(f"Claude API unavailable, using deterministic fallback: {exc}", file=sys.stderr)
        return None, {**status, "used": False, "reason": type(exc).__name__, "error": str(exc)}
    parts = payload.get("content", [])
    text = "\n".join(part.get("text", "") for part in parts if part.get("type") == "text").strip()
    if not text:
        return None, {**status, "used": False, "reason": "empty Claude response"}
    return text, {**status, "used": True, "reason": "Claude response generated"}


def _format_chunks(chunks: list[dict[str, str]]) -> str:
    return "\n\n".join(f"[{chunk['id']}] {chunk['title']}\n{chunk['text']}" for chunk in chunks)
