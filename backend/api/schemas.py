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
