import json
import os
import time
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage

from agent.state import GameState
from agent.prompts import build_system_prompt, build_turn_context
from engine.loader import get_config
from engine import (
    consumption as cons_engine,
    travel as travel_engine,
    events as event_engine,
    scavenging as scav_engine,
    store as store_engine,
    conditions as cond_engine,
)


def _get_llm() -> ChatGoogleGenerativeAI:
    model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
    return ChatGoogleGenerativeAI(
        model=model,
        google_api_key=os.getenv("GEMINI_API_KEY"),
        temperature=0.8,
    )


def setup_node(state: GameState) -> dict:
    """Handles new game initialization before the first turn."""
    game = state.get("game", {})
    if game.get("phase") != "setup":
        return state

    cfg = get_config()
    occupation = game.get("occupation", "carpenter")
    occ_cfg = cfg["occupations"][occupation]

    game["phase"] = "preparation"
    game.setdefault("day", 0)
    game.setdefault("distance_traveled", 0.0)
    game.setdefault("terrain", "coastal")
    game.setdefault("region", "west")
    game.setdefault("weather", "clear")
    game.setdefault("pace", "steady")
    game.setdefault("rations", "filling")
    game.setdefault("vehicle_condition", 100)
    game.setdefault("current_landmark", None)
    game.setdefault("next_landmark", "Las Vegas")
    game.setdefault("suggestions", [
        "Buy food and water",
        "Stock up on fuel",
        "Buy spare parts",
    ])

    game["supplies"] = {
        "food_days": 100.0,
        "water_days": 50.0,
        "medicine_kits": 1,
        "ammo_rounds": 40,
        "fuel_gallons": 80.0,
        "trade_goods": occ_cfg["starting_budget"],
        "spare_tires": 1,
        "engine_kits": 0,
        "generic_parts": 1,
    }

    store_key = "long_beach"
    game["store_inventory"] = store_engine.get_store_inventory(store_key, occupation)
    game["current_store"] = store_key

    return {**state, "game": game}


def engine_node(state: GameState) -> dict:
    """Pure Python game logic — no Gemini calls."""
    game = dict(state["game"])
    messages = state.get("messages", [])
    last_message = messages[-1].content if messages else ""
    cfg = get_config()

    events_triggered = []
    action_context = {}

    phase = game.get("phase", "preparation")

    if phase == "preparation":
        action_context = _handle_preparation(game, last_message)

    elif phase == "on_trail":
        game, arrived = travel_engine.advance_travel(game)
        game = cons_engine.apply_daily_consumption(game)
        game, starvation_events = cons_engine.apply_starvation(game)
        events_triggered.extend(starvation_events)

        raw_events = event_engine.roll_daily_events(game)
        game, applied_events = event_engine.apply_events(game, raw_events)
        events_triggered.extend(applied_events)

        action_context = _handle_trail_action(game, last_message)
        if arrived:
            action_context["arrived_at"] = arrived

    elif phase == "at_landmark":
        action_context = _handle_landmark_action(game, last_message)

    elif phase == "event":
        action_context = _handle_event_action(game, last_message)

    game = cond_engine.update_health_labels(game)
    outcome, reason = cond_engine.check_win_loss(game)
    if outcome:
        game["outcome"] = outcome
        game["outcome_reason"] = reason
        game["phase"] = "game_over"

    game["_events_this_turn"] = events_triggered
    game["_action_context"] = action_context

    return {**state, "game": game}


def _handle_preparation(game: dict, message: str) -> dict:
    msg = message.lower()
    cfg = get_config()

    buy_keywords = ["buy", "get", "purchase", "take", "grab"]
    leave_keywords = ["go", "leave", "head out", "depart", "hit the road", "ready", "let's roll", "move out"]

    if any(kw in msg for kw in leave_keywords):
        game["phase"] = "on_trail"
        game["current_store"] = None
        game["store_inventory"] = {}
        return {"action": "depart", "message": "Departing Long Beach."}

    for kw in buy_keywords:
        if kw in msg:
            return _parse_buy_action(game, message)

    return {"action": "browse", "message": message}


