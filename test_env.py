from env import SupermarketEnv, PricingAction

print("--- Starting Supermarket Simulation ---")

# 1. Boot up the environment
store = SupermarketEnv()
observation = store.reset()

print(f"Day {observation.current_day} | Starting Revenue: ${observation.total_revenue}")
print(f"Items on shelf: {len(observation.inventory)}")
print("-" * 30)

# Let's look at the first item (Milk, item_id 1)
first_item = observation.inventory[0]
print(f"Targeting: {first_item.name} (Expires in {first_item.days_to_expiration} days)")

# 2. Fire an Action: Let's discount the milk
print("Action: Applying 50% Discount...")
action = PricingAction(item_id=first_item.item_id, action_type="set_discount")

# 3. Step the environment forward
new_obs, reward, done, error = store.step(action)

# 4. Check the results
print(f"Reward Received: {reward}")
print(f"New Total Revenue: ${new_obs.total_revenue}")
print(f"Item Status: {new_obs.inventory[0].status}")
print(f"Is simulation over? {done}")