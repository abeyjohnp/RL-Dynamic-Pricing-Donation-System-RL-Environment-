from pydantic import BaseModel
from typing import List, Literal, Any
import random

class PerishableItem(BaseModel):
    item_id: int
    name: str 
    days_to_expiration: int
    base_price: float
    status: Literal["on_shelf", "discounted", "donated", "sold", "landfill"]

class RetailObservation(BaseModel):
    current_day: int
    total_revenue: float
    landfill_waste_count: int
    inventory: List[PerishableItem]
    reward: float = 0.01  # Safe Micro-Reward
    done: bool = False   

class PricingAction(BaseModel):
    item_id: int
    action_type: Literal["hold_price", "set_discount", "donate"]

class SupermarketEnv:
    def __init__(self):
        self.max_days = 30
        self.current_day = 1
        self.total_revenue = 0.0
        self.landfill_waste_count = 0
        self.inventory: List[PerishableItem] = []
        self.current_task = "medium"

    def close(self): pass

    def _get_observation(self, reward: float = 0.01, done: bool = False) -> RetailObservation:
        return RetailObservation(
            current_day=self.current_day,
            total_revenue=self.total_revenue,
            landfill_waste_count=self.landfill_waste_count,
            inventory=self.inventory,
            reward=float(reward), 
            done=bool(done)      
        )

    def reset(self, task: Any = "medium", task_level: Any = None, **kwargs) -> RetailObservation:
        # Support both 'task' and 'task_level' keyword arguments
        resolved_task = str(task_level) if task_level is not None else str(task)
        self.current_task = resolved_task

        self.current_day = 1
        self.total_revenue = 0.0
        self.landfill_waste_count = 0

        # Differentiate difficulty by item count and expiry window
        if resolved_task == "easy":
            count = 5
            expiry_range = (5, 10)   # More time — easier to manage
        elif resolved_task == "hard":
            count = 20
            expiry_range = (1, 5)    # Very tight — items expire fast
        else:  # medium (default)
            count = 10
            expiry_range = (3, 10)

        self.inventory = [
            PerishableItem(
                item_id=i,
                name="Produce",
                days_to_expiration=random.randint(*expiry_range),
                base_price=5.0,
                status="on_shelf"
            ) for i in range(1, count + 1)
        ]
        return self._get_observation(reward=0.01)

    def step(self, action: PricingAction):
        # BASE MICRO-REWARD: Never 0.0
        reward = 0.01 
        done = False
        target_item = next((i for i in self.inventory if i.item_id == action.item_id), None)
        
        if target_item and target_item.status == "on_shelf":
            if action.action_type == "donate":
                target_item.status = "donated"
                reward = 0.02
            elif action.action_type == "set_discount":
                target_item.status = "sold"
                reward = 0.02
            elif action.action_type == "hold_price":
                target_item.status = "sold"
                reward = 0.03 # Max step reward. 30 * 0.03 = 0.90 (Safe!)

        # Age items
        for item in self.inventory:
            if item.status == "on_shelf":
                item.days_to_expiration -= 1
                if item.days_to_expiration <= 0:
                    item.status = "landfill"
                    self.landfill_waste_count += 1
                    # No negative rewards allowed, keep it positive
                    reward = 0.01 

        if self.current_day >= self.max_days or not any(i.status == "on_shelf" for i in self.inventory):
            done = True

        self.current_day += 1
        return self._get_observation(reward=reward, done=done), reward, done, None

    async def reset_async(self, **kwargs): return self.reset(**kwargs)
    async def step_async(self, action: PricingAction): return self.step(action)