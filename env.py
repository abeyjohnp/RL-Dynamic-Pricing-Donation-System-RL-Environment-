from pydantic import BaseModel
from typing import List, Literal
import random

# Observation space (AI sees this)
class PerishableItem(BaseModel):
    item_id : int
    name : str 
    days_to_expiration: int
    base_price: float
    status: Literal["on_shelf", "discounted", "donated", "sold", "landfill"]

class RetailObservation(BaseModel):
    current_day: int
    total_revenue: float
    landfill_waste_count: int
    inventory: List[PerishableItem]
    reward: float = 0.0  
    done: bool = False   

# Action space (AI does this)
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
    
    def _generate_mock_inventory(self, task: str) -> List[PerishableItem]:
        items = []
        if task == "easy":
            for i in range(1, 6):
                items.append(PerishableItem(item_id=i, name="Milk", days_to_expiration=14, base_price=4.0, status="on_shelf"))
        elif task == "medium":
            for i in range(1, 11):
                if i <= 5:
                    items.append(PerishableItem(item_id=i, name="Milk", days_to_expiration=10, base_price=4.0, status="on_shelf"))
                else:
                    items.append(PerishableItem(item_id=i, name="Bananas", days_to_expiration=5, base_price=2.0, status="on_shelf"))
        elif task == "hard":
            # HARD: More items, shorter expiration dates
            for i in range(1, 15):
                items.append(PerishableItem(item_id=i, name="Ground Beef", days_to_expiration=random.randint(2, 4), base_price=8.0, status="on_shelf"))
        return items
    
    def reset(self, task_level: str = "medium") -> RetailObservation:
        self.current_task = task_level
        self.current_day = 1
        self.total_revenue = 0.0
        self.landfill_waste_count = 0
        self.inventory = self._generate_mock_inventory(task_level)
        return self._get_observation(reward=0.0, done=False)
    
    def step(self, action: PricingAction):
        reward = 0.0
        done = False
        target_item = None
        for item in self.inventory:
            if item.item_id == action.item_id:
                target_item = item
                break
        
        if not target_item or target_item.status != "on_shelf":
            return self._get_observation(), -0.1, done, "Invalid item or already processed."
        
        # Action Logic
        if action.action_type == "donate":
            target_item.status = "donated"
            reward += 0.2  # Positive reinforcement for food rescue
        elif action.action_type == "set_discount":
            if random.random() > 0.10: 
                target_item.status = "sold"
                self.total_revenue += (target_item.base_price * 0.5)
                reward += 0.5
        elif action.action_type == "hold_price":
            if random.random() > 0.50: 
                target_item.status = "sold"
                self.total_revenue += target_item.base_price
                reward += 1.0
        
        # Aging and Expiration Logic
        if target_item.status in ["on_shelf", "discounted"]:
            if self.current_task == "hard" and self.current_day == 14:
                target_item.days_to_expiration -= 2
                self.current_day += 2
            else:
                target_item.days_to_expiration -= 1
                self.current_day += 1

            # Check for Landfill (Waste)
            if target_item.days_to_expiration <= 0:
                target_item.status = "landfill"
                self.landfill_waste_count += 1
                reward -= 2.0  # Significant penalty for waste!

        active_items = [item for item in self.inventory if item.status in ["on_shelf", "discounted"]]
        if not active_items:
            done = True

        obs = self._get_observation(reward=reward, done=done)
        return obs, reward, done, None

    def get_metadata(self):
        return {
            "name": "supermarket-food-rescue",
            "description": "AI-driven Dynamic Pricing and Donation Manager."
        }

    def get_schema(self):
        return {}

    def _get_observation(self, reward: float = 0.0, done: bool = False) -> RetailObservation:
        return RetailObservation(
            current_day=self.current_day,
            total_revenue=self.total_revenue,
            landfill_waste_count=self.landfill_waste_count,
            inventory=self.inventory,
            reward=reward, 
            done=done      
        )

    async def reset_async(self, task_level: str = "medium"):
        return self.reset(task_level=task_level)

    async def step_async(self, action: PricingAction):
        return self.step(action)

    def close(self):
        pass