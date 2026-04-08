import uvicorn
import os
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from env import SupermarketEnv, PricingAction, RetailObservation

# Build a plain FastAPI app — no create_app() wrapper.
# This means WE control every route, so the validator always sees OUR /tasks.
app = FastAPI(title="Supermarket Food Rescue", version="0.3.0")

# ── Singleton environment ────────────────────────────────────────────────────
_env = SupermarketEnv()

TASKS = [
    {"name": "easy",   "description": "Low volume — 5 items, agent must minimise waste", "grader": {"type": "reward", "goal": 0.5}},
    {"name": "medium", "description": "Standard operations — 10 items",                  "grader": {"type": "reward", "goal": 0.7}},
    {"name": "hard",   "description": "Holiday rush — 20 items, tight expiry windows",   "grader": {"type": "reward", "goal": 0.9}},
]

METADATA = {
    "name": "supermarket-food-rescue",
    "version": "0.3.0",
    "description": "AI-driven Dynamic Pricing and Donation Manager for reducing food waste.",
    "tasks": TASKS,
}

# ── Discovery routes (what the validator reads) ──────────────────────────────
@app.get("/tasks")
async def get_tasks():
    return JSONResponse(content=TASKS)

@app.get("/metadata")
async def get_metadata():
    return JSONResponse(content=METADATA)

# Mirror routes under /v1 just in case the validator probes those
@app.get("/v1/tasks")
async def get_tasks_v1():
    return JSONResponse(content=TASKS)

@app.get("/v1/metadata")
async def get_metadata_v1():
    return JSONResponse(content=METADATA)

# ── Environment interaction routes ────────────────────────────────────────────
@app.post("/reset")
async def reset(task: str = "medium"):
    obs = _env.reset(task=task)
    return obs

@app.post("/step")
async def step(action: PricingAction):
    result, reward, done, _ = _env.step(action)
    return {"observation": result, "reward": reward, "done": done}

@app.get("/health")
async def health():
    return {"status": "ok"}

# ── Entry point ───────────────────────────────────────────────────────────────
def main():
    bind_ip   = os.environ.get("SERVER_HOST", "0.0.0.0")
    bind_port = int(os.environ.get("SERVER_PORT", "8000"))
    uvicorn.run(app, host=bind_ip, port=bind_port)

if __name__ == "__main__":
    main()