def _handle_trail_action(game: dict, message: str) -> dict:
    msg = message.lower()

    if any(kw in msg for kw in ["rest", "camp", "stop", "sleep"]):
        game = cons_engine.apply_rest(game)
        game["day"] += 1
        return {"action": "rest"}

    if any(kw in msg for kw in ["scavenge", "search", "look for", "find", "forage"]):
        item = _extract_item(msg)
        result = scav_engine.attempt_scavenge(game, item)
        game = scav_engine.apply_scavenge_result(game, result)
        return {"action": "scavenge", "result": result}

    if any(kw in msg for kw in ["medicine", "heal", "treat", "give"]):
        target = _extract_name(game, message)
        if target:
            game, msg_out = cond_engine.apply_medicine(game, target)
            return {"action": "use_medicine", "target": target, "result": msg_out}

    if any(kw in msg for kw in ["fast", "speed up", "push harder", "reckless"]):
        game["pace"] = "fast" if "fast" in msg else "reckless"
        return {"action": "change_pace", "pace": game["pace"]}

    if any(kw in msg for kw in ["slow", "steady", "careful"]):
        game["pace"] = "steady"
        return {"action": "change_pace", "pace": "steady"}

    if "meager" in msg or "less food" in msg:
        game["rations"] = "meager"
        return {"action": "change_rations", "rations": "meager"}
    if "bare" in msg or "minimum" in msg:
        game["rations"] = "bare_minimum"
        return {"action": "change_rations", "rations": "bare_minimum"}
    if "filling" in msg or "full rations" in msg:
        game["rations"] = "filling"
        return {"action": "change_rations", "rations": "filling"}

    return {"action": "travel"}


def _handle_landmark_action(game: dict, message: str) -> dict:
    msg = message.lower()

    leave_keywords = ["leave", "go", "continue", "head out", "hit the road", "move on", "depart"]
    if any(kw in msg for kw in leave_keywords):
        game["phase"] = "on_trail"
        game["current_landmark"] = None
        game["store_inventory"] = {}
        game["current_store"] = None
        return {"action": "leave_settlement"}

    if any(kw in msg for kw in ["buy", "purchase", "get", "trade"]):
        return _parse_buy_action(game, message)

    if any(kw in msg for kw in ["rest", "sleep", "camp", "stay"]):
        game = cons_engine.apply_rest(game)
        game["day"] += 1
        return {"action": "rest"}

    if any(kw in msg for kw in ["medicine", "heal", "treat"]):
        target = _extract_name(game, message)
        if target:
            game, result = cond_engine.apply_medicine(game, target)
            return {"action": "use_medicine", "target": target, "result": result}

    return {"action": "talk"}


def _handle_event_action(game: dict, message: str) -> dict:
    msg = message.lower()
    landmark = game.get("current_landmark", "")

    if landmark == "Mississippi Crossing":
        if "bridge" in msg:
            return _apply_river_crossing(game, "bridge")
        elif "ferry" in msg or "ferryman" in msg or "pay" in msg:
            return _apply_river_crossing(game, "ferry")
        elif "raft" in msg or "build" in msg:
            return _apply_river_crossing(game, "raft")
        elif "detour" in msg or "go around" in msg:
            return _apply_river_crossing(game, "detour")

    return {"action": "wait", "message": "Waiting at event location."}


def _apply_river_crossing(game: dict, method: str) -> dict:
    cfg = get_config()
    crossing_cfg = next(
        lm for lm in cfg["trail"]["landmarks"] if lm["name"] == "Mississippi Crossing"
    )
    option = next(o for o in crossing_cfg["crossing_options"] if o["id"] == method)

    occupation = game.get("occupation", "carpenter")

    fuel_cost = option["fuel_cost"]
    vehicle_damage = option["vehicle_damage"]
    trade_cost = option["trade_goods_cost"]

    if method == "ferry" and game["supplies"]["trade_goods"] < trade_cost:
        return {"action": "river_crossing", "method": method, "blocked": True,
                "reason": f"Need {trade_cost} trade goods for the ferry."}

    if method == "raft" and occupation == "carpenter":
        damage_mod = cfg["occupations"]["carpenter"].get("raft_damage_modifier", 0.5)
        vehicle_damage = int(vehicle_damage * damage_mod)

    game["supplies"]["fuel_gallons"] = max(0.0, game["supplies"]["fuel_gallons"] - fuel_cost)
    game["supplies"]["trade_goods"] = max(0, game["supplies"]["trade_goods"] - trade_cost)
    game["vehicle_condition"] = max(0, game["vehicle_condition"] - vehicle_damage)
    game["day"] = game.get("day", 0) + option["time_days"]
    game["phase"] = "on_trail"
    game["current_landmark"] = None
    game["region"] = "east"

    return {"action": "river_crossing", "method": method, "days": option["time_days"],
            "vehicle_damage": vehicle_damage}


