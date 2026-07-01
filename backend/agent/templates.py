"""
Template-based narrative generation — no LLM required.
All game situations have a canned narrative except genuinely freeform player input.
"""

import random

# ── Terrain / weather lookup tables ──────────────────────────────────────────

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

_WEATHER_CHANGE_LINE = {
    "clear":        "The sky clears. Visibility improves.",
    "cloudy":       "Clouds roll in, grey and heavy.",
    "rain":         "Rain begins, steady and cold.",
    "storm":        "A storm closes in fast. Lightning in the distance.",
    "extreme_heat": "The temperature spikes. Heat shimmers off the road.",
    "extreme_cold": "A cold front hits. The temperature drops sharply.",
}

# ── Supply warning helper ─────────────────────────────────────────────────────

def _supply_warnings(supplies: dict) -> str:
    food  = supplies.get("food_days", 0)
    water = supplies.get("water_days", 0)
    fuel  = supplies.get("fuel_gallons", 0)
    warnings = []
    if food < 5:     warnings.append("food critically low")
    elif food < 15:  warnings.append("food running short")
    if water < 3:    warnings.append("water nearly gone")
    elif water < 10: warnings.append("water getting scarce")
    if fuel < 10:    warnings.append("fuel dangerously low")
    elif fuel < 20:  warnings.append("fuel dropping")
    return f" Warning: {', '.join(warnings)}." if warnings else ""


# ── Event narrative lines ─────────────────────────────────────────────────────

def _event_lines(events: list[dict]) -> list[str]:
    lines = []
    for ev in events:
        t = ev.get("type")

        if t == "disease":
            victim  = ev.get("victim", "Someone")
            disease = ev.get("disease", "illness")
            _DISEASE_LINES = {
                "radiation_sickness": f"{victim} starts showing signs of radiation sickness — nausea, fatigue, hair falling in clumps.",
                "infected_wound":     f"{victim}'s wound has gone bad. Red streaks crawl up the skin.",
                "dysentery":          f"{victim} doubles over with cramps. Dysentery. The worst timing.",
                "heat_exhaustion":    f"{victim} is fading fast in the heat. Heat exhaustion setting in.",
                "fever":              f"{victim} has spiked a fever, skin slick with sweat.",
            }
            lines.append(_DISEASE_LINES.get(disease, f"{victim} has fallen ill with {disease.replace('_', ' ')}."))

        elif t == "breakdown":
            kind      = ev.get("breakdown", "mechanical issue")
            fixed     = ev.get("auto_fixed", False)
            _BREAKDOWN_LINES = {
                "flat_tire":      ("A tire blows with a gunshot crack.", "Spare tire deployed. Back on the road."),
                "engine_failure": ("The engine coughs and dies. Oil everywhere.", "Engine kit used. It's running rough but running."),
                "minor_damage":   ("Something snaps underneath — suspension or worse.", "Parts on hand. Damage contained."),
            }
            fail_line, fix_line = _BREAKDOWN_LINES.get(kind, (f"Breakdown: {kind.replace('_', ' ')}.", "Repairs made."))
            lines.append(fail_line + (" " + fix_line if fixed else " No parts to fix it. Condition worsens."))

        elif t == "raider":
            result = ev.get("result", "fled")
            ammo   = ev.get("ammo_cost", 0)
            stolen = ev.get("trade_goods_stolen", 0)
            if result == "repelled":
                lines.append(f"Raiders hit from the flanks. Held them off — {ammo} rounds spent.")
            elif result == "ambushed":
                lines.append(f"Ambushed. They took {stolen} trade goods before you could react.")
            elif result == "fled":
                lines.append("Raiders on the road. Floored it and burned fuel to get clear.")

        elif t == "weather_change":
            new_w = ev.get("new_weather", "clear")
            lines.append(_WEATHER_CHANGE_LINE.get(new_w, f"Weather shifts to {new_w.replace('_', ' ')}."))

        elif t == "starvation":
            lines.append("No food. The party is weakening from hunger.")

        elif t == "dehydration":
            lines.append("No water. Dehydration is setting in — everyone is suffering.")

    return lines


# ── Main travel / on-trail templates ─────────────────────────────────────────

