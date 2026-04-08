import asyncio
import os
import textwrap
from typing import List, Optional
from openai import OpenAI

# Import YOUR environment
from env import SupermarketEnv, PricingAction

API_KEY = os.getenv("HF_TOKEN") or os.getenv("API_KEY")
API_BASE_URL = os.getenv("API_BASE_URL") or "https://router.huggingface.co/v1"
MODEL_NAME = os.getenv("MODEL_NAME") or "Qwen/Qwen2.5-72B-Instruct"
TASK_NAME = os.getenv("MY_ENV_V4_TASK", "medium") # Defaulting to your medium task
BENCHMARK = os.getenv("MY_ENV_V4_BENCHMARK", "supermarket-food-rescue")

# A simulated month is 30 days
MAX_STEPS = 30
TEMPERATURE = 0.7
MAX_TOKENS = 150

# The instructions for the AI
SYSTEM_PROMPT = textwrap.dedent(
    """
    You are the Dynamic Pricing & Donation Manager for a supermarket.
    Every step, you will see a list of perishable inventory and how many days until they expire.
    Your goal is to maximize revenue while minimizing food waste (items hitting 0 days).
    You can respond with exactly one JSON action.
    Example: {"item_id": 1, "action_type": "set_discount"}
    Valid actions: "hold_price", "set_discount", "donate".
    """
).strip()

def log_start(task: str, env: str, model: str) -> None:
    print(f"[START] task={task} env={env} model={model}", flush=True)

def log_step(step: int, action: str, reward: float, done: bool, error: Optional[str]) -> None:
    error_val = error if error else "null"
    done_val = str(done).lower()
    print(f"[STEP] step={step} action={action} reward={reward:.2f} done={done_val} error={error_val}", flush=True)

def log_end(success: bool, steps: int, score: float, rewards: List[float]) -> None:
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(f"[END] success={str(success).lower()} steps={steps} score={score:.3f} rewards={rewards_str}", flush=True)

async def main() -> None:
    # Initialize the OpenAI client (connecting to HF router)
    client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)
    
    # Boot up YOUR environment directly for testing
    env = SupermarketEnv()
    
    history: List[str] = []
    rewards: List[float] = []
    
    log_start(task=TASK_NAME, env=BENCHMARK, model=MODEL_NAME)
    
    try:
        # 1. Reset the environment
        obs = env.reset(task_level=TASK_NAME)
        
        for step in range(1, MAX_STEPS + 1):
            # 2. Build the prompt for the AI based on what's on the shelves
            inventory_status = "\n".join([f"ID: {i.item_id} | {i.name} | Expires in: {i.days_to_expiration} days | Status: {i.status}" for i in obs.inventory if i.status in ["on_shelf", "discounted"]])
            
            user_prompt = f"Day: {obs.current_day}\nRevenue: ${obs.total_revenue}\nInventory:\n{inventory_status}\nWhat is your next action?"
            
            # 3. Ask the LLM
            completion = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=TEMPERATURE,
                max_tokens=MAX_TOKENS,
            )
            ai_response = (completion.choices[0].message.content or "").strip()
            
            # 4. Parse AI response and step the environment
            try:
                # Basic parsing assuming the AI returns a valid JSON string 
                # (In production, you'd use strict JSON parsing here)
                import json
                action_dict = json.loads(ai_response)
                action = PricingAction(**action_dict)
                obs, reward, done, error = env.step(action)
            except Exception as e:
                reward = -0.5
                done = False
                error = f"Invalid action format: {str(e)}"
                ai_response = "Format Error"

            rewards.append(reward)
            log_step(step=step, action=ai_response, reward=reward, done=done, error=error)
            
            if done:
                break
                
        # Calculate final score (Revenue minus massive penalties)
        final_score = max(0.0, min(1.0, obs.total_revenue / 100.0)) 
        success = obs.landfill_waste_count == 0 # True success means zero waste!
        
    finally:
        log_end(success=success, steps=step, score=final_score, rewards=rewards)

if __name__ == "__main__":
    asyncio.run(main())