def _parse_buy_action(game: dict, message: str) -> dict:
    item_map = {
        "food": "food", "water": "water", "medicine": "medicine",
        "ammo": "ammo", "ammunition": "ammo", "fuel": "fuel",
        "tire": "spare_tire", "tires": "spare_tire",
        "engine": "engine_kit", "engine kit": "engine_kit",
        "parts": "generic_parts", "part": "generic_parts",
        "trade": "trade_goods", "goods": "trade_goods",
    }

    msg = message.lower()
    found_item = None
    for keyword, item_key in item_map.items():
        if keyword in msg:
            found_item = item_key
            break

    if not found_item:
        return {"action": "browse", "message": "What would you like to buy?"}

    quantity = 1
    import re
    nums = re.findall(r'\b(\d+)\b', msg)
    if nums:
        quantity = int(nums[0])

    landmark_key = game.get("current_store", "long_beach")
    game, result_msg = store_engine.buy_item(game, found_item, quantity, landmark_key)

    return {"action": "buy", "item": found_item, "quantity": quantity, "result": result_msg}


def _extract_item(message: str) -> str | None:
    items = ["food", "water", "ammo", "ammunition", "medicine", "fuel"]
    msg = message.lower()
    for item in items:
        if item in msg:
            return "ammo" if item == "ammunition" else item
    return None


def _extract_name(game: dict, message: str) -> str | None:
    for member in game["party"]:
        if member["name"].lower() in message.lower():
            return member["name"]
    return None


# Actions that never need LLM narration when no events fired
TEMPLATE_ACTIONS = {"travel", "change_pace", "change_rations", "rest"}


def _invoke_with_retry(llm, messages, max_retries: int = 3):
    """Invoke the LLM with exponential backoff on 429 rate-limit errors."""
    delay = 20
    for attempt in range(max_retries):
        try:
            return llm.invoke(messages)
        except Exception as e:
            err = str(e)
            if "429" in err or "RESOURCE_EXHAUSTED" in err:
                if attempt < max_retries - 1:
                    time.sleep(delay)
                    delay *= 2
                    continue
            raise
    return llm.invoke(messages)


def narrate_node(state: GameState) -> dict:
    """Calls Gemini to generate narrative and suggestions, with a fast-path for routine travel."""
    game = dict(state["game"])
    messages = list(state.get("messages", []))
    last_player_message = messages[-1].content if messages else ""

    events = game.pop("_events_this_turn", [])
    action_context = game.pop("_action_context", {})
    action = action_context.get("action")

    # Fast-path: skip the LLM whenever a routine on-trail action produced no events
    is_template = (
        action in TEMPLATE_ACTIONS
        and not events
        and game.get("phase") == "on_trail"
        and not game.get("outcome")
        and not action_context.get("arrived_at")
    )

    if is_template:
        game["suggestions"] = ["Continue traveling", "Rest for the day", "Scavenge for supplies", "Change pace"]
        game["_last_narrative"] = _template_narrative(game, action_context)
        return {**state, "game": game}

    # Full LLM path
    events_summary = _summarize_events(events, action_context)
    system_prompt = build_system_prompt(game)
    turn_context = build_turn_context(game, events_summary)

    llm = _get_llm()
    messages_to_send = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"{turn_context}\n\nPLAYER: {last_player_message}\n\nRespond with JSON only."),
    ]
    response = _invoke_with_retry(llm, messages_to_send)

    try:
        raw = response.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        result = json.loads(raw)
    except Exception:
        result = {
            "narrative": response.content,
            "action_type": "unknown",
            "action_params": {},
            "state_delta": {},
            "suggestions": ["Continue driving", "Check your supplies", "Rest here"],
        }

    VALID_PACES = {"steady", "fast", "reckless"}
    PACE_ALIASES = {"normal": "steady", "moderate": "steady", "slow": "steady", "quick": "fast", "hurry": "fast"}
    VALID_RATIONS = {"meager", "filling", "bare_minimum", "normal"}

    if result.get("state_delta"):
        delta = result["state_delta"]
        if "pace" in delta:
            raw_pace = str(delta["pace"]).lower()
            game["pace"] = PACE_ALIASES.get(raw_pace, raw_pace) if raw_pace not in VALID_PACES else raw_pace
            if game["pace"] not in VALID_PACES:
                game["pace"] = "steady"
        if "rations" in delta:
            raw_rations = str(delta["rations"]).lower()
            game["rations"] = raw_rations if raw_rations in VALID_RATIONS else "filling"
        if "weather" in delta:
            game["weather"] = delta["weather"]

    game["suggestions"] = result.get("suggestions", [])
    game["_last_narrative"] = result.get("narrative", "")

    return {**state, "game": game}


_TERRAIN_DESC = {
    "coastal":     "along the crumbling coastal highway",
    "deep_desert": "across scorched, sun-blasted desert",
    "high_desert": "through the sparse high desert",
    "plains":      "across the open, wind-swept plains",
    "swamp":       "through dense, fetid swampland",
    "woodland":    "through overgrown, reclaimed woodland",
    "urban_ruins": "through the shattered remnants of a city",
}

