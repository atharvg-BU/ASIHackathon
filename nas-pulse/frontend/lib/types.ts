export type RiskLevel = "low" | "medium" | "high" | "severe";

export type Flight = {
  flight_id: string;
  airline: string;
  origin: string;
  destination: string;
  departure_time_utc: string;
  arrival_time_utc: string;
  aircraft_id: string;
  planned_altitude: number;
  planned_speed: number;
  passenger_count: number;
  priority_score: number;
  planned_route_latlons: [number, number][];
  data_source?: "nas_pulse_demo" | "hackathon_data_bundle";
  route_snapshot_asked_at?: string;
  data_note?: string;
  total_risk?: number;
  risk_level?: RiskLevel;
  weather_risk?: number;
  airspace_risk?: number;
  airport_congestion_risk?: number;
  delay_propagation_risk?: number;
};

export type Airport = { airport_code: string; name: string; lat: number; lon: number; capacity_per_hour: number };
export type PolygonHazard = { id: string; polygon: [number, number][]; description?: string; name?: string; severity?: number };
export type Scenario = { airports: Airport[]; flights: Flight[]; weather_cells: PolygonHazard[]; constraints: PolygonHazard[]; playbooks: any[] };
export type SimResult = {
  impacted_flights: Flight[];
  direct_impact_count: number;
  indirect_impact_count: number;
  airport_congestion_summary: Record<string, any>;
  delay_cascade_graph: { nodes: { id: string; delay: number; risk: RiskLevel }[]; edges: { source: string; target: string; reason: string }[] };
  total_predicted_delay_before_optimization: number;
  scenario_tags: string[];
};
export type Optimization = {
  recommended_actions: any[];
  before_metrics: any;
  after_metrics: any;
  delay_reduction_percentage: number;
  congestion_reduction_percentage: number;
  trajectory_options: Record<string, any[]>;
  simulation: SimResult;
};
export type CaseMatch = {
  case_id: string;
  case_name: string;
  similarity_score: number;
  matched_tags: string[];
  situation_summary: string;
  system_lesson: string;
  how_nas_pulse_uses_it: string[];
};

export type ChatMessage = {
  role: "controller" | "assistant";
  content: string;
};

export type EmergencyChatResponse = {
  intent: string;
  response: string;
  historical_matches: CaseMatch[];
  recommended_actions: any[];
  message_tags?: string[];
  effective_scenario_tags?: string[];
  rag_context?: { query: string; chunks: { id: string; title: string; text: string }[] };
  llm_used?: boolean;
  llm_status?: {
    enabled: boolean;
    provider: string;
    model: string;
    api_key_present: boolean;
    used: boolean;
    reason: string;
    error?: string;
  };
  focused_flight_id?: string | null;
  unknown_flight_id?: string | null;
  session_memory?: Record<string, any>;
  disclaimer: string;
};

export type LiveFlight = {
  flight_id: string;
  scenario_time: string;
  status: "scheduled" | "airborne" | "arrived";
  progress: number;
  current_position: [number, number];
  minutes_since_departure: number;
  minutes_to_arrival: number;
  flight: Flight;
  water_context?: {
    nearby_water_bodies: { name: string; type: string; distance_nm: number }[];
    note: string;
  };
};
