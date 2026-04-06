#this is the envt file
from pydantic import BaseModel
from typing import List, Literal
import random

#Observation space (AI sees this)
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

#Action space (Ai does this)
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
    
    def _generate_mock_inventory(self) -> List[PerishableItem]:
        """Generates the starting inventory for the Easy/Medium tasks."""
        items = []
        # Let's generate 10 items (a mix of Milk, Bananas, and Beef)
        for i in range(1, 11):
            if i <= 4:
                items.append(PerishableItem(item_id=i, name="Milk", days_to_expiration=14, base_price=4.0, status="on_shelf"))
            elif i <= 7:
                items.append(PerishableItem(item_id=i, name="Bananas", days_to_expiration=5, base_price=2.0, status="on_shelf"))
            else:
                items.append(PerishableItem(item_id=i, name="Ground Beef", days_to_expiration=3, base_price=8.0, status="on_shelf"))
        return items
    
    def reset(self) -> RetailObservation:
        """Starts a new simulation month."""
        self.current_day = 1
        self.total_revenue = 0.0
        self.landfill_waste_count = 0
        self.inventory = self._generate_mock_inventory()
        
        return RetailObservation(
            current_day=self.current_day,
            total_revenue=self.total_revenue,
            landfill_waste_count=self.landfill_waste_count,
            inventory=self.inventory
        )
    