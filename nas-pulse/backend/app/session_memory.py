from __future__ import annotations

import re
from typing import Any


def summarize_session(chat_history: list[dict[str, str]], current_message: str) -> dict[str, Any]:
    text = "\n".join(item.get("content", "") for item in chat_history[-10:])
    combined = f"{text}\n{current_message}".lower()
    flight_ids = re.findall(r"\b[A-Z]{2,4}\d{2,4}\b", f"{text}\n{current_message}".upper())
    facts = {
        "active_flight_id": flight_ids[-1] if flight_ids else None,
        "event_type": None,
        "fuel_status": None,
        "fuel_minutes": None,
        "last_user_messages": [item.get("content", "") for item in chat_history[-6:] if item.get("role") == "controller"],
    }
    if "bird" in combined or "strike" in combined:
        facts["event_type"] = "bird_strike"
    if any(phrase in combined for phrase in ["fuel wont", "fuel won't", "fuel will not", "not enough fuel", "insufficient fuel", "fuel low", "no fuel", "no fuell"]):
        facts["fuel_status"] = "insufficient"
    elif "fuel" in combined:
        facts["fuel_status"] = "mentioned"
    minute_matches = re.findall(r"(\d{1,3})\s*(?:min|mins|minutes)", combined)
    if minute_matches and "fuel" in combined:
        facts["fuel_minutes"] = int(minute_matches[-1])
    return facts


def format_session_summary(memory: dict[str, Any]) -> str:
    bits = []
    if memory.get("active_flight_id"):
        bits.append(f"active flight {memory['active_flight_id']}")
    if memory.get("event_type"):
        bits.append(f"event {memory['event_type']}")
    if memory.get("fuel_status"):
        bits.append(f"fuel status {memory['fuel_status']}")
    return ", ".join(bits) if bits else "no prior emergency facts"
