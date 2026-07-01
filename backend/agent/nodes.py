import json
import os
import time
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage

from agent.state import GameState
from agent.prompts import build_system_prompt, build_turn_context
from agent.templates import build_narrative, get_suggestions
from engine.loader import get_config
from engine import (
    consumption as cons_engine,
    travel as travel_engine,
    events as event_engine,
    scavenging as scav_engine,
    store as store_engine,
    conditions as cond_engine,
)


_FALLBACK_MODELS = ["gemini-3.5-flash", "gemini-3.1-flash-lite"]

def _get_llm(model: str | None = None) -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(
        model=model or os.getenv("GEMINI_MODEL", _FALLBACK_MODELS[0]),
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

    elif phase == "stranded":
        game["day"] = game.get("day", 0) + 1
        game, starvation_events = cons_engine.apply_starvation(game)
        events_triggered.extend(starvation_events)
        action_context = _handle_stranded_action(game, last_message)

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
    # Only explicit departure phrases — avoids "go buy fuel" or "get ready" accidentally departing
    leave_keywords = ["head out", "depart", "hit the road", "let's roll", "move out",
                      "begin journey", "begin the journey", "start journey", "start the journey"]

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

    if msg.strip() == "scavenge for supplies":
        return {"action": "select_scavenge"}

    if any(kw in msg for kw in ["scavenge", "salvage", "search", "look for", "find", "forage"]):
        item = _extract_item(msg)
        result = scav_engine.attempt_scavenge(game, item)
        game = scav_engine.apply_scavenge_result(game, result)
        return {"action": "scavenge", "result": result}

    if any(kw in msg for kw in ["medicine", "heal", "treat", "give"]):
        target = _extract_name(game, message)
        if target:
            game, msg_out = cond_engine.apply_medicine(game, target)
            return {"action": "use_medicine", "target": target, "result": msg_out}

    if msg.strip() in ("change pace", "change my pace"):
        return {"action": "select_pace"}

    if "keep current pace" in msg:
        return {"action": "change_pace", "pace": game.get("pace", "steady")}

    if any(kw in msg for kw in ["fast", "speed up", "push harder", "reckless"]):
        game["pace"] = "fast" if "fast" in msg else "reckless"
        return {"action": "change_pace", "pace": game["pace"]}

    if any(kw in msg for kw in ["slow", "steady", "careful", "moderate", "normal"]):
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

    if any(kw in msg for kw in ["attack", "raid", "ambush", "rob", "caravan", "intercept"]):
        return _do_caravan_attack(game)

    _TRAVEL_WORDS = {"drive", "travel", "go", "move", "continue", "push", "head", "advance", "ride", "roll", "keep"}
    if any(w in msg.split() for w in _TRAVEL_WORDS) or not msg.strip():
        return {"action": "travel"}

    return {"action": "travel", "is_freeform": True}


def _handle_landmark_action(game: dict, message: str) -> dict:
    msg = message.lower()

    if any(kw in msg for kw in ["marketplace", "market", "shop", "store", "trade post"]):
        landmark = game.get("current_landmark", "")
        store_key = landmark.lower().replace(" ", "_").replace(",", "").replace(".", "")
        occupation = game.get("occupation", "carpenter")
        if not game.get("store_inventory"):
            game["store_inventory"] = store_engine.get_store_inventory(store_key, occupation)
            game["current_store"] = store_key
        return {"action": "select_marketplace"}

    if any(kw in msg for kw in ["buy", "purchase", "get", "trade"]):
        return _parse_buy_action(game, message)

    if msg.strip() == "scavenge for supplies":
        return {"action": "select_scavenge"}

    if any(kw in msg for kw in ["scavenge", "salvage", "search", "look for", "find", "forage"]):
        item = _extract_item(msg)
        result = scav_engine.attempt_scavenge(game, item)
        game = scav_engine.apply_scavenge_result(game, result)
        return {"action": "scavenge", "result": result}

    if any(kw in msg for kw in ["attack", "raid", "ambush", "rob", "caravan", "intercept"]):
        return _do_caravan_attack(game)

    if any(kw in msg for kw in ["rest", "sleep", "camp", "stay"]):
        game = cons_engine.apply_rest(game)
        game["day"] += 1
        return {"action": "rest"}

    if any(kw in msg for kw in ["medicine", "heal", "treat"]):
        target = _extract_name(game, message)
        if target:
            game, result = cond_engine.apply_medicine(game, target)
            return {"action": "use_medicine", "target": target, "result": result}

    leave_keywords = ["leave settlement", "leave", "continue", "head out", "hit the road", "move on", "depart", "push on"]
    if any(kw in msg for kw in leave_keywords):
        game["phase"] = "on_trail"
        game["current_landmark"] = None
        game["store_inventory"] = {}
        game["current_store"] = None
        return {"action": "leave_settlement"}

    if any(kw in msg for kw in ["look", "explore", "inspect", "check", "survey", "examine", "around", "what"]):
        return {"action": "talk"}

    return {"action": "talk", "is_freeform": True}


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


def _handle_stranded_action(game: dict, message: str) -> dict:
    import random
    msg = message.lower()

    # Walk on foot — slow progress, burns extra food/water
    if any(kw in msg for kw in ["walk", "foot", "hike", "march", "trek", "on foot", "keep moving", "continue", "move"]):
        cfg = get_config()
        miles = random.randint(10, 20)
        game["distance_traveled"] = game.get("distance_traveled", 0.0) + miles
        game = cons_engine.apply_walking_consumption(game)
        # Check if walking brought us to a landmark
        from engine.travel import _check_landmark_arrival, _set_next_landmark
        arrived = _check_landmark_arrival(game, cfg)
        if arrived:
            landmark = next((lm for lm in cfg["trail"]["landmarks"] if lm["name"] == arrived), None)
            game["current_landmark"] = arrived
            if landmark:
                game["terrain"] = landmark["terrain"]
                game["region"] = landmark["region"]
                game["phase"] = "at_landmark"
            _set_next_landmark(game, cfg, arrived)
            return {"action": "walk", "miles": miles, "arrived_at": arrived}
        return {"action": "walk", "miles": miles}

    # Scavenge for fuel
    if any(kw in msg for kw in ["scavenge", "search", "look", "find", "fuel", "gas", "petrol", "forage"]):
        import random
        chance = 0.35
        if game.get("terrain") in ["urban_ruins", "coastal"]:
            chance = 0.50
        elif game.get("terrain") in ["deep_desert", "high_desert"]:
            chance = 0.20
        if random.random() < chance:
            gallons = random.randint(5, 20)
            game["supplies"]["fuel_gallons"] = game["supplies"].get("fuel_gallons", 0) + gallons
            game["phase"] = "on_trail"
            return {"action": "scavenge_fuel", "found": True, "gallons": gallons}
        return {"action": "scavenge_fuel", "found": False}

    # Attack caravan
    if any(kw in msg for kw in ["attack", "raid", "ambush", "rob", "caravan", "vehicle", "intercept", "assault"]):
        return _do_caravan_attack(game)

    return {"action": "stranded_wait", "is_freeform": True}


def _do_caravan_attack(game: dict) -> dict:
    import random
    ammo  = game["supplies"].get("ammo_rounds", 0)
    alive = sum(1 for m in game["party"] if m["alive"])
    chance = min(0.75, 0.2 + (ammo / 100) * 0.3 + (alive / 4) * 0.25)
    ammo_spent = min(ammo, random.randint(5, 15))
    game["supplies"]["ammo_rounds"] = max(0, ammo - ammo_spent)

    was_stranded = game.get("phase") == "stranded"
    if random.random() < chance:
        fuel_gained  = random.randint(15, 40)
        food_gained  = round(random.uniform(2, 8), 1)
        trade_gained = random.randint(3, 12)
        game["supplies"]["fuel_gallons"] = round(game["supplies"].get("fuel_gallons", 0) + fuel_gained, 2)
        game["supplies"]["food_days"]    = round(game["supplies"].get("food_days", 0) + food_gained, 2)
        game["supplies"]["trade_goods"]  = game["supplies"].get("trade_goods", 0) + trade_gained
        if was_stranded:
            game["phase"] = "on_trail"
        return {"action": "attack_caravan", "success": True, "was_stranded": was_stranded,
                "fuel_gained": fuel_gained, "food_gained": food_gained,
                "trade_gained": trade_gained, "ammo_spent": ammo_spent}
    else:
        for member in game["party"]:
            if member["alive"]:
                member["health"] = max(0, member["health"] - random.randint(10, 25))
        return {"action": "attack_caravan", "success": False, "was_stranded": was_stranded,
                "ammo_spent": ammo_spent}


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

    from engine.travel import _set_next_landmark
    _set_next_landmark(game, cfg, "Mississippi Crossing")

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
    # Strip "— N goods" price suffix to avoid matching "goods" as trade_goods
    item_msg = msg.split("—")[0] if "—" in msg else msg
    found_item = None
    for keyword, item_key in item_map.items():
        if keyword in item_msg:
            found_item = item_key
            break

    if not found_item:
        return {"action": "browse", "message": "What would you like to buy?"}

    quantity = 1
    import re
    # Strip "— N goods" price suffix so "Buy fuel — 4 goods" doesn't parse 4 as quantity
    qty_msg = msg.split("—")[0] if "—" in msg else msg
    nums = re.findall(r'\b(\d+)\b', qty_msg)
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


def _invoke_with_retry(llm, messages, max_retries: int = 2):
    """Try primary model, then fall back through FALLBACK_MODELS on quota/not-found errors."""
    models_to_try = [llm] + [_get_llm(m) for m in _FALLBACK_MODELS[1:]]
    last_err = None
    for candidate in models_to_try:
        delay = 15
        for attempt in range(max_retries):
            try:
                return candidate.invoke(messages)
            except Exception as e:
                err = str(e)
                last_err = e
                if "429" in err or "RESOURCE_EXHAUSTED" in err:
                    if attempt < max_retries - 1:
                        time.sleep(delay)
                        delay *= 2
                        continue
                    break  # exhausted retries for this model, try next
                if "404" in err or "NOT_FOUND" in err:
                    break  # model gone, try next immediately
                raise  # unexpected error — surface it
    raise last_err


def narrate_node(state: GameState) -> dict:
    """Template-first narrator. LLM only fires for genuinely freeform player input."""
    game = dict(state["game"])
    messages = list(state.get("messages", []))
    last_player_message = messages[-1].content if messages else ""

    events = game.pop("_events_this_turn", [])
    action_context = game.pop("_action_context", {})

    # ── LLM path: freeform player input only ──────────────────────────────────
    if action_context.get("is_freeform") and not game.get("outcome"):
        game["_last_narrative"] = _llm_freeform(game, last_player_message, events, action_context)
        game["suggestions"] = get_suggestions(game, action_context.get("action", "travel"))
        return {**state, "game": game}

    # ── Template path: everything else ────────────────────────────────────────
    game["_last_narrative"] = build_narrative(game, action_context, events)
    game["suggestions"] = get_suggestions(game, action_context.get("action", "travel"))
    return {**state, "game": game}


def _llm_freeform(game: dict, player_message: str, events: list, action_context: dict) -> str:
    """Call the LLM for a freeform player message. Returns narrative string."""
    system_prompt = build_system_prompt(game)
    events_text = _summarize_events_brief(events, action_context)
    prompt = (
        f"Current state: Day {game.get('day')}, {game.get('distance_traveled', 0):.0f} miles traveled, "
        f"phase={game.get('phase')}, terrain={game.get('terrain')}, weather={game.get('weather')}.\n"
        f"Events this turn: {events_text}\n\n"
        f"PLAYER: {player_message}\n\n"
        "Respond with 2-4 sentences of in-world narrative. Plain text only, no JSON."
    )

    llm = _get_llm()
    try:
        response = _invoke_with_retry(llm, [
            SystemMessage(content=system_prompt),
            HumanMessage(content=prompt),
        ])
        return response.content.strip()
    except Exception as e:
        # Fallback to template if LLM fails
        from agent.templates import travel_narrative
        return travel_narrative(game, events)


def _summarize_events_brief(events: list, action_context: dict) -> str:
    if not events:
        return "none"
    parts = []
    for ev in events:
        if not isinstance(ev, dict):
            parts.append(str(ev))
            continue
        t = ev.get("type", "")
        if t == "disease":
            parts.append(f"{ev['victim']} contracted {ev['disease']}")
        elif t == "breakdown":
            parts.append(f"vehicle breakdown: {ev['breakdown']}")
        elif t == "raider":
            parts.append(f"raider encounter: {ev['result']}")
        elif t == "weather_change":
            parts.append(f"weather → {ev['new_weather']}")
        elif t == "starvation":
            parts.append("party starving")
        elif t == "dehydration":
            parts.append("party dehydrating")
        else:
            parts.append(t or "unknown event")
    return "; ".join(parts) if parts else "none"
