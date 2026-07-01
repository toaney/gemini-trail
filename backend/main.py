import os
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from psycopg import AsyncConnection
from psycopg_pool import AsyncConnectionPool
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from agent.graph import build_graph
from api.routes import router

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    db_url = os.getenv("DATABASE_URL")

    # CREATE INDEX CONCURRENTLY cannot run inside a transaction block,
    # so run migrations with a direct autocommit connection before opening the pool.
    async with await AsyncConnection.connect(db_url, autocommit=True) as conn:
        await AsyncPostgresSaver(conn).setup()
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS game_saves (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                thread_id TEXT NOT NULL,
                game_state JSONB NOT NULL,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)

    pool = AsyncConnectionPool(conninfo=db_url, max_size=20, open=False)
    await pool.open()

    checkpointer = AsyncPostgresSaver(pool)
    app.state.graph = build_graph().compile(checkpointer=checkpointer)
    app.state.pool = pool

    yield

    await pool.close()


app = FastAPI(title="Gemini Trail", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")
