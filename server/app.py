import uvicorn
from openenv.core.env_server.http_server import create_app
from env import SupermarketEnv

# Create the FastAPI app instance
app = create_app(env_class=SupermarketEnv)

def main():
    """
    The entry point for the 'server' command defined in pyproject.toml.
    It starts the Uvicorn server to host your RL environment.
    """
    uvicorn.run("server.app:app", host="0.0.0.0", port=8000, reload=True)

if __name__ == "__main__":
    main()