def travel_narrative(game: dict, events: list[dict]) -> str:
    day     = game.get("day", 0)
    dist    = game.get("distance_traveled", 0.0)
    terrain = game.get("terrain", "plains")
    weather = game.get("weather", "clear")
    next_lm = game.get("next_landmark", "the next settlement")

    terrain_desc = _TERRAIN_DESC.get(terrain, "down the broken road")
    weather_line = _WEATHER_LINE.get(weather, "")

    parts = [f"Day {day}. You push {terrain_desc}. {weather_line}".strip()]
    parts.append(f"{dist:.0f} miles from Long Beach. Next stop: {next_lm}.")
    parts.extend(_event_lines(events))
    parts.append(_supply_warnings(game.get("supplies", {})))
    return " ".join(p for p in parts if p.strip())


def pace_narrative(game: dict, events: list[dict]) -> str:
    day  = game.get("day", 0)
    dist = game.get("distance_traveled", 0.0)
    pace = game.get("pace", "steady")
    next_lm = game.get("next_landmark", "the next settlement")

    _PACE_LINES = {
        "steady":   "You ease off, settling into a steady, fuel-conscious rhythm.",
        "fast":     "You push harder. The engine climbs, eating up road.",
        "reckless": "Pedal down. The vehicle screams east. Every mile costs.",
    }
    parts = [f"Day {day}. {_PACE_LINES.get(pace, 'Pace adjusted.')}"]
    parts.append(f"{dist:.0f} miles from Long Beach. Next stop: {next_lm}.")
    parts.extend(_event_lines(events))
    parts.append(_supply_warnings(game.get("supplies", {})))
    return " ".join(p for p in parts if p.strip())


def rations_narrative(game: dict, events: list[dict]) -> str:
    day     = game.get("day", 0)
    dist    = game.get("distance_traveled", 0.0)
    rations = game.get("rations", "filling")
    next_lm = game.get("next_landmark", "the next settlement")

    _RATIONS_LINES = {
        "meager":       "Rations cut. Everyone gets less. Hunger joins the ride.",
        "bare_minimum": "Bare minimum issued. Just enough to keep moving.",
        "filling":      "Full rations restored. The party eats properly for now.",
        "normal":       "Rations back to normal.",
    }
    parts = [f"Day {day}. {_RATIONS_LINES.get(rations, 'Rations adjusted.')}"]
    parts.append(f"{dist:.0f} miles from Long Beach. Next stop: {next_lm}.")
    parts.extend(_event_lines(events))
    parts.append(_supply_warnings(game.get("supplies", {})))
    return " ".join(p for p in parts if p.strip())


def rest_narrative(game: dict, events: list[dict]) -> str:
    day     = game.get("day", 0)
    dist    = game.get("distance_traveled", 0.0)
    terrain = game.get("terrain", "plains")
    weather = game.get("weather", "clear")
    next_lm = game.get("next_landmark", "the next settlement")

    terrain_desc = _TERRAIN_DESC.get(terrain, "on the road")
    weather_line = _WEATHER_LINE.get(weather, "")

    parts = [f"Day {day}. The party makes camp {terrain_desc}. {weather_line}".strip()]
    parts.append("You rest through the night.")
    parts.append(f"{dist:.0f} miles from Long Beach. Next stop: {next_lm}.")
    parts.extend(_event_lines(events))
    parts.append(_supply_warnings(game.get("supplies", {})))
    return " ".join(p for p in parts if p.strip())


def scavenge_narrative(game: dict, action_context: dict, events: list[dict]) -> str:
    result = action_context.get("result", {})
    found  = result.get("found", False)
    item   = result.get("item", "supplies")
    qty    = result.get("quantity", 0)

    if found:
        line = f"You search the area and turn up {qty} {item.replace('_', ' ')}. Worth the stop."
    else:
        line = "You pick through the ruins. Nothing useful. Time wasted."

    parts = [line]
    parts.extend(_event_lines(events))
    parts.append(_supply_warnings(game.get("supplies", {})))
    return " ".join(p for p in parts if p.strip())


def medicine_narrative(game: dict, action_context: dict, events: list[dict]) -> str:
    target = action_context.get("target", "the patient")
    result = action_context.get("result", "")
    parts  = [result or f"You administer medicine to {target}."]
    parts.extend(_event_lines(events))
    return " ".join(p for p in parts if p.strip())


