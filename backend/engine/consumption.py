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
    fuel_rate = cons["fuel_gallons_per_day"][fuel_key]
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


def apply_starvation(game: dict) -> tuple[dict, list[str]]:
    events = []
    if game["supplies"]["food_days"] <= 0:
        for member in game["party"]:
            if member["alive"]:
                member["health"] = max(0, member["health"] - 10)
        events.append("starvation")
    if game["supplies"]["water_days"] <= 0:
        for member in game["party"]:
            if member["alive"]:
                member["health"] = max(0, member["health"] - 15)
        events.append("dehydration")
    return game, events


def apply_rest(game: dict) -> dict:
    cfg = get_config()
    recovery = cfg["health"]["rest_recovery_per_day"]
    for member in game["party"]:
        if member["alive"] and member["health"] > 0:
            member["health"] = min(100, member["health"] + recovery)
    game["supplies"]["fuel_gallons"] = max(
        0.0,
        game["supplies"]["fuel_gallons"] - cfg["consumption"]["fuel_gallons_per_day"]["rest_day"],
    )
    return game
