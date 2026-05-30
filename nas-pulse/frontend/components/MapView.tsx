"use client";

import { useEffect, useRef } from "react";
import type { Airport, Flight, PolygonHazard } from "@/lib/types";
import { riskColor } from "@/lib/api";

type Props = {
  airports: Airport[];
  flights: Flight[];
  weather: PolygonHazard[];
  constraints: PolygonHazard[];
  selectedFlight?: string;
  emergencyFlightId?: string;
  livePosition?: [number, number];
  onSelectFlight: (flight: Flight) => void;
};

export default function MapView({ airports, flights, weather, constraints, selectedFlight, emergencyFlightId, livePosition, onSelectFlight }: Props) {
  const divRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<any>(null);
  const layersRef = useRef<any[]>([]);

  useEffect(() => {
    let mounted = true;
    import("leaflet").then((L) => {
      if (!mounted || !divRef.current || mapRef.current) return;
      mapRef.current = L.map(divRef.current, { zoomControl: false }).setView([39.5, -96], 4);
      L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: "OpenStreetMap"
      }).addTo(mapRef.current);
    });
    return () => { mounted = false; };
  }, []);

  useEffect(() => {
    import("leaflet").then((L) => {
      const map = mapRef.current;
      if (!map) return;
      layersRef.current.forEach((layer) => layer.remove());
      layersRef.current = [];

      weather.forEach((cell) => {
        const layer = L.polygon(cell.polygon as any, { color: "#ff5b6e", fillColor: "#ff5b6e", fillOpacity: 0.22, weight: 2 }).addTo(map);
        layersRef.current.push(layer);
      });
      constraints.forEach((constraint) => {
        const layer = L.polygon(constraint.polygon as any, { color: "#b88cff", fillOpacity: 0.05, dashArray: "6 6", weight: 2 }).addTo(map);
        layersRef.current.push(layer);
      });
      flights.forEach((flight) => {
        const emergency = emergencyFlightId === flight.flight_id;
        const layer = L.polyline(flight.planned_route_latlons as any, {
          color: emergency ? "#ff5b6e" : riskColor(flight.risk_level),
          weight: emergency ? 7 : selectedFlight === flight.flight_id ? 5 : 2,
          opacity: emergency || selectedFlight === flight.flight_id ? 1 : 0.72
        }).addTo(map);
        layer.on("click", () => onSelectFlight(flight));
        layer.bindTooltip(`${flight.flight_id} ${flight.origin}-${flight.destination}`);
        layersRef.current.push(layer);
      });
      if (livePosition) {
        const live = L.circleMarker(livePosition as any, {
          radius: 9,
          color: "#ffffff",
          fillColor: "#43d9ff",
          fillOpacity: 1,
          weight: 3
        }).addTo(map);
        live.bindTooltip("Live aircraft position");
        layersRef.current.push(live);
      }
      airports.forEach((airport) => {
        const marker = L.circleMarker([airport.lat, airport.lon], { radius: 4, color: "#43d9ff", fillColor: "#43d9ff", fillOpacity: 0.9 }).addTo(map);
        marker.bindTooltip(`${airport.airport_code} ${airport.name}`);
        layersRef.current.push(marker);
      });
    });
  }, [airports, flights, weather, constraints, selectedFlight, emergencyFlightId, livePosition, onSelectFlight]);

  return <div ref={divRef} className="h-[620px] w-full overflow-hidden rounded-lg border border-white/10" />;
}
