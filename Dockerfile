FROM python:3.10-slim

# Set the working directory
WORKDIR /app

# Copy everything into the container
COPY . .

# Install dependencies (including uv for the lockfile)
RUN pip install --no-cache-dir openenv-core pydantic fastapi uvicorn uv

# Generate/Sync the lockfile
RUN uv lock

# EXPOSE the port the validator looks for
EXPOSE 8000

# THE CRITICAL CHANGE: 
# We run your custom server file directly using uvicorn.
# This forces the /tasks and /metadata routes we wrote to go live.
CMD ["uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "8000"]