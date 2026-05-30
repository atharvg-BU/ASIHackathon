from pydantic import BaseModel, Field


class SimulateRequest(BaseModel):
    scenario_time: str = "14:30"
    enabled_weather_ids: list[str] = Field(default_factory=lambda: ["WX_CHI_001"])
    enabled_constraint_ids: list[str] = Field(default_factory=lambda: ["ZAU_CONSTRAINT_001"])


class OptimizeRequest(BaseModel):
    scenario_time: str = "14:30"
    objective: str = "minimum_intervention"
    max_interventions: int = 20


class BriefingRequest(BaseModel):
    scenario_time: str = "14:30"
    selected_flight_id: str | None = None


class CaseMatchRequest(BaseModel):
    scenario_time: str = "14:30"
    selected_flight_id: str | None = None
    scenario_tags: list[str] = Field(default_factory=list)


class EmergencyChatRequest(BaseModel):
    scenario_time: str = "14:30"
    selected_flight_id: str | None = None
    message: str
    scenario_tags: list[str] = Field(default_factory=list)
    chat_history: list[dict[str, str]] = Field(default_factory=list)