_WEATHER_LINE = {
    "clear":        "Clear skies.",
    "cloudy":       "Heavy clouds roll in from the west.",
    "rain":         "Steady rain drums on the roof.",
    "storm":        "A violent storm batters the vehicle.",
    "extreme_heat": "The heat is punishing, radiating off the asphalt.",
    "extreme_cold": "Bitter cold seeps through every seam.",
}


def _template_narrative(game: dict, action_context: dict) -> str:
    action  = action_context.get("action", "travel")
    day     = game.get("day", 0)
    dist    = game.get("distance_traveled", 0.0)
    terrain = game.get("terrain", "plains")
    weather = game.get("weather", "clear")
    next_lm = game.get("next_landmark", "the next settlement")
    supplies = game.get("supplies", {})
    food  = supplies.get("food_days", 0)
    water = supplies.get("water_days", 0)
    fuel  = supplies.get("fuel_gallons", 0)

    terrain_desc = _TERRAIN_DESC.get(terrain, "down the broken road")
    weather_line = _WEATHER_LINE.get(weather, "")

    if action == "rest":
        parts = [
            f"Day {day}. The party makes camp {terrain_desc}. {weather_line}".strip(),
            "You rest through the night, letting exhaustion ease out of tired muscles.",
            f"{dist:.0f} miles from Long Beach. Next stop: {next_lm}.",
        ]
    elif action == "change_pace":
        pace = game.get("pace", "steady")
        pace_line = {
            "steady":   "You ease off, settling into a steady, fuel-conscious rhythm.",
            "fast":     "You push harder. The engine climbs, eating up road.",
            "reckless": "Pedal down. The vehicle screams east. Every mile costs.",
        }.get(pace, "You adjust your pace.")
        parts = [
            f"Day {day}. {pace_line} {weather_line}".strip(),
            f"{dist:.0f} miles from Long Beach. Next stop: {next_lm}.",
        ]
    elif action == "change_rations":
        rations = game.get("rations", "filling")
        rations_line = {
            "meager":       "Rations cut. Everyone gets less. Hunger is a passenger now.",
            "bare_minimum": "Bare minimum. Just enough to keep moving.",
            "filling":      "Full rations restored. The party eats well for now.",
            "normal":       "Rations back to normal.",
        }.get(rations, "Rations adjusted.")
        parts = [
            f"Day {day}. {rations_line}",
            f"{dist:.0f} miles from Long Beach. Next stop: {next_lm}.",
        ]
    else:  # travel
        parts = [
            f"Day {day}. You push {terrain_desc}. {weather_line}".strip(),
            f"{dist:.0f} miles from Long Beach. Next stop: {next_lm}.",
        ]

    warnings = []
    if food < 5:     warnings.append("food critically low")
    elif food < 15:  warnings.append("food running short")
    if water < 3:    warnings.append("water nearly gone")
    elif water < 10: warnings.append("water getting scarce")
    if fuel < 10:    warnings.append("fuel dangerously low")
    elif fuel < 20:  warnings.append("fuel dropping")
    if warnings:
        parts.append(f"Warning: {', '.join(warnings)}.")

    return " ".join(parts)


def _summarize_events(events: list, action_context: dict) -> str:
    lines = []

    for event in events:
        if isinstance(event, str):
            lines.append(f"- {event}")
            continue
        etype = event.get("type", "")
        if etype == "disease":
            lines.append(f"- {event['victim']} contracted {event['disease']} ({event['severity']})")
        elif etype == "breakdown":
            fixed = "auto-fixed with parts" if event.get("auto_fixed") else "requires attention"
            lines.append(f"- Vehicle breakdown: {event['breakdown']} — {fixed}")
        elif etype == "raider":
            lines.append(f"- Raider encounter: {event['result']}")
        elif etype == "weather_change":
            lines.append(f"- Weather changed to: {event['new_weather']}")
        elif event in ["starvation", "dehydration"]:
            lines.append(f"- Party suffering from {event}")

    action = action_context.get("action", "")
    if action == "buy":
        lines.append(f"- {action_context.get('result', '')}")
    elif action == "scavenge":
        result = action_context.get("result", {})
        if result.get("success"):
            lines.append(f"- Scavenged {result['amount']} {result['unit']} of {result['item']}")
        else:
            lines.append(f"- Scavenge attempt failed — found nothing")
    elif action == "use_medicine":
        lines.append(f"- {action_context.get('result', '')}")
    elif action == "river_crossing":
        lines.append(f"- Mississippi crossing via {action_context.get('method')} — {action_context.get('days')} day(s)")
    elif action == "arrive":
        lines.append(f"- Arrived at {action_context.get('arrived_at')}")

    return "\n".join(lines) if lines else "Uneventful turn."
