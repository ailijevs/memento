"""FastAPI application entrypoint for the Memento service."""

from fastapi import FastAPI

app = FastAPI()


@app.get("/")
def hello() -> str:
    """Return a simple greeting to confirm the service is running."""
    return "Hello world, welcome to Memento"
