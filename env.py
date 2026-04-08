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
        """Generates inventory based on the selected difficulty."""
        items = []
        if task == "easy":
            # EASY: Only 5 Milks. Highly predictable.
            for i in range(1, 6):
                items.append(PerishableItem(item_id=i, name="Milk", days_to_expiration=14, base_price=4.0, status="on_shelf"))
                
        elif task in ["medium", "hard"]:
            # MEDIUM/HARD: 10 Mixed items with different expiration dates.
            for i in range(1, 11):
                if i <= 4:
                    items.append(PerishableItem(item_id=i, name="Milk", days_to_expiration=14, base_price=4.0, status="on_shelf"))
                elif i <= 7:
                    items.append(PerishableItem(item_id=i, name="Bananas", days_to_expiration=5, base_price=2.0, status="on_shelf"))
                else:
                    items.append(PerishableItem(item_id=i, name="Ground Beef", days_to_expiration=3, base_price=8.0, status="on_shelf"))
        return items
    
    def reset(self, task: str = "medium") -> RetailObservation:
        self.current_task = task
        self.current_day = 1
        self.total_revenue = 0.0
        self.landfill_waste_count = 0
        self.inventory = self._generate_mock_inventory(task)
        
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
            # Invalid action (item doesn't exist or is already gone)
            return self._get_observation(), -0.1, done, "Invalid item or already processed."
        
        if action.action_type == "donate":
            target_item.status = "donated"
            reward += 0.1  # Small reward for saving the food from the landfill
        elif action.action_type == "set_discount":
            target_item.status = "discounted"
            # Simulate a high chance of selling because it's cheap
            if random.random() > 0.10:  # 90% chance to sell
                target_item.status = "sold"
                self.total_revenue += (target_item.base_price * 0.5)
                reward += 0.5
        elif action.action_type == "hold_price":
            # Simulate a lower chance of selling at full price
            if random.random() > 0.50:  # 50% chance to sell
                target_item.status = "sold"
                self.total_revenue += target_item.base_price
                reward += 1.0
        
        # If it didn't sell and wasn't donated, it gets one day older
        if target_item.status in ["on_shelf", "discounted"]:
            # --- HOLIDAY FOR THE HARD TASK ---
            if self.current_task == "hard" and self.current_day == 14:
                # Store is closed for a 2-day holiday! Food ages, but no one buys it.
                target_item.days_to_expiration -= 2
                self.current_day += 2
            else:
                target_item.days_to_expiration -= 1
                self.current_day += 1

        active_items = [item for item in self.inventory if item.status in ["on_shelf", "discounted"]]
        if not active_items:
            done = True
        obs = self._get_observation(reward=reward, done=done)
        return obs, reward, done, None
    def get_metadata(self):
        """
        Provides the required name and description for the /metadata endpoint.
        """
        return {
            "name": "supermarket-food-rescue",
            "description": "AI-driven Dynamic Pricing and Donation Manager for reducing food waste."
        }

    def get_schema(self):
        """
        Provides the action/observation schema to the /schema endpoint.
        """
        return {}
    def _get_observation(self, reward: float = 0.0, done: bool = False) -> RetailObservation:
        """Helper to return the current state as a Pydantic model."""
        return RetailObservation(
            current_day=self.current_day,
            total_revenue=self.total_revenue,
            landfill_waste_count=self.landfill_waste_count,
            inventory=self.inventory,
            reward=reward, 
            done=done      
        )
    async def reset_async(self, task: str = "medium"):
        return self.reset(task=task)

    async def step_async(self, action: PricingAction):
        return self.step(action)

    def close(self):
        pass
    
    