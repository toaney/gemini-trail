import json
import uuid
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage

from api.schemas import NewGameRequest, ActionRequest, GameSessionResponse, SaveRequest, SavePoint, LoadRequest
from agent.state import GameData, PartyMember, Supplies

router = APIRouter()


def _initial_game_state(req: NewGameRequest) -> dict:
    names = req.party_names[:4]
    while len(names) < 4:
        names.append(f"Traveler {len(names) + 1}")

    party = [PartyMember(name=name).model_dump() for name in names]

    game = GameData(
        phase="setup",
        departure_month=req.departure_month,
        occupation=req.occupation,
        party=party,
    ).model_dump()

    return game


@router.post("/game/new", response_model=GameSessionResponse)
async def new_game(req: NewGameRequest, request: Request):
    thread_id = str(uuid.uuid4())
    graph = request.app.state.graph

    initial_game = _initial_game_state(req)

    config = {"configurable": {"thread_id": thread_id}}
    result = await graph.ainvoke(
        {
            "messages": [HumanMessage(content="view supplies")],
            "game": initial_game,
        },
        config=config,
    )

    game = result.get("game", {})
    return GameSessionResponse(
        thread_id=thread_id,
        player_name=req.party_names[0] if req.party_names else req.player_name,
        occupation=req.occupation,
        departure_month=req.departure_month,
        opening_narrative=game.get("_last_narrative", ""),
        opening_suggestions=game.get("suggestions", []),
        initial_game_state=_safe_game_state(game),
    )


@router.post("/game/stream")
async def stream_action(req: ActionRequest, request: Request):
    graph = request.app.state.graph
    config = {"configurable": {"thread_id": req.thread_id}}

    async def event_generator():
        try:
            result = await graph.ainvoke(
                {"messages": [HumanMessage(content=req.message)]},
                config=config,
            )
            game = result.get("game", {})
            if game:
                narrative_text = game.get("_last_narrative", "")
                if narrative_text:
                    yield f"data: {json.dumps({'type': 'narrative', 'text': narrative_text})}\n\n"

                safe_game = _safe_game_state(game)
                yield f"data: {json.dumps({'type': 'state_update', 'game': safe_game})}\n\n"

                suggestions = game.get("suggestions", [])
                if suggestions:
                    yield f"data: {json.dumps({'type': 'suggestions', 'actions': suggestions})}\n\n"

                if game.get("outcome"):
                    yield f"data: {json.dumps({'type': 'game_over', 'outcome': game['outcome'], 'reason': game.get('outcome_reason', '')})}\n\n"

            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/game/state/{thread_id}")
async def get_game_state(thread_id: str, request: Request):
    graph = request.app.state.graph
    config = {"configurable": {"thread_id": thread_id}}
    state = await graph.aget_state(config)
    if not state or not state.values:
        return {"error": "Game not found"}
    game = state.values.get("game", {})
    return {"game": _safe_game_state(game)}


@router.post("/game/save")
async def save_game(req: SaveRequest, request: Request):
    pool = request.app.state.pool
    async with pool.connection() as conn:
        await conn.execute(
            "INSERT INTO game_saves (name, thread_id, game_state) VALUES (%s, %s, %s)",
            (req.name, req.thread_id, json.dumps(req.game_state)),
        )
    return {"ok": True}


@router.get("/game/saves", response_model=list[SavePoint])
async def list_saves(request: Request):
    pool = request.app.state.pool
    async with pool.connection() as conn:
        rows = await conn.execute(
            "SELECT id, name, thread_id, game_state, created_at FROM game_saves ORDER BY created_at DESC LIMIT 50"
        )
        saves = []
        async for row in rows:
            gs = row[3] if isinstance(row[3], dict) else json.loads(row[3])
            saves.append(SavePoint(
                id=row[0],
                name=row[1],
                thread_id=row[2],
                day=gs.get("day", 0),
                distance=gs.get("distance_traveled", 0.0),
                phase=gs.get("phase", "unknown"),
                created_at=row[4].isoformat(),
            ))
    return saves


@router.post("/game/load")
async def load_save(req: LoadRequest, request: Request):
    pool = request.app.state.pool
    graph = request.app.state.graph

    async with pool.connection() as conn:
        rows = await conn.execute(
            "SELECT thread_id, game_state FROM game_saves WHERE id = %s", (req.save_id,)
        )
        row = await rows.fetchone()
        if not row:
            return {"error": "Save not found"}, 404

    _, game_state = row
    gs = game_state if isinstance(game_state, dict) else json.loads(game_state)

    new_thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": new_thread_id}}

    result = await graph.ainvoke(
        {"messages": [HumanMessage(content="view supplies")], "game": gs},
        config=config,
    )

    game = result.get("game", {})
    return {
        "thread_id": new_thread_id,
        "game_state": _safe_game_state(game),
        "narrative": game.get("_last_narrative", ""),
        "suggestions": game.get("suggestions", []),
    }


@router.delete("/game/save/{save_id}")
async def delete_save(save_id: int, request: Request):
    pool = request.app.state.pool
    async with pool.connection() as conn:
        await conn.execute("DELETE FROM game_saves WHERE id = %s", (save_id,))
    return {"ok": True}


@router.get("/health")
async def health():
    return {"status": "ok"}


def _safe_game_state(game: dict) -> dict:
    """Strip internal fields before sending to frontend."""
    safe = {k: v for k, v in game.items() if not k.startswith("_")}

    if "party" in safe:
        for member in safe["party"]:
            member.pop("health", None)

    return safe
