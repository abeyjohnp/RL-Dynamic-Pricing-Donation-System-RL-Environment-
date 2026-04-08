from openenv.core.env_server import create_web_interface_app
from env import SupermarketEnv, PricingAction, RetailObservation

# 1. Boot up your game engine
store_env = SupermarketEnv()

# 2. Wrap it in the official OpenEnv web server
app = create_web_interface_app(store_env, PricingAction, RetailObservation)