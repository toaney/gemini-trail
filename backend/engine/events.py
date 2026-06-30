import random
from .loader import get_config


def roll_daily_events(game: dict) -> list[dict]:
    """Roll for random events. Returns list of triggered events."""
    triggered = []

    disease = _roll_disease(game)
    if disease:
        triggered.append(disease)

    breakdown = _roll_breakdown(game)
    if breakdown:
        triggered.append(breakdown)

    raider = _roll_raider(game)
    if raider:
        triggered.append(raider)

    weather = _roll_weather_change(game)
    if weather:
        triggered.append(weather)

    return triggered


def _roll_disease(game: dict) -> dict | None:
    cfg = get_config()
    d_cfg = cfg["events"]["disease"]
    chance = d_cfg["base_chance_per_day"]

    mods = d_cfg["modifiers"]
    rations = game.get("rations", "filling")
    terrain = game.get("terrain", "plains")
    weather = game.get("weather", "clear")

    if rations == "bare_minimum":
        chance *= mods["bare_minimum_rations"]
    elif rations == "meager":
        chance *= mods["meager_rations"]
    if terrain == "swamp":
        chance *= mods["swamp_terrain"]
    if weather in ["storm", "rain"]:
        chance *= mods["bad_weather"]

    if random.random() > chance:
        return None

    alive = [m for m in game["party"] if m["alive"]]
    if not alive:
        return None

    victim = random.choice(alive)
    types = [t for t in d_cfg["types"] if "terrain_requirement" not in t or t["terrain_requirement"] == terrain]
    if not types:
        return None

    weights = [t["weight"] for t in types]
    disease_type = random.choices(types, weights=weights)[0]

    return {
        "type": "disease",
        "disease": disease_type["name"],
        "severity": disease_type["severity"],
        "victim": victim["name"],
        "health_damage": disease_type["health_damage_per_day"],
        "cure": disease_type["cure"],
    }


def _roll_breakdown(game: dict) -> dict | None:
    cfg = get_config()
    b_cfg = cfg["events"]["breakdown"]
    chance = b_cfg["base_chance_per_day"]

    mods = b_cfg["modifiers"]
    condition = game.get("vehicle_condition", 100)
    pace = game.get("pace", "steady")
    terrain = game.get("terrain", "plains")

    if condition < 25:
        chance *= mods["vehicle_condition_below_25"]
    elif condition < 50:
        chance *= mods["vehicle_condition_below_50"]
    if pace == "reckless":
        chance *= mods["reckless_pace"]
    if terrain in ["swamp", "urban_ruins", "deep_desert"]:
        chance *= mods["rough_terrain"]

    if random.random() > chance:
        return None

    types = b_cfg["types"]
    weights = [t["weight"] for t in types]
    breakdown_type = random.choices(types, weights=weights)[0]

    cost_range = breakdown_type["trade_goods_cost"]
    cost = random.randint(cost_range["min"], cost_range["max"])

    return {
        "type": "breakdown",
        "breakdown": breakdown_type["name"],
        "fix_with": breakdown_type["fix_with"],
        "trade_goods_cost": cost,
        "time_days": breakdown_type["time_days"],
        "vehicle_damage": breakdown_type.get("vehicle_damage", 0),
    }


def _roll_raider(game: dict) -> dict | None:
    cfg = get_config()
    r_cfg = cfg["events"]["raider_attack"]
    chance = r_cfg["base_chance_per_day"]

    mods = r_cfg["modifiers"]
    landmark = game.get("current_landmark", "")
    ammo = game["supplies"].get("ammo_rounds", 0)

    if landmark == "Las Vegas":
        chance *= mods["las_vegas_region"]
    if ammo < 10:
        chance *= mods["low_ammo_below_10"]

    if random.random() > chance:
        return None

    outcomes = r_cfg["outcomes"]
    weights = [o["weight"] for o in outcomes]
    outcome = random.choices(outcomes, weights=weights)[0]

    result = {"type": "raider", "result": outcome["result"]}

    if "ammo_cost" in outcome:
        cost = outcome["ammo_cost"]
        result["ammo_cost"] = random.randint(cost["min"], cost["max"])
    if "trade_goods_stolen" in outcome:
        stolen = outcome["trade_goods_stolen"]
        result["trade_goods_stolen"] = random.randint(stolen["min"], stolen["max"])
    if "health_damage" in outcome:
        dmg = outcome["health_damage"]
        if isinstance(dmg, dict):
            result["health_damage"] = random.randint(dmg["min"], dmg["max"])
        else:
            result["health_damage"] = dmg
    if "fuel_cost" in outcome:
        result["fuel_cost"] = outcome["fuel_cost"]

    return result


