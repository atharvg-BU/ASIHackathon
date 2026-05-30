"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import DelayCascadeGraph from "@/components/DelayCascadeGraph";
import DispatcherBriefing from "@/components/DispatcherBriefing";
import EmergencyChat from "@/components/EmergencyChat";
import FlightRiskTable from "@/components/FlightRiskTable";
import HistoricalCaseMatch from "@/components/HistoricalCaseMatch";
import InterventionList from "@/components/InterventionList";
import LiveFlightPanel from "@/components/LiveFlightPanel";
import MapView from "@/components/MapView";
import ScenarioControls from "@/components/ScenarioControls";
import Scorecard from "@/components/Scorecard";
import TrajectoryOptions from "@/components/TrajectoryOptions";
import { api } from "@/lib/api";
import type { CaseMatch, Flight, LiveFlight, Optimization, Scenario, SimResult } from "@/lib/types";

const DEFAULT_FOCUS_FLIGHT_ID = "UAL777";

export default function Home() {
  const [scenario, setScenario] = useState<Scenario | null>(null);
  const [flights, setFlights] = useState<Flight[]>([]);
  const [selected, setSelected] = useState<Flight | null>(null);
  const [emergencyFlight, setEmergencyFlight] = useState<Flight | null>(null);
  const [liveFlight, setLiveFlight] = useState<LiveFlight | undefined>();
  const [time, setTime] = useState("15:10");
  const [playing, setPlaying] = useState(false);
  const [weatherEnabled, setWeatherEnabled] = useState(true);
  const [constraintEnabled, setConstraintEnabled] = useState(true);
  const [simulation, setSimulation] = useState<SimResult | undefined>();
  const [optimization, setOptimization] = useState<Optimization | undefined>();
  const [briefing, setBriefing] = useState<string | undefined>();
  const [caseMatches, setCaseMatches] = useState<CaseMatch[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | undefined>();

  const loadFlights = useCallback(async () => {
    const scored = await api.flights<Flight[]>(time);
    setFlights(scored);
    setSelected((current) => {
      if (current) return scored.find((flight) => flight.flight_id === current.flight_id) || scored[0] || null;
      return scored.find((flight) => flight.flight_id === DEFAULT_FOCUS_FLIGHT_ID) || scored[0] || null;
    });
  }, [time]);

  const loadLiveFlight = useCallback(async () => {
    const flightId = selected?.flight_id || DEFAULT_FOCUS_FLIGHT_ID;
    const live = await api.liveFlight<LiveFlight>(flightId, time);
    setLiveFlight(live);
    setSelected(live.flight);
  }, [selected?.flight_id, time]);

  useEffect(() => {
    api.scenario<Scenario>().then(setScenario).catch((err) => setError(err.message));
  }, []);

  useEffect(() => {
    loadFlights().catch((err) => setError(err.message));
  }, [loadFlights]);

  useEffect(() => {
    loadLiveFlight().catch((err) => setError(err.message));
  }, [loadLiveFlight]);

  useEffect(() => {
    if (!playing) return;
    const timer = window.setInterval(() => {
      setTime((current) => addMinutes(current, 5));
    }, 1400);
    return () => window.clearInterval(timer);
  }, [playing]);

  const enabledWeatherIds = weatherEnabled ? ["WX_CHI_001"] : [];
  const enabledConstraintIds = constraintEnabled ? ["ZAU_CONSTRAINT_001"] : [];

  const runSimulation = useCallback(async () => {
    setLoading(true);
    setError(undefined);
    try {
      const sim = await api.simulate<SimResult>({ scenario_time: time, enabled_weather_ids: enabledWeatherIds, enabled_constraint_ids: enabledConstraintIds });
      const cases = await api.caseMatches<{ matches: CaseMatch[] }>({ scenario_time: time, selected_flight_id: selected?.flight_id, scenario_tags: sim.scenario_tags });
      const brief = await api.briefing<{ briefing: string }>({ scenario_time: time, selected_flight_id: selected?.flight_id });
      setSimulation(sim);
      setCaseMatches(cases.matches);
      setBriefing(brief.briefing);
      setFlights(sim.impacted_flights.length ? mergeRisk(flights, sim.impacted_flights) : flights);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [time, enabledWeatherIds, enabledConstraintIds, selected?.flight_id, flights]);

  const runOptimizer = useCallback(async () => {
    setLoading(true);
    setError(undefined);
    try {
      const opt = await api.optimize<Optimization>({ scenario_time: time, objective: "minimum_intervention", max_interventions: 20 });
      const brief = await api.briefing<{ briefing: string }>({ scenario_time: time, selected_flight_id: selected?.flight_id });
      const cases = await api.caseMatches<{ matches: CaseMatch[] }>({ scenario_time: time, selected_flight_id: selected?.flight_id, scenario_tags: opt.simulation.scenario_tags });
      setOptimization(opt);
      setSimulation(opt.simulation);
      setBriefing(brief.briefing);
      setCaseMatches(cases.matches);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [time, selected?.flight_id]);

  const activeWeather = useMemo(() => (weatherEnabled ? scenario?.weather_cells || [] : []), [scenario, weatherEnabled]);
  const activeConstraints = useMemo(() => (constraintEnabled ? scenario?.constraints || [] : []), [scenario, constraintEnabled]);
  const activeFlights = useMemo(() => {
    const now = toMinutes(time);
    return flights.filter((flight) => {
      const dep = toMinutes(flight.departure_time_utc);
      const arr = toMinutes(flight.arrival_time_utc);
      return dep <= now && now <= arr;
    });
  }, [flights, time]);
  const focusedFlight = useMemo(() => liveFlight?.flight || selected || flights.find((flight) => flight.flight_id === DEFAULT_FOCUS_FLIGHT_ID), [flights, liveFlight, selected]);
  const visibleFlights = focusedFlight ? [focusedFlight] : [];

  return (
    <main className="min-h-screen bg-[#071019] p-4 text-slate-100">
      <header className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-normal text-white">NAS Pulse</h1>
          <p className="text-sm text-slate-400">Counterfactual Airspace Recovery Engine</p>
        </div>
        <div className="flex items-center gap-2">
          <span className="rounded-full border border-runway/30 bg-runway/10 px-3 py-1 text-xs font-semibold text-runway">Demo Mode</span>
          <span className="rounded-full border border-danger/30 bg-danger/10 px-3 py-1 text-xs text-danger">Not for operational aviation use</span>
        </div>
      </header>

      {error && <div className="mb-4 rounded-md border border-danger/40 bg-danger/10 p-3 text-sm text-danger">{error}</div>}

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-[300px_1fr_340px]">
        <aside className="space-y-4">
          <LiveFlightPanel
            liveFlight={liveFlight}
            playing={playing}
            onTogglePlay={() => setPlaying((value) => !value)}
            onFlagEmergency={() => {
              if (focusedFlight) {
                setEmergencyFlight(focusedFlight);
                setSelected(focusedFlight);
              }
            }}
          />
          <FlightRiskTable
            flights={activeFlights}
            selected={selected?.flight_id}
            emergencyFlightId={emergencyFlight?.flight_id}
            onSelect={(flight) => {
              setSelected(flight);
              setEmergencyFlight((current) => current?.flight_id === flight.flight_id ? flight : current);
            }}
            onFlagEmergency={(flight) => {
              setEmergencyFlight(flight);
              setSelected(flight);
            }}
          />
          <ScenarioControls
            time={time}
            setTime={setTime}
            weatherEnabled={weatherEnabled}
            setWeatherEnabled={setWeatherEnabled}
            constraintEnabled={constraintEnabled}
            setConstraintEnabled={setConstraintEnabled}
            onSimulate={runSimulation}
            onOptimize={runOptimizer}
            loading={loading}
          />
        </aside>

        <section className="space-y-4">
          <div className="glass rounded-lg p-3">
            {scenario ? (
              <MapView
                airports={scenario.airports}
                flights={visibleFlights}
                weather={activeWeather}
                constraints={activeConstraints}
                selectedFlight={selected?.flight_id}
                emergencyFlightId={emergencyFlight?.flight_id}
                livePosition={liveFlight?.current_position}
                onSelectFlight={setSelected}
              />
            ) : (
              <div className="h-[620px] animate-pulse rounded-lg bg-white/[0.04]" />
            )}
          </div>
          <DelayCascadeGraph simulation={simulation} />
        </section>

        <aside className="space-y-4">
          <Scorecard simulation={simulation} optimization={optimization} />
          {selected && (
            <section className="glass rounded-lg p-4">
              <div className="flex items-center justify-between gap-2">
                <h2 className="text-sm font-semibold text-white">Selected Flight</h2>
                {emergencyFlight?.flight_id === selected.flight_id && <span className="rounded-full bg-danger/15 px-2 py-1 text-[11px] font-semibold text-danger">Emergency</span>}
              </div>
              <div className="mt-3 grid grid-cols-2 gap-2 text-sm">
                <Info label="Flight" value={selected.flight_id} />
                <Info label="Route" value={`${selected.origin}-${selected.destination}`} />
                <Info label="Risk" value={selected.risk_level || "low"} />
                <Info label="Passengers" value={String(selected.passenger_count)} />
              </div>
              <button
                onClick={() => setEmergencyFlight(selected)}
                className="mt-3 w-full rounded-md bg-danger/15 px-3 py-2 text-sm font-semibold text-danger hover:bg-danger/25"
              >
                {emergencyFlight?.flight_id === selected.flight_id ? "Emergency flagged for chat" : "Flag this flight for emergency chat"}
              </button>
            </section>
          )}
          <DispatcherBriefing text={briefing} />
        </aside>
      </div>

      <section className="mt-4 grid grid-cols-1 gap-4 xl:grid-cols-3">
        <InterventionList optimization={optimization} />
        <TrajectoryOptions optimization={optimization} selectedFlightId={selected?.flight_id} />
        <HistoricalCaseMatch matches={caseMatches} />
      </section>

      <footer className="mt-5 text-center text-xs text-slate-500">
        Demo only - not for operational aviation use. Sample data is simplified for hackathon evaluation.
      </footer>
      <EmergencyChat
        scenarioTime={time}
        selectedFlightId={selected?.flight_id}
        emergencyFlightId={emergencyFlight?.flight_id}
        scenarioTags={simulation?.scenario_tags || []}
        onFlagFlight={(flightId) => {
          const flight = liveFlight?.flight?.flight_id === flightId
            ? liveFlight.flight
            : flights.find((item) => item.flight_id === flightId);
          if (flight) {
            setEmergencyFlight(flight);
            setSelected(flight);
          }
        }}
      />
    </main>
  );
}

function Info({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md bg-white/[0.04] p-2">
      <div className="text-xs text-slate-400">{label}</div>
      <div className="font-semibold text-white">{value}</div>
    </div>
  );
}

function mergeRisk(base: Flight[], impacted: Flight[]) {
  const byId = new Map(impacted.map((flight) => [flight.flight_id, flight]));
  return base.map((flight) => byId.get(flight.flight_id) || flight);
}

function toMinutes(value: string) {
  const [hh, mm] = value.split(":").map(Number);
  return hh * 60 + mm;
}

function addMinutes(value: string, increment: number) {
  const total = (toMinutes(value) + increment) % 1440;
  const hh = String(Math.floor(total / 60)).padStart(2, "0");
  const mm = String(total % 60).padStart(2, "0");
  return `${hh}:${mm}`;
}