def depart_narrative(game: dict) -> str:
    month = game.get("departure_month", "march").capitalize()
    return (
        f"The engine catches on the second turn. {month} air, already warm, "
        "fills the cab as Long Beach falls behind. The road east begins."
    )


# ── Landmark arrival templates ────────────────────────────────────────────────

_LANDMARK_ARRIVALS = {
    "Las Vegas": (
        "The Strip emerges from the haze — a graveyard of neon and broken glass. "
        "Raiders have carved it into a black market. Eyes on you the moment you roll in. "
        "Trade fast, trust no one, leave faster."
    ),
    "Phoenix": (
        "Phoenix is a scorched maze of collapsed overpasses and stripped strip malls. "
        "A survivor camp holds the north edge — wary but willing to trade. "
        "The heat here is its own kind of hostile."
    ),
    "Roswell": (
        "Roswell. The cult hit this place before anyone else could. "
        "They believe the collapse was extraterrestrial — a cleansing. "
        "Strange murals cover every building. They'll trade, but they're watching."
    ),
    "Fort Worth": (
        "Fort Worth is the biggest thing you've seen since Long Beach. "
        "Texas militia runs it hard — checkpoints, armed guards, strict rules. "
        "But the walls hold, and the shelves aren't empty."
    ),
    "Shreveport": (
        "The bayou smell hits before the city does. Shreveport is half-submerged and fully lawless. "
        "Disease runs through the streets, but so does medicine — if you can afford it."
    ),
    "Mississippi Crossing": (
        "The river. You can hear it before you see it. "
        "The bridges are down — every one of them, twisted metal rusting in the current. "
        "You'll need to choose how to cross: brave the old bridge ruins, hire the ferryman, "
        "build a raft, or find a detour."
    ),
    "Tuscaloosa": (
        "The stadium rises out of the treeline like a fortress — because it is one. "
        "A farming commune turned it into the most defensible structure in Alabama. "
        "They're suspicious of strangers but honest in trade."
    ),
    "Atlanta": (
        "Atlanta never stopped fighting. Faction banners hang from every building. "
        "It's the most dangerous stop on the route and the best-supplied. "
        "Navigate the politics carefully."
    ),
    "Charleston": (
        "Salt air. The ocean. "
        "Charleston's naval faction controls the harbor and everything that moves through it. "
        "It's the closest thing to civilization you've seen. That makes it valuable and expensive."
    ),
    "Washington DC": (
        "The Capitol dome appears through the trees — cracked, weathered, still standing. "
        "You made it. Three thousand miles of broken road, and you made it. "
        "Whatever comes next, it starts here."
    ),
}

def landmark_arrival_narrative(game: dict, landmark_name: str) -> str:
    day  = game.get("day", 0)
    dist = game.get("distance_traveled", 0.0)
    base = _LANDMARK_ARRIVALS.get(landmark_name, f"You arrive at {landmark_name}.")
    return f"Day {day}. {dist:.0f} miles from Long Beach.\n\n{base}"


# ── At-landmark templates ─────────────────────────────────────────────────────

_LANDMARK_BROWSE = {
    "Las Vegas": "You move through the market stalls, eyes peeled. Everything has a price here, and most of it's marked up.",
    "Phoenix":   "The camp is sparse but organized. Survivors here have learned to stockpile what matters.",
    "Roswell":   "The cult's traders eye you sideways. Their goods are genuine enough.",
    "Fort Worth": "The militia quartermaster runs a tight inventory. Prices are fair, no haggling.",
    "Shreveport": "The market here reeks of swamp and desperation. Stalls everywhere, half of it junk.",
    "Tuscaloosa": "The commune trades in staples — food, basic parts. Not much else.",
    "Atlanta":    "Three factions, three markets. You'll need to pick your side or stay neutral.",
    "Charleston": "The naval stores are well-stocked and properly priced. Closest thing to before.",
}

def landmark_browse_narrative(game: dict) -> str:
    landmark = game.get("current_landmark", "the settlement")
    return _LANDMARK_BROWSE.get(landmark, f"You look around {landmark}. Survivors go about their business.")


def buy_narrative(game: dict, action_context: dict) -> str:
    result = action_context.get("result", "")
    return result or "Transaction complete."


