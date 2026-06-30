import random
from .loader import get_config


def attempt_scavenge(game: dict, item: str | None = None) -> dict:
    cfg = get_config()
    scav = cfg["scavenging"]

    region = game.get("region", "west")
    at_landmark = game.get("current_landmark") is not None
    zone = f"{region}_{'city' if at_landmark else 'rural'}"

    success_rate = scav["success_rates"].get(zone, 0.25)
    yield_mult = scav["yield_multipliers"].get(zone, 0.6)

    if item == "medicine" and scav["item_exceptions"]["medicine"]["city_only"] and not at_landmark:
        return {"success": False, "item": "medicine", "reason": "Medicine only found near settlements."}

    if item == "fuel":
        fuel_exc = scav["item_exceptions"]["fuel"]
        success_rate = fuel_exc["base_success_rate"]
        if at_landmark:
            success_rate += fuel_exc["city_bonus"]

    if item == "ammo":
        ammo_exc = scav["item_exceptions"]["ammo"]
        if region == "west" and not at_landmark:
            success_rate += ammo_exc["west_rural_bonus"]
        elif region == "east" and at_landmark:
            success_rate = max(0.05, success_rate - ammo_exc["east_city_penalty"])

    if item == "water":
        water_exc = scav["item_exceptions"]["water"]
        if region == "west" and not at_landmark:
            success_rate += water_exc["west_rural_bonus"]
        elif region == "east" and at_landmark:
            success_rate = max(0.05, success_rate - water_exc["east_city_penalty"])

    if random.random() > success_rate:
        return {"success": False, "item": item}

    if not item:
        weights_cfg = scav["item_weights"].copy()
        if scav["item_exceptions"]["medicine"]["city_only"] and not at_landmark:
            weights_cfg.pop("medicine", None)
        items = list(weights_cfg.keys())
        weights = list(weights_cfg.values())
        item = random.choices(items, weights=weights)[0]

    yield_cfg = scav["scavenge_yields"][item]
    amount = random.randint(yield_cfg["min"], yield_cfg["max"])
    amount = max(1, int(amount * yield_mult))

    return {"success": True, "item": item, "amount": amount, "unit": yield_cfg["unit"]}


def apply_scavenge_result(game: dict, result: dict) -> dict:
    if not result.get("success"):
        return game

    item = result["item"]
    amount = result["amount"]
    supplies = game["supplies"]

    if item == "food":
        supplies["food_days"] = round(supplies["food_days"] + amount, 2)
    elif item == "water":
        supplies["water_days"] = round(supplies["water_days"] + amount, 2)
    elif item == "ammo":
        supplies["ammo_rounds"] += amount
    elif item == "medicine":
        supplies["medicine_kits"] += amount
    elif item == "fuel":
        supplies["fuel_gallons"] = round(supplies["fuel_gallons"] + amount, 2)

    return game
