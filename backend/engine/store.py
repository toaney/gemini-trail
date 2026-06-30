from .loader import get_config


def get_store_inventory(landmark_key: str, occupation: str) -> dict:
    cfg = get_config()
    store_cfg = cfg["store"].get(landmark_key)
    if not store_cfg:
        return {}

    inventory = {}
    for item, data in store_cfg["inventory"].items():
        if data.get("available", True):
            inventory[item] = {
                "price": data["price"],
                "stock": data["stock"],
                "unit": data.get("unit", ""),
                "available": True,
            }

    if occupation == "bunker_ceo" and store_cfg.get("hidden_stock"):
        for item, data in store_cfg["hidden_stock"].items():
            if item not in inventory:
                inventory[item] = {
                    "price": data["price"],
                    "stock": data["stock"],
                    "unit": data.get("unit", ""),
                    "available": True,
                    "hidden": True,
                }

    return inventory


def calculate_price(base_price: int, store_cfg: dict, occupation: str, cfg: dict) -> int:
    settlement_mod = store_cfg.get("trade_modifier", 1.0)
    occ_mod = cfg["occupations"][occupation].get("trade_modifier", 1.0)
    return max(1, round(base_price * settlement_mod / occ_mod))


def buy_item(game: dict, item: str, quantity: int, landmark_key: str) -> tuple[dict, str]:
    cfg = get_config()
    store_cfg = cfg["store"].get(landmark_key)
    if not store_cfg:
        return game, "No store at this location."

    occupation = game.get("occupation", "carpenter")
    inventory = game.get("store_inventory", {})

    if item not in inventory or not inventory[item].get("available"):
        return game, f"{item} is not available here."

    available_stock = inventory[item]["stock"]
    if quantity > available_stock:
        return game, f"Only {available_stock} {item} in stock."

    base_price = inventory[item]["price"]
    price_per_unit = calculate_price(base_price, store_cfg, occupation, cfg)
    total_cost = price_per_unit * quantity

    if game["supplies"]["trade_goods"] < total_cost:
        return game, f"Not enough trade goods. Need {total_cost}, have {game['supplies']['trade_goods']}."

    game["supplies"]["trade_goods"] -= total_cost
    inventory[item]["stock"] -= quantity
    if inventory[item]["stock"] == 0:
        inventory[item]["available"] = False
    game["store_inventory"] = inventory

    supply_map = {
        "food":          ("food_days",      3.0 * quantity),
        "water":         ("water_days",     3.0 * quantity),
        "medicine":      ("medicine_kits",  quantity),
        "ammo":          ("ammo_rounds",    20 * quantity),
        "fuel":          ("fuel_gallons",   5.0 * quantity),
        "spare_tire":    ("spare_tires",    quantity),
        "engine_kit":    ("engine_kits",    quantity),
        "generic_parts": ("generic_parts",  quantity),
        "trade_goods":   ("trade_goods",    5 * quantity),
    }

    if item in supply_map:
        key, amount = supply_map[item]
        current = game["supplies"].get(key, 0)
        game["supplies"][key] = round(current + amount, 2)

    return game, f"Bought {quantity} {item} for {total_cost} trade goods."
