from langgraph.graph import StateGraph, END
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from agent.state import GameState
from agent.nodes import setup_node, engine_node, narrate_node


def _route_after_engine(state: GameState) -> str:
    game = state.get("game", {})
    if game.get("phase") == "game_over":
        return "narrate"
    return "narrate"


def build_graph() -> StateGraph:
    workflow = StateGraph(GameState)

    workflow.add_node("setup", setup_node)
    workflow.add_node("engine", engine_node)
    workflow.add_node("narrate", narrate_node)

    workflow.set_entry_point("setup")
    workflow.add_edge("setup", "engine")
    workflow.add_edge("engine", "narrate")
    workflow.add_edge("narrate", END)

    return workflow


async def create_compiled_graph(conn_string: str):
    async with AsyncPostgresSaver.from_conn_string(conn_string) as checkpointer:
        await checkpointer.setup()
        graph = build_graph().compile(checkpointer=checkpointer)
        return graph, checkpointer