def leave_settlement_narrative(game: dict) -> str:
    landmark = game.get("current_landmark") or "the settlement"
    _LEAVE = {
        "Las Vegas":   "The Strip shrinks in the rearview. Good riddance.",
        "Phoenix":     "Phoenix disappears into the heat shimmer. East.",
        "Roswell":     "The cult's painted eyes watch you leave. You don't look back.",
        "Fort Worth":  "The militia checkpoint waves you through. The plains open up ahead.",
        "Shreveport":  "The bayou smell fades. The road lifts out of the swamp.",
        "Tuscaloosa":  "The stadium walls recede into the treeline.",
        "Atlanta":     "Atlanta's faction towers disappear behind you.",
        "Charleston":  "The harbor fades. The road north awaits.",
    }
    return _LEAVE.get(landmark, f"You leave {landmark} behind and push on.")


# ── Mississippi crossing templates ────────────────────────────────────────────

def stranded_intro_narrative(game: dict) -> str:
    day  = game.get("day", 0)
    dist = game.get("distance_traveled", 0.0)
    terrain = game.get("terrain", "plains")
    terrain_desc = _TERRAIN_DESC.get(terrain, "on the road")
    return (
        f"Day {day}. The engine sputters and dies. Fuel gauge reads empty. "
        f"The vehicle rolls to a stop {terrain_desc}, {dist:.0f} miles from Long Beach. "
        f"Silence. You're stranded. "
        f"Options: push on foot, scavenge the area for fuel, or take what you need from whoever passes."
    )


def stranded_walk_narrative(game: dict, action_context: dict) -> str:
    miles   = action_context.get("miles", 0)
    day     = game.get("day", 0)
    dist    = game.get("distance_traveled", 0.0)
    terrain = game.get("terrain", "plains")
    arrived = action_context.get("arrived_at")
    terrain_desc = _TERRAIN_DESC.get(terrain, "down the road")

    if arrived:
        return (
            f"Day {day}. You cover {miles} miles on foot {terrain_desc}. "
            f"Legs burning, packs heavy. {arrived} appears on the horizon. "
            f"You limp into the settlement. Maybe someone here has fuel."
        )
    next_lm = game.get("next_landmark", "the next settlement")
    warn = _supply_warnings(game.get("supplies", {}))
    return (
        f"Day {day}. {miles} miles on foot {terrain_desc}. "
        f"{dist:.0f} miles from Long Beach. Still heading for {next_lm}.{warn}"
    )


def stranded_scavenge_narrative(game: dict, action_context: dict) -> str:
    found   = action_context.get("found", False)
    gallons = action_context.get("gallons", 0)
    terrain = game.get("terrain", "plains")

    if found:
        _FOUND_LINES = {
            "urban_ruins": f"You tear through abandoned garages and parking structures. Pay dirt — {gallons} gallons in a buried cache.",
            "coastal":     f"An old marina storage shed, half-collapsed but intact inside. {gallons} gallons of diesel. It'll do.",
            "plains":      f"A rusted farm truck behind a collapsed barn. You siphon every drop. {gallons} gallons.",
            "woodland":    f"A hidden camp, long abandoned. Whoever was here left fuel behind. {gallons} gallons.",
            "swamp":       f"A supply cache half-submerged in the mud. Waterlogged but the fuel cans are sealed. {gallons} gallons.",
            "deep_desert": f"Against the odds — a buried drum under a rock cairn. Survivor stash. {gallons} gallons.",
            "high_desert": f"A wrecked pickup off the shoulder, tank mostly intact. You siphon {gallons} gallons.",
        }
        found_line = _FOUND_LINES.get(terrain, f"You find {gallons} gallons of fuel. Back on the road.")
        return f"{found_line} The engine turns over. You're moving again."
    else:
        _EMPTY_LINES = {
            "urban_ruins": "Hours of searching through the ruins. Every tank drained, every can empty. Nothing.",
            "deep_desert": "The desert gives nothing. Miles of scrub and rock and not a drop of fuel anywhere.",
            "plains":      "Flat land, no cover, no abandoned vehicles. You come back empty-handed.",
            "swamp":       "The swamp swallowed everything useful years ago. No fuel to be found.",
        }
        return _EMPTY_LINES.get(terrain, "You search the area thoroughly. No fuel. Not today.")


