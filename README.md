# Gemini Trail

A post-apocalyptic cross-country survival game. Drive from **Long Beach, CA to Washington, DC** — 3,245 miles through a broken America.

Powered by [Gemini 2.5 Flash](https://deepmind.google/technologies/gemini/) as the game master, with a [LangGraph](https://langchain-ai.github.io/langgraph/) state machine managing game logic and a [Next.js](https://nextjs.org/) frontend streaming the story in real time.

---

## Gameplay

- Choose an occupation: **Bunker CEO**, **Engineer**, or **Carpenter** — each with different starting resources and skills
- Name your party of 4
- Pick a departure month — it affects weather across the entire route
- Stock up at the Long Beach market before you leave
- Drive east through Las Vegas, Phoenix, Roswell, Fort Worth, Shreveport, the Mississippi Crossing, Tuscaloosa, Atlanta, and Charleston
- Manage fuel, food, water, medicine, ammo, trade goods, and your vehicle
- Scavenge between stops — easier east of the Mississippi
- Trade at settlements — but not every city has what you need
- Survive random events: disease, breakdowns, raider attacks, extreme weather
- Make it to Washington, DC

---

## Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 15, App Router, TypeScript, Tailwind CSS |
| Backend | FastAPI, Python 3.11 |
| AI / Game Master | Gemini 2.5 Flash via `langchain-google-genai` |
| Agent Framework | LangGraph with PostgreSQL checkpointer |
| Database | PostgreSQL 16 |
| Infrastructure | Docker Compose |

---

## Project Structure

```
gemini-trail/
├── frontend/               # Next.js app
│   ├── app/                # App Router pages and API proxy
│   ├── components/         # StatsPanel, NarrativePanel, ActionInput
│   └── lib/                # Types and useGameStream SSE hook
├── backend/
│   ├── config/
│   │   └── game_config.yaml   # All game weights, prices, probabilities
│   ├── engine/                # Pure Python game logic (no Gemini)
│   │   ├── travel.py
│   │   ├── events.py
│   │   ├── consumption.py
│   │   ├── scavenging.py
│   │   ├── store.py
│   │   └── conditions.py
│   ├── agent/                 # LangGraph graph + Gemini nodes
│   │   ├── graph.py
│   │   ├── nodes.py
│   │   ├── prompts.py
│   │   └── state.py
│   ├── api/                   # FastAPI routes
│   └── main.py
└── docker-compose.yml
```

---

## Local Setup

**Prerequisites:** Docker Desktop, a [Gemini API key](https://aistudio.google.com/app/apikey)

```bash
# 1. Clone the repo
git clone https://github.com/YOUR_USERNAME/gemini-trail.git
cd gemini-trail

# 2. Set up environment variables
cp .env.example .env
# Edit .env and fill in:
#   GEMINI_API_KEY=your-key-here
#   POSTGRES_PASSWORD=choose-a-password

# 3. Start everything
docker compose up --build
```

- Frontend: http://localhost:3000
- Backend: http://localhost:8000
- Both services hot-reload on file changes

---

## Architecture Notes

**Game logic is entirely on the backend.** The frontend receives only:
- Narrative text (streamed token by token)
- Current supply values and party health labels
- Suggested actions for the next turn

Probabilities, damage formulas, scavenge rates, and store prices live in `game_config.yaml` and are never sent to the client.

**Gemini is called twice per turn:**
1. To interpret the player's free-text action
2. To write the narrative and generate 3 suggestions

All math between those two calls is deterministic Python.

**Conversation state** is stored in PostgreSQL via the LangGraph checkpointer. Each game session is a `thread_id` — players can close the browser and resume.

---

## Environment Variables

| Variable | Description |
|---|---|
| `GEMINI_API_KEY` | Your Gemini API key — backend only, never exposed to the browser |
| `POSTGRES_PASSWORD` | PostgreSQL password |
| `DATABASE_URL` | Set automatically by Docker Compose |
| `BACKEND_URL` | Set automatically by Docker Compose (`http://backend:8000`) |
