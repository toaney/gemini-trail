from typing import Annotated, Optional
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages
from pydantic import BaseModel


class PartyMember(BaseModel):
    name: str
    health: int = 100
    health_label: str = "Good"
    status: str = "healthy"
    alive: bool = True


class Supplies(BaseModel):
    food_days: float = 0.0
    water_days: float = 0.0
    medicine_kits: int = 0
    ammo_rounds: int = 0
    fuel_gallons: float = 0.0
    trade_goods: int = 0
    spare_tires: int = 0
    engine_kits: int = 0
    generic_parts: int = 0


class StoreItem(BaseModel):
    price: int
    stock: int
    unit: str
    available: bool = True


class GameData(BaseModel):
    phase: str = "setup"
    day: int = 0
    departure_month: str = ""
    distance_traveled: float = 0.0
    current_landmark: Optional[str] = None
    next_landmark: str = "Las Vegas"
    region: str = "west"
    terrain: str = "coastal"
    weather: str = "clear"
    pace: str = "steady"
    rations: str = "filling"
    occupation: str = ""
    party: list[PartyMember] = []
    supplies: Supplies = Supplies()
    vehicle_condition: int = 100
    store_inventory: dict = {}
    suggestions: list[str] = []
    outcome: Optional[str] = None
    outcome_reason: Optional[str] = None


class GameState(TypedDict):
    messages: Annotated[list, add_messages]
    game: dict
