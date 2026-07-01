from pydantic import BaseModel
from typing import Optional


class NewGameRequest(BaseModel):
    player_name: str
    party_names: list[str]
    occupation: str
    departure_month: str


class ActionRequest(BaseModel):
    thread_id: str
    message: str


class GameSessionResponse(BaseModel):
    thread_id: str
    player_name: str
    occupation: str
    departure_month: str
    opening_narrative: str = ""
    opening_suggestions: list[str] = []
    initial_game_state: dict = {}


class SaveRequest(BaseModel):
    thread_id: str
    name: str
    game_state: dict


class SavePoint(BaseModel):
    id: int
    name: str
    thread_id: str
    day: int
    distance: float
    phase: str
    created_at: str


class LoadRequest(BaseModel):
    save_id: int
