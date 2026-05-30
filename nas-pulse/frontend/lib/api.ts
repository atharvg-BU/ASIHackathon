const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
    cache: "no-store"
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

export const api = {
  scenario: <T>() => request<T>("/api/scenario"),
  flights: <T>(time: string) => request<T>(`/api/flights?scenario_time=${time}`),
  liveFlight: <T>(flightId: string, time: string) => request<T>(`/api/live-flight/${flightId}?scenario_time=${time}`),
  simulate: <T>(body: unknown) => request<T>("/api/simulate", { method: "POST", body: JSON.stringify(body) }),
  optimize: <T>(body: unknown) => request<T>("/api/optimize", { method: "POST", body: JSON.stringify(body) }),
  briefing: <T>(body: unknown) => request<T>("/api/briefing", { method: "POST", body: JSON.stringify(body) }),
  caseMatches: <T>(body: unknown) => request<T>("/api/case-matches", { method: "POST", body: JSON.stringify(body) }),
  emergencyChat: <T>(body: unknown) => request<T>("/api/emergency-chat", { method: "POST", body: JSON.stringify(body) })
};

export function riskColor(level?: string) {
  return { low: "#8cf7b1", medium: "#ffe66b", high: "#ffbc58", severe: "#ff5b6e" }[level || "low"] || "#8cf7b1";
}
