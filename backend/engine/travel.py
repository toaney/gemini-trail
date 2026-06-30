from .loader import get_config


def calculate_distance(game: dict) -> float:
    cfg = get_config()
    travel = cfg["travel"]
    pace = game.get("pace", "steady")
    terrain = game.get("terrain", "plains")
    weather = game.get("weather", "clear")

    base = travel["base_miles_per_day"][pace]
    terrain_mod = travel["terrain_modifier"].get(terrain, 1.0)
    weather_mod = cfg["events"]["weather_travel_modifier"].get(weather, 1.0)

    return base * terrain_mod * weather_mod


def advance_travel(game: dict) -> tuple[dict, str | None]:
    """Move the party forward one day. Returns updated game and landmark name if arrived."""
    cfg = get_config()
    miles = calculate_distance(game)
    game["distance_traveled"] = game.get("distance_traveled", 0.0) + miles
    game["day"] = game.get("day", 0) + 1

    arrived_at = _check_landmark_arrival(game, cfg)
    if arrived_at:
        landmark = next(
            lm for lm in cfg["trail"]["landmarks"] if lm["name"] == arrived_at
        )
        game["current_landmark"] = arrived_at
        game["terrain"] = landmark["terrain"]
        game["region"] = landmark["region"]
        game["phase"] = "event" if landmark["type"] == "event" else "at_landmark"
        _set_next_landmark(game, cfg, arrived_at)

    return game, arrived_at


def _check_landmark_arrival(game: dict, cfg: dict) -> str | None:
    dist = game["distance_traveled"]
    total = cfg["trail"]["total_distance"]

    if dist >= total:
        return "Washington DC"

    for lm in cfg["trail"]["landmarks"]:
        if game.get("current_landmark") != lm["name"]:
            if dist >= lm["mile"]:
                if game.get("next_landmark") == lm["name"]:
                    return lm["name"]
    return None


def _set_next_landmark(game: dict, cfg: dict, current_name: str) -> None:
    landmarks = cfg["trail"]["landmarks"]
    names = [lm["name"] for lm in landmarks] + ["Washington DC"]
    try:
        idx = names.index(current_name)
        game["next_landmark"] = names[idx + 1] if idx + 1 < len(names) else "Washington DC"
    except ValueError:
        game["next_landmark"] = "Washington DC"


def get_current_terrain(game: dict) -> str:
    cfg = get_config()
    dist = game.get("distance_traveled", 0.0)
    landmarks = cfg["trail"]["landmarks"]

    prev_terrain = "coastal"
    for lm in landmarks:
        if dist < lm["mile"]:
            return prev_terrain
        prev_terrain = lm["terrain"]
    return prev_terrain


def get_current_region(game: dict) -> str:
    dist = game.get("distance_traveled", 0.0)
    return "east" if dist >= 2005 else "west"


def miles_to_next_landmark(game: dict) -> float:
    cfg = get_config()
    dist = game.get("distance_traveled", 0.0)
    next_name = game.get("next_landmark", "Las Vegas")

    if next_name == "Washington DC":
        return max(0.0, cfg["trail"]["total_distance"] - dist)

    for lm in cfg["trail"]["landmarks"]:
        if lm["name"] == next_name:
            return max(0.0, lm["mile"] - dist)
    return 0.0