def _roll_weather_change(game: dict) -> dict | None:
    cfg = get_config()
    if random.random() > cfg["events"]["weather_change"]["chance_per_day"]:
        return None

    month = game.get("departure_month", "march").lower()
    dist = cfg["events"]["weather_change"]["distributions"].get(month, {})
    if not dist:
        return None

    weathers = list(dist.keys())
    weights = list(dist.values())
    new_weather = random.choices(weathers, weights=weights)[0]

    if new_weather == game.get("weather"):
        return None

    return {"type": "weather_change", "new_weather": new_weather}


def apply_events(game: dict, events: list[dict]) -> tuple[dict, list[dict]]:
    cfg = get_config()
    applied = []

    for event in events:
        if event["type"] == "disease":
            game, ev = _apply_disease(game, event, cfg)
            applied.append(ev)

        elif event["type"] == "breakdown":
            game, ev = _apply_breakdown(game, event, cfg)
            applied.append(ev)

        elif event["type"] == "raider":
            game, ev = _apply_raider(game, event)
            applied.append(ev)

        elif event["type"] == "weather_change":
            game["weather"] = event["new_weather"]
            applied.append(event)

    return game, applied


def _apply_disease(game: dict, event: dict, cfg: dict) -> tuple[dict, dict]:
    victim_name = event["victim"]
    damage = event["health_damage"]

    for member in game["party"]:
        if member["name"] == victim_name and member["alive"]:
            member["health"] = max(0, member["health"] - damage)
            member["status"] = event["disease"]
            break

    return game, event


def _apply_breakdown(game: dict, event: dict, cfg: dict) -> tuple[dict, dict]:
    occupation = game.get("occupation", "")
    parts_cfg = cfg["parts"]
    fix_with = event["fix_with"]
    auto_fixed = False

    parts_map = {
        "spare_tire": "spare_tires",
        "engine_kit": "engine_kits",
        "generic_parts": "generic_parts",
    }
    supply_key = parts_map.get(fix_with)

    if supply_key and game["supplies"].get(supply_key, 0) > 0:
        efficiency = parts_cfg[fix_with].get(
            "engineer_covers_events" if occupation == "engineer" else "carpenter_covers_events", 1
        )
        uses_per_kit = efficiency if occupation in ["engineer", "carpenter"] else 1
        game["supplies"][supply_key] = max(
            0, game["supplies"][supply_key] - (1 if uses_per_kit <= 1 else 0)
        )
        auto_fixed = True
        event["auto_fixed"] = True
    else:
        game["vehicle_condition"] = max(
            0, game["vehicle_condition"] - event.get("vehicle_damage", 0)
        )
        event["auto_fixed"] = False
        event["requires_action"] = True

    return game, event


def _apply_raider(game: dict, event: dict) -> tuple[dict, dict]:
    result = event["result"]

    if result == "repelled":
        ammo_used = event.get("ammo_cost", 0)
        game["supplies"]["ammo_rounds"] = max(
            0, game["supplies"]["ammo_rounds"] - ammo_used
        )
        dmg = event.get("health_damage", 0)
        if dmg > 0:
            alive = [m for m in game["party"] if m["alive"]]
            if alive:
                victim = random.choice(alive)
                victim["health"] = max(0, victim["health"] - dmg)

    elif result == "ambushed":
        stolen = event.get("trade_goods_stolen", 0)
        game["supplies"]["trade_goods"] = max(
            0, game["supplies"]["trade_goods"] - stolen
        )
        dmg = event.get("health_damage", 0)
        if dmg > 0:
            alive = [m for m in game["party"] if m["alive"]]
            if alive:
                victim = random.choice(alive)
                victim["health"] = max(0, victim["health"] - dmg)

    elif result == "fled":
        game["supplies"]["fuel_gallons"] = max(
            0.0, game["supplies"]["fuel_gallons"] - event.get("fuel_cost", 0)
        )

    return game, event
