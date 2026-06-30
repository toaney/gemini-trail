import json
import uuid
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage

from api.schemas import NewGameRequest, ActionRequest, GameSessionResponse
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
    await graph.ainvoke(
        {
            "messages": [HumanMessage(content="start new game")],
            "game": initial_game,
        },
        config=config,
    )

    return GameSessionResponse(
        thread_id=thread_id,
        player_name=req.player_names[0] if req.party_names else req.player_name,
        occupation=req.occupation,
        departure_month=req.departure_month,
    )


@router.post("/game/stream")
async def stream_action(req: ActionRequest, request: Request):
    graph = request.app.state.graph
    config = {"configurable": {"thread_id": req.thread_id}}

    async def event_generator():
        try:
            async for event in graph.astream_events(
                {"messages": [HumanMessage(content=req.message)]},
                config=config,
                version="v2",
            ):
                kind = event.get("event")

                if kind == "on_chat_model_stream":
                    chunk = event["data"].get("chunk")
                    if chunk and hasattr(chunk, "content") and chunk.content:
                        yield f"data: {json.dumps({'type': 'token', 'content': chunk.content})}\n\n"

                elif kind == "on_chain_end" and event.get("name") == "narrate":
                    output = event.get("data", {}).get("output", {})
                    game = output.get("game", {})
                    if game:
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