def stranded_caravan_narrative(game: dict, action_context: dict) -> str:
    success      = action_context.get("success", False)
    fuel_gained  = action_context.get("fuel_gained", 0)
    food_gained  = action_context.get("food_gained", 0)
    trade_gained = action_context.get("trade_gained", 0)
    ammo_spent   = action_context.get("ammo_spent", 0)
    was_stranded = action_context.get("was_stranded", False)

    if success:
        loot_parts = []
        if fuel_gained:
            loot_parts.append(f"{fuel_gained} gallons of fuel")
        if food_gained:
            loot_parts.append(f"{food_gained} days of food")
        if trade_gained:
            loot_parts.append(f"{trade_gained} trade goods")
        loot_str = ", ".join(loot_parts) if loot_parts else "some supplies"
        tail = " The engine starts." if was_stranded else ""
        return (
            f"A vehicle convoy rolls into view. You set the ambush fast. "
            f"Shots fired — {ammo_spent} rounds. They don't fight back long. "
            f"You take {loot_str}. They scatter into the dust. You don't think about it too hard.{tail}"
        )
    else:
        tail = " You're still stranded, and now you're hurt." if was_stranded else " Nothing gained."
        return (
            f"The ambush goes wrong. They're armed and ready. "
            f"{ammo_spent} rounds wasted, and your people took hits before you pulled back. "
            f"The convoy disappears east.{tail}"
        )


def river_crossing_narrative(game: dict, action_context: dict) -> str:
    method  = action_context.get("method", "bridge")
    blocked = action_context.get("blocked", False)
    damage  = action_context.get("vehicle_damage", 0)
    days    = action_context.get("days", 1)

    if blocked:
        reason = action_context.get("reason", "You can't use that method right now.")
        return f"Crossing blocked. {reason}"

    _CROSSING = {
        "bridge": (
            f"The old bridge holds — barely. Twisted metal groans under the weight. "
            f"{days} day{'s' if days > 1 else ''} picking through the wreckage. "
            f"Vehicle took {damage} damage, but you're across."
        ),
        "ferry": (
            f"The ferryman demands his price and gets it. "
            f"The barge is slow and the current is strong, but {days} day{'s' if days > 1 else ''} later "
            f"you're on the east bank. Worth every trade good."
        ),
        "raft": (
            f"You build a raft from scavenged timber and float across. "
            f"{days} day{'s' if days > 1 else ''} of work. "
            f"Vehicle took {damage} damage in the crossing. But you're through."
        ),
        "detour": (
            f"The long way around — {days} day{'s' if days > 1 else ''} of back roads and flooded bridges. "
            f"Slower, but the vehicle survives intact. You rejoin the highway east of the river."
        ),
    }
    return _CROSSING.get(method, "You cross the Mississippi and push east.")


# ── Suggestions by phase / action ────────────────────────────────────────────

_TRAIL_SUGGESTIONS = [
    "Continue traveling",
    "Rest for the day",
    "Scavenge for supplies",
    "Change pace",
]

_PACE_SUGGESTIONS = [
    "Steady pace (safe, fuel-efficient)",
    "Fast pace (more ground, more fuel)",
    "Reckless pace (fastest, wears vehicle)",
    "Keep current pace",
]

_SCAVENGE_SUGGESTIONS = [
    "Salvage nearby junk",
    "Look for water",
    "Attack a passing caravan",
]

_LANDMARK_SUGGESTIONS = [
    "Go to marketplace",
    "Rest for the day",
    "Scavenge for supplies",
    "Leave settlement",
]

_MISSISSIPPI_SUGGESTIONS = [
    "Cross the old bridge (risky, free)",
    "Pay the ferryman (costs trade goods)",
    "Build a raft (slow, damages vehicle)",
    "Find a detour (long way around)",
]

_STRANDED_SUGGESTIONS = [
    "Walk on foot",
    "Scavenge for fuel",
    "Attack a passing caravan",
    "Rest and conserve supplies",
]


