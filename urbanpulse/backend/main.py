"""
FastAPI backend for MetroMind / UrbanPulse.
"""
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from .orchestrator import make_city, Orchestrator

app = FastAPI(
    title="MetroMind API",
    description="Agentic AI for Smart Urban Transit Management",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
        "http://127.0.0.1:5501",
        "http://localhost:5501",
        "http://127.0.0.1:5502",
        "http://localhost:5502",
        "http://127.0.0.1:3000",
        "http://localhost:3000",
        "null",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

city = make_city()
orchestrator = Orchestrator()


@app.get("/api/state")
def get_state():
    """Get current city state without advancing time."""
    return orchestrator.get_state(city)


@app.post("/api/step")
def do_step():
    """Advance simulation by one step."""
    return orchestrator.step(city)


@app.post("/api/simulate")
def simulate(hour: int = Query(ge=0, le=23)):
    """Simulate to the given hour of day.
    If the city is already past that hour today, advance to that hour tomorrow.
    Runs multiple steps as needed to reach the target hour.
    """
    target_hour = hour
    current_hour = city.hour_of_day

    if target_hour == current_hour:
        return orchestrator.step(city)

    if target_hour > current_hour:
        steps_needed = target_hour - current_hour
    else:
        steps_needed = (24 - current_hour) + target_hour

    steps_needed = min(steps_needed, 24)

    result = None
    for _ in range(steps_needed):
        result = orchestrator.step(city)
    return result


@app.post("/api/run")
def run_steps(n: int = Query(default=10, ge=1, le=100)):
    """Run N simulation steps."""
    result = None
    for _ in range(n):
        result = orchestrator.step(city)
    return result


@app.post("/api/reset")
def reset_city():
    """Reset the city to initial state."""
    global city
    city = make_city()
    return orchestrator.get_state(city)


@app.get("/")
def root():
    return {
        "name": "MetroMind API",
        "version": "2.0.0",
        "endpoints": [
            "GET /api/state",
            "POST /api/step",
            "POST /api/simulate?hour=HH",
            "POST /api/run?n=N",
            "POST /api/reset",
        ],
    }
