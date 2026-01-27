"""
FastAPI backend for UrbanPulse.
"""
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from .orchestrator import make_city, Orchestrator

app = FastAPI(
    title="MetroMind API",
    description="Agentic AI for Smart Urban Transit Management",
    version="1.0.0",
)

# Enable CORS for Live Server (common ports: 5500, 5501, 5502, 3000)
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
        "null",  # For file:// protocol
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state
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


@app.post("/api/jump")
def jump_to_time(hour: int = Query(default=0, ge=0, le=23)):
    """Jump to a specific hour of the day."""
    global city
    current_hour = city.t % 24
    current_day = city.t // 24

    # Calculate target time
    target_time = current_day * 24 + hour

    # If target hour is in the past for current day, go to next day
    if hour < current_hour:
        target_time += 24

    # Run steps to reach target time
    steps_needed = target_time - city.t
    result = None
    for _ in range(steps_needed):
        result = orchestrator.step(city)

    return result if result else orchestrator.get_state(city)


@app.get("/")
def root():
    """API root endpoint."""
    return {
        "name": "MetroMind API",
        "version": "1.0.0",
        "endpoints": [
            "GET /api/state - Get current state",
            "POST /api/step - Advance one step",
            "POST /api/run?n=N - Run N steps",
            "POST /api/jump?hour=H - Jump to specific hour",
            "POST /api/reset - Reset simulation",
        ],
    }
