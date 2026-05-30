# NAS Pulse

Counterfactual Airspace Recovery Engine for a hackathon demo.

**Demo only - not for operational aviation use.** NAS Pulse is a simplified full-stack simulator for exploring how weather, constrained airspace, airport congestion, and aircraft reuse can create network delay cascades.

## Why It Is Different

Most reroute demos treat each flight independently. NAS Pulse treats the National Airspace System as a network. It scores flights, propagates downstream delay through aircraft turns and arrival banks, then recommends the smallest high-impact set of ground holds, reroutes, altitude shifts, and speed adjustments.

## Architecture

```text
Next.js dashboard
  -> FastAPI endpoints
    -> CSV/JSON demo scenario + hackathon_data_bundle route snapshots
    -> risk_engine.py
    -> cascade_simulator.py
    -> optimizer.py
    -> historical_case_matcher.py
    -> briefing_generator.py
```

## Data Requirements From `hackathon_data_bundle`

The provided bundle documentation was used to shape the project:

- `routes`: route snapshots contain ISO UTC times, ICAO origin/destination codes, cruise altitude/speed, parallel `lats`/`lons`, and `is_airborne`.
- `wx`: weather strips are `refc` and `retop` NPZ matrices on a 256 x 358 CONUS lat/lon grid. Operationally, high reflectivity plus echo tops above cruise altitude would indicate impact.
- `sectors`: synthetic ATC sectors are GeoJSON polygons split into LOW and HIGH altitude bands with capacity values.

For this runnable hackathon app, the backend now imports a capped set of real route-snapshot flights from `hackathon_data_bundle/asked_at_2025-06-10T17:00:00Z/routes.json` and combines them with the curated demo flights. The Chicago weather polygon still stands in for weather derived from `refc`/`retop`, and `airspace_constraints.json` stands in for a capacity-constrained sector set.

## Historical Case Memory

NAS Pulse includes `backend/data/historical_cases.json`, a demo-only memory layer that matches scenario tags such as `convective_weather`, `airspace_constraint`, `ground_hold`, `reroute`, `fuel_emergency`, and `emergency_landing` against past aviation disruption patterns.

This makes the project different because the optimizer does not only emit actions; it also explains why those actions resemble known disruption patterns. The API uses simple Jaccard similarity and conservative boosts for matching weather or airspace characteristics.

Historical case memory is useful for explanation and decision support, but it is not operational aviation guidance. It never provides cockpit instructions and should not be used for real dispatch, ATC, or flight operations.

## Controller Emergency Chat

The dashboard now runs in **selectable-flight live simulation mode**. `UAL777` is still the default focus, but controllers can select any active demo/bundle flight from the flight list and the map, live panel, emergency flag, and chat will follow that selected flight.

The dashboard includes a floating **Emergency Chat** panel. Controllers can flag the live flight and ask for:

- historical case analogies for the current scenario
- high-level best options for the selected flight
- emergency-style network risk summaries
- optimizer-backed action suggestions

The chat uses a small RAG-style context bundle for the flagged flight. It retrieves flight profile, route waypoints, computed risk, nearby water-body context, optimizer actions, and historical case matches before answering. The response is designed to be conversational: it gives a best choice, explains why, compares alternatives, and names what to monitor next.

The chat is deterministic and local by default. It does not require an API key. To enable Claude responses over the same retrieved context, set:

```bash
export ANTHROPIC_API_KEY=your_key
export USE_LLM_CHAT=true
export ANTHROPIC_MODEL=claude-opus-4-8
```

In Docker, these environment variables are already wired through `docker-compose.yml`; pass them from your shell before running Compose. If the key is missing or the API call fails, the deterministic conversational fallback still works.

The chat is intentionally constrained: it provides controller/dispatcher situational awareness and high-level playbook comparison only. It does not generate cockpit instructions.

## Selectable-Flight Live Simulation

- default focused flight: `UAL777`
- selectable bundle flights are loaded from `hackathon_data_bundle`
- traffic clock starts at `15:10 UTC`
- live aircraft position is interpolated along whichever flight is selected
- Play/Pause advances the traffic clock in five-minute steps
- the emergency flag and RAG chat attach to the selected/flagged flight
- map shows the selected route and one live aircraft marker

This keeps the emergency workflow easy to judge while allowing multiple real route-snapshot flights to be tested.

## Setup

Backend:

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000`. The backend runs at `http://localhost:8000`.

Docker:

```bash
docker-compose up --build
```

`docker-compose.yml` mounts `../hackathon_data_bundle` into the backend container as read-only data. If you want a different snapshot or more imported flights, change `BUNDLE_ROUTES_FILE` or `BUNDLE_FLIGHT_LIMIT`.

## API Endpoints

- `GET /health`
- `GET /api/scenario`
- `GET /api/live-flight/{flight_id}?scenario_time=15:10`
- `GET /api/flights?scenario_time=14:30`
- `GET /api/flights/{flight_id}`
- `POST /api/simulate`
- `POST /api/optimize`
- `POST /api/briefing`
- `POST /api/case-matches`
- `POST /api/emergency-chat`

## Demo Script

1. Open the dashboard and confirm the visible demo disclaimer.
2. Pick a flight from **Selectable Flights**, for example `JBU315` or `UAL2398`.
3. Press Play to move the selected aircraft along its planned route.
4. Flag the selected flight for emergency chat.
5. Open Emergency Chat and ask: `bird strike on JBU315, what are best options?`
6. Run Simulation or Optimizer to show the broader network context when needed.

## Data Assumptions

- Flight paths are simplified waypoint lines.
- Weather and constraints are simplified polygons around the Chicago corridor.
- Airport congestion uses arrival-bank counts and demo capacity scaling.
- Delay propagation is graph-based and deterministic.
- Optimizer choices are heuristic and intended for explainable demos.

## Safety Disclaimer

NAS Pulse is not certified aviation software. It is a hackathon simulation for network reasoning, visual explanation, and counterfactual exploration. It must not be used for operational aviation decisions.
