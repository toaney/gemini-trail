from .loader import get_config


HEALTH_LABELS = [
    (75, "Good"),
    (45, "Fair"),
    (20, "Poor"),
    (1,  "Critical"),
]


def update_health_labels(game: dict) -> dict:
    for member in game["party"]:
        if not member["alive"]:
            continue
        if member["health"] <= 0:
            member["alive"] = False
            member["health"] = 0
            member["health_label"] = "Dead"
            member["status"] = "dead"
        else:
            for threshold, label in HEALTH_LABELS:
                if member["health"] >= threshold:
                    member["health_label"] = label
                    break
    return game


def check_win_loss(game: dict) -> tuple[str | None, str | None]:
    cfg = get_config()
    total = cfg["trail"]["total_distance"]

    if game.get("distance_traveled", 0) >= total or game.get("current_landmark") == "Washington DC":
        return "win", "You reached Washington, DC."

    alive_count = sum(1 for m in game["party"] if m["alive"])
    if alive_count == 0:
        return "loss", "Your entire party has perished."

    if game["supplies"].get("fuel_gallons", 0) <= 0 and game.get("phase") == "on_trail":
        return "loss", "You ran out of fuel and are stranded."

    if game.get("vehicle_condition", 100) <= 0:
        return "loss", "Your vehicle is destroyed."

    if game.get("day", 0) >= cfg["game_over"]["max_days"]:
        return "loss", f"You ran out of time after {game['day']} days on the road."

    return None, None


def get_alive_count(game: dict) -> int:
    return sum(1 for m in game["party"] if m["alive"])


def apply_morale_death_penalty(game: dict, deaths: int) -> dict:
    cfg = get_config()
    penalty = cfg["health"]["morale_death_penalty"] * deaths
    for member in game["party"]:
        if member["alive"]:
            member["health"] = max(1, member["health"] - penalty)
    return game


def apply_medicine(game: dict, target_name: str) -> tuple[dict, str]:
    cfg = get_config()
    if game["supplies"].get("medicine_kits", 0) <= 0:
        return game, "No medicine kits remaining."

    for member in game["party"]:
        if member["name"].lower() == target_name.lower() and member["alive"]:
            recovery = cfg["health"]["medicine_recovery_per_kit"]
            member["health"] = min(100, member["health"] + recovery)
            member["status"] = "recovering"
            game["supplies"]["medicine_kits"] -= 1
            return game, f"Used 1 medicine kit on {member['name']}."

    return game, f"No living party member named {target_name}."
