from __future__ import annotations

from collections import defaultdict
from typing import Any

from .data_loader import time_to_minutes
from .risk_engine import compute_airport_congestion, score_flights


def simulate_delay_cascade(
    flights: list[dict[str, Any]],
    airports: list[dict[str, Any]],
    weather_cells: list[dict[str, Any]],
    constraints: list[dict[str, Any]],
    scenario_time: str,
    enabled_weather_ids: list[str],
    enabled_constraint_ids: list[str],
) -> dict[str, Any]:
    scored = score_flights(flights, airports, weather_cells, constraints, scenario_time, enabled_weather_ids, enabled_constraint_ids)
    graph = SimpleDiGraph()
    for flight in scored:
        base_delay = _base_delay(flight)
        graph.add_node(flight["flight_id"], delay=base_delay, risk=flight["risk_level"], total_risk=flight["total_risk"])

    _add_aircraft_edges(graph, scored)
    _add_congestion_edges(graph, scored)
    _propagate_delay(graph)

    direct = [f for f in scored if f["weather_risk"] > 0 or f["airspace_risk"] > 0]
    indirect_ids = {
        target
        for source in [f["flight_id"] for f in direct]
        for target in graph.descendants(source)
        if graph.nodes[target]["delay"] > 0
    }
    impacted_ids = {f["flight_id"] for f in direct} | indirect_ids
    impacted = [f for f in scored if f["flight_id"] in impacted_ids]
    total_delay = int(sum(graph.nodes[n]["delay"] for n in graph.nodes))

    return {
        "scenario_time": scenario_time,
        "impacted_flights": impacted,
        "direct_impact_count": len(direct),
        "indirect_impact_count": len(indirect_ids - {f["flight_id"] for f in direct}),
        "airport_congestion_summary": compute_airport_congestion(scored, airports),
        "delay_cascade_graph": {
            "nodes": [
                {"id": n, "delay": int(graph.nodes[n]["delay"]), "risk": graph.nodes[n]["risk"]}
                for n in graph.nodes
                if graph.nodes[n]["delay"] > 0
            ],
            "edges": [
                {"source": a, "target": b, "reason": graph.edges[a, b]["reason"]}
                for a, b in graph.edge_pairs()
                if graph.nodes[a]["delay"] > 0 or graph.nodes[b]["delay"] > 0
            ],
        },
        "total_predicted_delay_before_optimization": total_delay,
        "scored_flights": scored,
        "scenario_tags": _scenario_tags(direct, enabled_weather_ids, enabled_constraint_ids),
    }


def _base_delay(flight: dict[str, Any]) -> int:
    if flight["risk_level"] == "severe":
        return 55
    if flight["risk_level"] == "high":
        return 34
    if flight["weather_risk"] or flight["airspace_risk"]:
        return 22
    return 0


class SimpleDiGraph:
    def __init__(self) -> None:
        self.nodes: dict[str, dict[str, Any]] = {}
        self.edges: dict[tuple[str, str], dict[str, Any]] = {}
        self.outgoing: dict[str, set[str]] = defaultdict(set)
        self.incoming: dict[str, set[str]] = defaultdict(set)

    def add_node(self, node_id: str, **attrs: Any) -> None:
        self.nodes[node_id] = attrs

    def add_edge(self, source: str, target: str, **attrs: Any) -> None:
        self.edges[(source, target)] = attrs
        self.outgoing[source].add(target)
        self.incoming[target].add(source)

    def successors(self, node_id: str) -> set[str]:
        return self.outgoing[node_id]

    def edge_pairs(self) -> list[tuple[str, str]]:
        return list(self.edges.keys())

    def descendants(self, node_id: str) -> set[str]:
        seen: set[str] = set()
        stack = list(self.successors(node_id))
        while stack:
            current = stack.pop()
            if current in seen:
                continue
            seen.add(current)
            stack.extend(self.successors(current))
        return seen

    def topological_order(self) -> list[str]:
        indegree = {node: len(self.incoming[node]) for node in self.nodes}
        queue = [node for node, degree in indegree.items() if degree == 0]
        ordered: list[str] = []
        while queue:
            node = queue.pop(0)
            ordered.append(node)
            for target in self.successors(node):
                indegree[target] -= 1
                if indegree[target] == 0:
                    queue.append(target)
        return ordered or list(self.nodes)


def _add_aircraft_edges(graph: SimpleDiGraph, flights: list[dict[str, Any]]) -> None:
    by_aircraft: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for flight in flights:
        by_aircraft[flight["aircraft_id"]].append(flight)
    for turns in by_aircraft.values():
        ordered = sorted(turns, key=lambda f: time_to_minutes(f["departure_time_utc"]))
        for a, b in zip(ordered, ordered[1:]):
            graph.add_edge(a["flight_id"], b["flight_id"], reason="same aircraft reuse")


def _add_congestion_edges(graph: SimpleDiGraph, flights: list[dict[str, Any]]) -> None:
    by_dest_hour: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    for flight in flights:
        by_dest_hour[(flight["destination"], time_to_minutes(flight["arrival_time_utc"]) // 60)].append(flight)
    for group in by_dest_hour.values():
        if len(group) >= 3:
            ordered = sorted(group, key=lambda f: time_to_minutes(f["arrival_time_utc"]))
            for a, b in zip(ordered, ordered[1:]):
                graph.add_edge(a["flight_id"], b["flight_id"], reason="shared arrival bank congestion")


def _propagate_delay(graph: SimpleDiGraph) -> None:
    for node in graph.topological_order():
        delay = graph.nodes[node]["delay"]
        if delay <= 0:
            continue
        for downstream in graph.successors(node):
            propagated = max(5, int(delay * 0.42))
            graph.nodes[downstream]["delay"] = max(graph.nodes[downstream]["delay"], propagated)


def _scenario_tags(direct: list[dict[str, Any]], weather_ids: list[str], constraint_ids: list[str]) -> list[str]:
    tags = set()
    if weather_ids:
        tags.update(["convective_weather", "weather_hazard"])
    if constraint_ids:
        tags.add("airspace_constraint")
    if direct:
        tags.update(["reroute", "ground_hold", "delay_cascade"])
    if any(f["airport_congestion_risk"] > 0.55 for f in direct):
        tags.add("airport_congestion")
    return sorted(tags)