def _store_suggestions(game: dict) -> list[str]:
    from engine.loader import get_config
    cfg        = get_config()
    store_key  = game.get("current_store", "")
    store_cfg  = cfg.get("store", {}).get(store_key, {})
    occupation = game.get("occupation", "carpenter")
    trade_mod  = store_cfg.get("trade_modifier", 1.0)
    occ_mod    = cfg["occupations"][occupation].get("trade_modifier", 1.0)

    # Use live game inventory (reflects sold-out state), not config
    live_inventory = game.get("store_inventory", {})

    def price_str(item: str) -> str | None:
        data = live_inventory.get(item, {})
        if not data.get("available", True):
            return None
        p = data.get("price")
        if p is None:
            return None
        return str(max(1, round(p * trade_mod / occ_mod)))

    is_prep = game.get("phase") == "preparation"

    suggestions = []
    for item, label in [("food", "Buy food"), ("water", "Buy water"), ("fuel", "Buy fuel")]:
        p = price_str(item)
        if p:
            suggestions.append(f"{label} — {p} goods")

    for item, label in [
        ("medicine",      "Buy medicine"),
        ("ammo",          "Buy ammo"),
        ("spare_tire",    "Buy spare tire"),
        ("engine_kit",    "Buy engine kit"),
        ("generic_parts", "Buy parts"),
    ]:
        p = price_str(item)
        if p:
            suggestions.append(f"{label} — {p} goods")

    suggestions.append("Leave the settlement" if not is_prep else "Head out — begin the journey")
    return suggestions


def _any_supply_zero(game: dict) -> bool:
    s = game.get("supplies", {})
    return (
        s.get("fuel_gallons", 1) <= 0
        or s.get("food_days", 1) <= 0
        or s.get("water_days", 1) <= 0
        or s.get("ammo_rounds", 1) <= 0
    )


def get_suggestions(game: dict, action: str) -> list[str]:
    phase    = game.get("phase", "on_trail")
    landmark = game.get("current_landmark", "")

    if phase == "preparation":
        return _store_suggestions(game) if game.get("current_store") else [
            "Buy food", "Buy water", "Buy fuel", "Begin the journey"
        ]
    if phase == "stranded":
        return _STRANDED_SUGGESTIONS
    if landmark == "Mississippi Crossing":
        return _MISSISSIPPI_SUGGESTIONS
    if phase in ("at_landmark", "event"):
        if action in ("select_marketplace", "buy"):
            return _store_suggestions(game)
        if action == "select_scavenge":
            return list(_SCAVENGE_SUGGESTIONS)
        return list(_LANDMARK_SUGGESTIONS)

    if action == "select_pace":
        return list(_PACE_SUGGESTIONS)

    if action == "select_scavenge":
        return list(_SCAVENGE_SUGGESTIONS)

    return list(_TRAIL_SUGGESTIONS)


# ── Router: pick the right template ──────────────────────────────────────────

def build_narrative(game: dict, action_context: dict, events: list[dict]) -> str:
    action   = action_context.get("action", "travel")
    arrived  = action_context.get("arrived_at")

    if arrived:
        return landmark_arrival_narrative(game, arrived)

    if action == "depart":
        return depart_narrative(game)
    if action == "select_pace":
        pace = game.get("pace", "steady")
        return f"Current pace: {pace}. Choose a new pace below."
    if action == "select_scavenge":
        return "What are you looking for? Choose below."
    if action == "select_marketplace":
        landmark = game.get("current_landmark", "the settlement")
        return f"You make your way to the market at {landmark}. Trade goods line the stalls."
    if action == "travel":
        return travel_narrative(game, events)
    if action == "change_pace":
        return pace_narrative(game, events)
    if action == "change_rations":
        return rations_narrative(game, events)
    if action == "rest":
        return rest_narrative(game, events)
    if action == "scavenge":
        return scavenge_narrative(game, action_context, events)
    if action == "use_medicine":
        return medicine_narrative(game, action_context, events)
    if action == "buy":
        return buy_narrative(game, action_context)
    if action in ("talk", "browse"):
        return landmark_browse_narrative(game)
    if action == "leave_settlement":
        return leave_settlement_narrative(game)
    if action == "river_crossing":
        return river_crossing_narrative(game, action_context)
    if action == "walk":
        return stranded_walk_narrative(game, action_context)
    if action == "scavenge_fuel":
        return stranded_scavenge_narrative(game, action_context)
    if action == "attack_caravan":
        return stranded_caravan_narrative(game, action_context)
    if action == "stranded_wait":
        return stranded_intro_narrative(game)

    # fallback — also catches first stranded turn before any action
    if game.get("phase") == "stranded":
        return stranded_intro_narrative(game)
    return travel_narrative(game, events)
