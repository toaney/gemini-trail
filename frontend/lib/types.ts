export interface PartyMember {
  name: string;
  health_label: "Good" | "Fair" | "Poor" | "Critical" | "Dead";
  status: string;
  alive: boolean;
}

export interface Supplies {
  food_days: number;
  water_days: number;
  medicine_kits: number;
  ammo_rounds: number;
  fuel_gallons: number;
  trade_goods: number;
  spare_tires: number;
  engine_kits: number;
  generic_parts: number;
}

export interface StoreItem {
  price: number;
  stock: number;
  unit: string;
  available: boolean;
  hidden?: boolean;
}

export interface GameState {
  phase: string;
  day: number;
  departure_month: string;
  distance_traveled: number;
  current_landmark: string | null;
  next_landmark: string;
  region: "west" | "east";
  terrain: string;
  weather: string;
  pace: string;
  rations: string;
  occupation: string;
  party: PartyMember[];
  supplies: Supplies;
  vehicle_condition: number;
  store_inventory: Record<string, StoreItem>;
  suggestions: string[];
  outcome: string | null;
  outcome_reason: string | null;
}

export interface SSEEvent {
  type: "token" | "state_update" | "suggestions" | "game_over" | "done" | "error";
  content?: string;
  game?: GameState;
  actions?: string[];
  outcome?: string;
  reason?: string;
  message?: string;
}

export interface NewGameForm {
  partyNames: [string, string, string, string];
  occupation: "bunker_ceo" | "engineer" | "carpenter";
  departureMonth: string;
}
