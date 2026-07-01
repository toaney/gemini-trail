from .loader import get_config


def apply_daily_consumption(game: dict) -> dict:
    cfg = get_config()
    party = game["party"]
    alive_count = sum(1 for m in party if m["alive"])
    if alive_count == 0:
        return game

    cons = cfg["consumption"]
    rations = game.get("rations", "filling")
    terrain = game.get("terrain", "plains")
    weather = game.get("weather", "clear")

    food_rate = cons["food_days_per_person_per_day"][rations]
    game["supplies"]["food_days"] = max(
        0.0, game["supplies"]["food_days"] - food_rate * alive_count
    )

    heat_terrains = cfg["travel"].get("heat_zone_terrains", [])
    weather_water = cfg["events"]["weather_water_modifier"].get(weather, 1.0)
    is_heat = terrain in heat_terrains
    water_key = "heat_zone" if is_heat else "normal"
    water_rate = cons["water_days_per_person_per_day"][water_key] * weather_water
    game["supplies"]["water_days"] = max(
        0.0, game["supplies"]["water_days"] - water_rate * alive_count
    )

    pace = game.get("pace", "steady")
    fuel_key = "highway" if terrain not in ["swamp", "urban_ruins"] else "rough_terrain"
    pace_fuel_mult = {"steady": 1.0, "fast": 1.35, "reckless": 1.75}
    fuel_rate = cons["fuel_gallons_per_day"][fuel_key] * pace_fuel_mult.get(pace, 1.0)
    game["supplies"]["fuel_gallons"] = max(
        0.0, game["supplies"]["fuel_gallons"] - fuel_rate
    )

    vehicle_wear = cfg["vehicle"]["daily_wear"]
    if pace == "fast":
        vehicle_wear += cfg["vehicle"]["fast_pace_wear"]
    elif pace == "reckless":
        vehicle_wear += cfg["vehicle"]["reckless_pace_wear"]
    if terrain in ["swamp", "urban_ruins", "deep_desert"]:
        vehicle_wear += cfg["vehicle"]["rough_terrain_wear"]
    game["vehicle_condition"] = max(0, game["vehicle_condition"] - vehicle_wear)

    return game


_DESERT_TERRAINS = {"deep_desert", "high_desert"}

def apply_starvation(game: dict) -> tuple[dict, list[dict]]:
    """
    Survival windows:
      Food: ~7 days → 100hp / 7 ≈ 15 damage/day
      Water (normal): ~3 days → 100hp / 3 ≈ 34 damage/day
      Water (desert): ~2 days → 100hp / 2 = 50 damage/day
    """
    events = []
    terrain = game.get("terrain", "plains")

    if game["supplies"]["food_days"] <= 0:
        for member in game["party"]:
            if member["alive"]:
                member["health"] = max(0, member["health"] - 15)
        events.append({"type": "starvation"})

    if game["supplies"]["water_days"] <= 0:
        damage = 50 if terrain in _DESERT_TERRAINS else 34
        for member in game["party"]:
            if member["alive"]:
                member["health"] = max(0, member["health"] - damage)
        events.append({"type": "dehydration", "terrain": terrain})

    return game, events


def deprivation_modifiers(game: dict) -> dict:
    """
    Returns speed and scavenge success multipliers based on food/water status.
    Both stack multiplicatively if both are depleted.
    """
    food  = game["supplies"].get("food_days", 1)
    water = game["supplies"].get("water_days", 1)
    speed_mod  = 1.0
    scav_mod   = 1.0

    if food <= 0:
        speed_mod  *= 0.65   # 35% slower — weak from hunger
        scav_mod   *= 0.70   # 30% worse scavenging — can't concentrate

    if water <= 0:
        speed_mod  *= 0.50   # 50% slower — severe dehydration
        scav_mod   *= 0.60   # 40% worse scavenging — dizzy, impaired

    return {"speed": speed_mod, "scavenge": scav_mod}


def apply_walking_consumption(game: dict) -> dict:
    """Food/water burn while traveling on foot — no fuel used, higher exertion."""
    cfg = get_config()
    party = game["party"]
    alive_count = sum(1 for m in party if m["alive"])
    if alive_count == 0:
        return game

    cons = cfg["consumption"]
    rations = game.get("rations", "filling")

    # Walking burns 1.5x food vs driving
    food_rate = cons["food_days_per_person_per_day"][rations] * 1.5
    game["supplies"]["food_days"] = max(0.0, game["supplies"]["food_days"] - food_rate * alive_count)

    # Walking burns 1.5x water vs driving
    terrain = game.get("terrain", "plains")
    weather = game.get("weather", "clear")
    heat_terrains = cfg["travel"].get("heat_zone_terrains", [])
    weather_water = cfg["events"]["weather_water_modifier"].get(weather, 1.0)
    is_heat = terrain in heat_terrains
    water_key = "heat_zone" if is_heat else "normal"
    water_rate = cons["water_days_per_person_per_day"][water_key] * weather_water * 1.5
    game["supplies"]["water_days"] = max(0.0, game["supplies"]["water_days"] - water_rate * alive_count)

    return game


def apply_rest(game: dict) -> dict:
    cfg = get_config()
    recovery = cfg["health"]["rest_recovery_per_day"]
    for member in game["party"]:
        if member["alive"] and member["health"] > 0:
            member["health"] = min(100, member["health"] + recovery)
    if game.get("phase") != "stranded":
        game["supplies"]["fuel_gallons"] = max(
            0.0,
            game["supplies"]["fuel_gallons"] - cfg["consumption"]["fuel_gallons_per_day"]["rest_day"],
        )
    return game
