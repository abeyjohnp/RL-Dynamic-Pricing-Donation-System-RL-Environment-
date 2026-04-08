import asyncio
import os
import json
from typing import List, Optional
from openai import OpenAI
from env import SupermarketEnv, PricingAction

API_KEY      = os.getenv("HF_TOKEN") or os.getenv("API_KEY")
API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME   = os.getenv("MODEL_NAME",   "Qwen/Qwen2.5-72B-Instruct")
BENCHMARK    = os.getenv("MY_ENV_V4_BENCHMARK", "supermarket-food-rescue")

# Run ALL three task levels so the validator sees 3 graded task executions
TASKS = ["easy", "medium", "hard"]

MAX_STEPS   = 30
TEMPERATURE = 0.7
MAX_TOKENS  = 150

SYSTEM_PROMPT = "You are a supermarket manager. Respond with a JSON action."

def log_start(task: str, env: str, model: str):
    print(f"[START] task={task} env={env} model={model}", flush=True)

def log_step(step: int, action: str, reward: float, done: bool, error: Optional[str]):
    print(f"[STEP] step={step} action={action} reward={reward:.2f} done={str(done).lower()} error={error or 'null'}", flush=True)

def log_end(success: bool, steps: int, score: float, rewards: List[float]):
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(f"[END] success={str(success).lower()} steps={steps} score={score:.3f} rewards={rewards_str}", flush=True)


async def run_task(client: OpenAI, task_name: str):
    """Run one full episode for a given task level."""
    env     = SupermarketEnv()
    rewards: List[float] = []
    step    = 0
    success = False
    final_score = 0.01

    log_start(task=task_name, env=BENCHMARK, model=MODEL_NAME)

    try:
        obs = env.reset(task=task_name)

        for step in range(1, MAX_STEPS + 1):
            # Build a minimal inventory summary for the prompt
            on_shelf = [i for i in obs.inventory if i.status == "on_shelf"]
            if not on_shelf:
                break

            item = on_shelf[0]  # Simple strategy: handle first item on shelf
            prompt = (
                f"Day {obs.current_day}. Item id={item.item_id} "
                f"expires_in={item.days_to_expiration}d price=${item.base_price}. "
                "Choose action_type: hold_price | set_discount | donate. "
                "Reply ONLY with JSON: {\"item_id\": <int>, \"action_type\": \"<str>\"}"
            )

            error = None
            try:
                completion = client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user",   "content": prompt},
                    ],
                    temperature=TEMPERATURE,
                    max_tokens=MAX_TOKENS,
                )
                ai_response = (completion.choices[0].message.content or "").strip()
                clean_json  = ai_response.replace("```json", "").replace("```", "").strip()
                action_dict = json.loads(clean_json)
                action      = PricingAction(**action_dict)
                obs, reward, done, _ = env.step(action)
            except Exception as e:
                reward      = 0.01
                done        = False
                error       = str(e)
                ai_response = "Error"

            rewards.append(reward)
            log_step(step, ai_response, reward, done, error)
            if done:
                break

        final_score = max(0.01, min(0.99, sum(rewards) / max(len(rewards), 1)))
        success     = obs.landfill_waste_count == 0

    finally:
        log_end(success=success, steps=step, score=final_score, rewards=rewards)


async def main():
    client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)
    # Run all 3 tasks sequentially so validator sees 3 [START]/[END] pairs
    for task_name in TASKS:
        await run_task(client, task_name)


if __name__ == "__main__":
    asyncio.run(main())