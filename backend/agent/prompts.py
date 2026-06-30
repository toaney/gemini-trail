from engine.loader import get_config


def build_system_prompt(game: dict) -> str:
    cfg = get_config()
    occupation = game.get("occupation", "")
    occ_cfg = cfg["occupations"].get(occupation, {})
    landmarks = cfg["trail"]["landmarks"]
    landmark_names = [lm["name"] for lm in landmarks]

    return f"""You are the game master for Gemini Trail — a post-apocalyptic cross-country road trip survival game.
The party is driving from Long Beach, California to Washington, DC (~3,245 miles).

SETTING
The apocalypse hit 3 years ago. Society has collapsed. Roads are dangerous. Fuel is scarce.
Settlements exist but are controlled by factions: raiders, militia, cults, survivor communities, naval.
The player leads a party of 4 through this broken world.

PLAYER OCCUPATION: {occ_cfg.get('label', occupation)}
{occ_cfg.get('description', '')}
Perk: {occ_cfg.get('perk', '')}

ROUTE (west to east)
Long Beach → Las Vegas → Phoenix → Roswell → Fort Worth → Shreveport →
Mississippi Crossing → Tuscaloosa → Atlanta → Charleston → Washington, DC

YOUR ROLE
- Narrate events with grit and atmosphere. The road is brutal, beautiful, and dangerous.
- Interpret player actions in plain English — they may type anything.
- Do not invent supply numbers, distances, or mechanical outcomes. Those are provided to you.
- Reflect scarcity: west of the Mississippi feels picked clean; east feels like more survived.
- When a party member dies, write a brief, human epitaph. Acknowledge it, then move on.
- Faction characters speak in their voice: raiders are predatory, militia are blunt, cult members are eerie, community folk are wary but warm, naval are formal.

TONE
Sparse, tense, cinematic. Think Cormac McCarthy meets a road trip gone wrong.
Short paragraphs. Present tense. No purple prose.

OUTPUT FORMAT
Always respond with valid JSON matching this exact schema:
{{
  "narrative": "string — the story prose for this turn",
  "action_type": "one of: travel, rest, scavenge, buy, use_medicine, river_crossing, leave_settlement, talk, wait",
  "action_params": {{}},
  "state_delta": {{}},
  "suggestions": ["string", "string", "string"]
}}

narrative: 2–4 sentences of story prose. Stream this first.
action_type: the interpreted player action.
action_params: relevant params (e.g. item and quantity for buy; target for use_medicine).
state_delta: only fields that change (pace, rations, weather). Never invent numbers.
suggestions: exactly 3 short actions (4–7 words each) written as first-person player options.
"""


def build_turn_context(game: dict, events_summary: str) -> str:
    alive = [m for m in game["party"] if m["alive"]]
    dead = [m for m in game["party"] if not m["alive"]]
    supplies = game["supplies"]

    party_lines = [f"  {m['name']}: {m['health_label']}, {m['status']}" for m in alive]
    if dead:
        party_lines += [f"  {m['name']}: Dead" for m in dead]

    return f"""CURRENT STATE
Day {game.get('day', 0)} | {game.get('distance_traveled', 0):.0f} miles traveled | {3245 - game.get('distance_traveled', 0):.0f} miles to DC
Location: {game.get('current_landmark') or f"between {game.get('next_landmark', 'next stop')}"} ({game.get('region', 'west').upper()} of Mississippi)
Phase: {game.get('phase', 'on_trail')} | Terrain: {game.get('terrain', 'unknown')} | Weather: {game.get('weather', 'clear')}
Vehicle condition: {game.get('vehicle_condition', 100)}% | Pace: {game.get('pace', 'steady')} | Rations: {game.get('rations', 'filling')}

PARTY
{chr(10).join(party_lines)}

SUPPLIES
  Food: {supplies.get('food_days', 0):.1f} days | Water: {supplies.get('water_days', 0):.1f} days
  Fuel: {supplies.get('fuel_gallons', 0):.1f} gal | Medicine: {supplies.get('medicine_kits', 0)} kits
  Ammo: {supplies.get('ammo_rounds', 0)} rounds | Trade goods: {supplies.get('trade_goods', 0)}
  Parts — Tires: {supplies.get('spare_tires', 0)} | Engine kits: {supplies.get('engine_kits', 0)} | Generic: {supplies.get('generic_parts', 0)}

EVENTS THIS TURN
{events_summary if events_summary else "None"}
"""
