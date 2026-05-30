from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .briefing_generator import generate_briefing
from .cascade_simulator import simulate_delay_cascade
from .data_loader import get_flight, load_scenario
from .emergency_chat import extract_candidate_flight_id, extract_flight_id, generate_emergency_chat_response
from .flight_rag import llm_config_status
from .historical_case_matcher import extract_scenario_tags, get_top_case_matches
from .live_simulator import build_live_flight_state
from .models import BriefingRequest, CaseMatchRequest, EmergencyChatRequest, OptimizeRequest, SimulateRequest
from .optimizer import optimize_interventions
from .risk_engine import score_flights
from .session_memory import summarize_session


app = FastAPI(title="NAS Pulse API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "mode": "demo", "disclaimer": "Demo only - not for operational aviation use."}


@app.get("/api/llm-status")
def llm_status() -> dict:
    return llm_config_status()


@app.get("/api/scenario")
def scenario() -> dict:
    data = load_scenario()
    return {**data, "disclaimer": "Demo only - not for operational aviation use."}


@app.get("/api/flights")
def flights(scenario_time: str = "14:30") -> list[dict]:
    data = load_scenario()
    return score_flights(data["flights"], data["airports"], data["weather_cells"], data["constraints"], scenario_time)


@app.get("/api/flights/{flight_id}")
def flight_detail(flight_id: str, scenario_time: str = "14:30") -> dict:
    data = load_scenario()
    scored = score_flights(data["flights"], data["airports"], data["weather_cells"], data["constraints"], scenario_time)
    flight = next((f for f in scored if f["flight_id"] == flight_id), None)
    if not flight:
        raise HTTPException(status_code=404, detail="Flight not found")
    return flight


@app.get("/api/live-flight/{flight_id}")
def live_flight(flight_id: str, scenario_time: str = "15:10") -> dict:
    data = load_scenario()
    scored = score_flights(data["flights"], data["airports"], data["weather_cells"], data["constraints"], scenario_time)
    flight = next((f for f in scored if f["flight_id"] == flight_id), None)
    if not flight:
        raise HTTPException(status_code=404, detail="Flight not found")
    return build_live_flight_state(flight, scenario_time)


@app.post("/api/simulate")
def simulate(req: SimulateRequest) -> dict:
    data = load_scenario()
    return simulate_delay_cascade(
        data["flights"],
        data["airports"],
        data["weather_cells"],
        data["constraints"],
        req.scenario_time,
        req.enabled_weather_ids,
        req.enabled_constraint_ids,
    )


@app.post("/api/optimize")
def optimize(req: OptimizeRequest) -> dict:
    data = load_scenario()
    return optimize_interventions(
        data["flights"],
        data["airports"],
        data["weather_cells"],
        data["constraints"],
        req.scenario_time,
        req.max_interventions,
    )


@app.post("/api/briefing")
def briefing(req: BriefingRequest) -> dict:
    data = load_scenario()
    simulation = simulate_delay_cascade(
        data["flights"],
        data["airports"],
        data["weather_cells"],
        data["constraints"],
        req.scenario_time,
        [w["id"] for w in data["weather_cells"]],
        [c["id"] for c in data["constraints"]],
    )
    optimization = optimize_interventions(
        data["flights"],
        data["airports"],
        data["weather_cells"],
        data["constraints"],
        req.scenario_time,
        20,
    )
    return generate_briefing(req.scenario_time, simulation, optimization, req.selected_flight_id)


@app.post("/api/case-matches")
def case_matches(req: CaseMatchRequest) -> dict:
    data = load_scenario()
    selected = get_flight(req.selected_flight_id) if req.selected_flight_id else None
    if req.scenario_tags:
        tags = req.scenario_tags
    else:
        simulation = simulate_delay_cascade(
            data["flights"],
            data["airports"],
            data["weather_cells"],
            data["constraints"],
            req.scenario_time,
            [w["id"] for w in data["weather_cells"]],
            [c["id"] for c in data["constraints"]],
        )
        tags = extract_scenario_tags(simulation, selected)
    return {"matches": get_top_case_matches({"scenario_tags": tags}, k=3), "scenario_tags": tags}


@app.post("/api/emergency-chat")
def emergency_chat(req: EmergencyChatRequest) -> dict:
    data = load_scenario()
    simulation = simulate_delay_cascade(
        data["flights"],
        data["airports"],
        data["weather_cells"],
        data["constraints"],
        req.scenario_time,
        [w["id"] for w in data["weather_cells"]],
        [c["id"] for c in data["constraints"]],
    )
    optimization = optimize_interventions(
        data["flights"],
        data["airports"],
        data["weather_cells"],
        data["constraints"],
        req.scenario_time,
        20,
    )
    scored = simulation["scored_flights"]
    known_flight_ids = {f["flight_id"] for f in scored}
    session_memory = summarize_session(req.chat_history, req.message)
    requested_flight_id = extract_candidate_flight_id(req.message)
    message_flight_id = extract_flight_id(req.message, known_flight_ids)
    unknown_flight_id = requested_flight_id if requested_flight_id and requested_flight_id not in known_flight_ids else None
    selected_flight_id = message_flight_id or req.selected_flight_id or session_memory.get("active_flight_id")
    selected = None if unknown_flight_id else next((f for f in scored if f["flight_id"] == selected_flight_id), None)
    tags = req.scenario_tags or extract_scenario_tags(simulation, selected)
    return generate_emergency_chat_response(
        req.message,
        req.scenario_time,
        selected,
        simulation,
        optimization,
        tags,
        data["airports"],
        session_memory,
        unknown_flight_id,
    )
