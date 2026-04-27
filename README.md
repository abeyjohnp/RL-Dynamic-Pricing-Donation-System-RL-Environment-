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

### Prerequisites

Install the required dependencies using `pip`:
```bash
pip install pydantic openenv-core fastapi uvicorn openai requests
```

Or use `uv` (recommended — uses the lockfile for reproducible installs):
```bash
pip install uv
uv sync
```

---

### How to run the whole project manually
To run the full suite of tools in this project, follow these steps in separate terminal windows:

#### 1. Start the Environment API (Backend)
This starts the "official" OpenEnv API server which would be used for formal evaluation.
```powershell
uvicorn server.app:app --host 127.0.0.1 --port 8000
```

#### 2. Start the Interactive Dashboard (Frontend)
This provides the visual UI for the project.
```powershell
python app.py
```
Open [http://127.0.0.1:5000](http://127.0.0.1:5000) in your browser.

#### 3. Run the LLM Inference Agent (The "AI")
If you want to see the AI (LLM) actually making decisions for the supermarket:
```powershell
# Note: Requires an HF_TOKEN set in your environment variables
python inference.py
```

#### 4. Run a Quick Smoke Test
To verify the core environment logic is working correctly without any servers:
```powershell
python test_env.py
```

**Summary of Ports:**
*   **Port 5000:** The Dashboard (User Interface).
*   **Port 8000:** The Environment API (The "Brain" for EVAL).

---

### How to run using Docker

Running with Docker ensures a consistent environment and is how the project is validated for the Google Solution Challenge.

#### 1. Build the Docker Image
Navigate to the root directory and run:
```bash
docker build -t supermarket-food-rescue .
```

#### 2. Run the Container
Start the container and map the internal port 8000 to your local machine:
```bash
docker run -p 8000:8000 supermarket-food-rescue
```

#### 3. What happens in Docker?
The Docker container is specifically configured to run the **Environment API** (`server/app.py`). 
*   It exposes **Port 8000**.
*   It serves the `/tasks` and `/metadata` endpoints required by the OpenEnv validator.
*   The interactive dashboard is typically run locally (outside Docker) during development, but the backend API is what counts for the submission.

---

### Full Submission Validation (Docker required)

Run the complete end-to-end submission validator:
```bash
# Make executable (first time only)
chmod +x validate-submission.sh

# Run against your HF Space URL
./validate-submission.sh https://your-space.hf.space
```

This performs 3 steps:
1. Pings your HF Space `/reset` endpoint (must return HTTP 200)
2. Runs `docker build` locally (with 600s timeout)
3. Runs `python -m openenv.cli validate` in the repo directory
