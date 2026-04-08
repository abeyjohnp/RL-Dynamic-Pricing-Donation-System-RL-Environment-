---
title: Supermarket Food Rescue
emoji: 🍎
colorFrom: green
colorTo: blue
sdk: docker
app_port: 8000
---

# Supermarket Food Rescue 

**AI-driven Dynamic Pricing and Donation Manager**: An OpenEnv Reinforcement Learning environment where agents must balance supermarket profitability with food waste reduction.

## The Idea & Real-World Utility
Supermarkets throw away millions of tons of food every year because items pass their expiration dates. This environment challenges an AI agent to solve this problem by managing a perishable inventory. The agent must make daily pricing decisions for each item, deciding whether to keep the base price, apply a discount to encourage a quick sale, or proactively donate the food to a charity before it ends up in a landfill.

## Observation Space
At each step, the agent sees the current state of the store (`RetailObservation`):
- `current_day`: The current day of the simulation (1-30).
- `total_revenue`: The total money earned so far.
- `landfill_waste_count`: The number of items that spoiled and were thrown away.
- `inventory`: A list of `PerishableItem`s currently in the store, showing their `item_id`, `name`, `days_to_expiration`, `base_price`, and current `status` (`on_shelf`, `discounted`, `donated`, `sold`, `landfill`).

##  Action Space
The agent can take one of three actions (`PricingAction`) on a specific `item_id`:
1. **`hold_price`**: Keep the item at full price. (Higher reward if sold, but lower chance of selling before expiration).
2. **`set_discount`**: Apply a 50% discount. (Lower reward when sold, but higher probability of a quick sale).
3. **`donate`**: Donate the item immediately to a food bank. (Small positive reward, guarantees zero waste).

##  Tasks & Graders
The environment implements 3 tasks of progressive difficulty:
1. **`easy`**: Low volume, long expiration dates. The agent just needs to make sure items are sold or donated without much pressure.
2. **`medium`**: Standard operations. A mix of items with different shelf lives (e.g., Milk vs. Bananas). The agent must prioritize which items to discount or donate.
3. **`hard`**: High volume, short expirations, and unexpected "holiday closures" that accelerate aging. The agent must aggressively manage discounts and donations to avoid massive landfill penalties.

##  Reward Function Design
The reward function is dense and provides partial feedback to guide the agent:
- **+1.0**: Item sold at full price (`hold_price`).
- **+0.5**: Item sold at a discount (`set_discount`).
- **+0.2**: Item rescued via donation (`donate`). Provides a safety net against waste!
- **-0.1**: Invalid action (e.g., trying to act on an already sold item).
- **-2.0**: Massive penalty if an item expires and goes to the `landfill`!

##  How to Run
You can connect to this environment using the standard OpenEnv client:
```python
from openenv.client import RemoteEnvironment
import asyncio

async def main():
    env = RemoteEnvironment("http://127.0.0.1:8000")
    obs = await env.reset()
    print(obs)

if __name__ == "__main__":
    asyncio.run(main())
```
