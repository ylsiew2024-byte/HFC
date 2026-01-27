# UrbanPulse - Agentic Mobility Orchestrator

A multi-agent system for urban mobility management that demonstrates agentic AI improving urban liveability and environmental outcomes.

## What Does This Simulate?

UrbanPulse simulates a **smart city's public transit system** where AI agents autonomously manage buses, trains, and passenger flow across 5 districts. Each simulation step represents roughly **1 hour of city operation**.

### The Problem Being Solved

Cities face daily mobility challenges:
- **Rush hour chaos**: Morning (8am) and evening (6pm) peaks overwhelm transit
- **Limited resources**: Only so many buses and trains available
- **Competing districts**: All areas need help, but budgets are finite
- **Cascading effects**: Poor transit → more cars → traffic → worse air quality

### What Happens Each Step

When you click **Step** or **Run 10**, the simulation:

1. **Simulates demand waves** - Passenger demand rises/falls like real rush hours (peaks at 8am and 6pm in the 24-hour cycle)

2. **Agents observe conditions** - The MonitoringAgent checks each district's:
   - Bus/MRT load factors (are they overcrowded?)
   - Station crowding levels
   - Road traffic congestion
   - Air quality

3. **Agents propose interventions** - The PlannerAgent suggests actions:
   - `ADD_BUSES` - Deploy more buses to reduce overcrowding
   - `ADD_TRAINS` - Increase MRT frequency
   - `BUS_PRIORITY` - Give buses priority lanes (when roads too congested for more buses)
   - `CROWD_MGMT` - Activate crowd control at dangerously crowded stations
   - `NUDGE` - Send app notifications encouraging off-peak travel

4. **Policy validation** - The PolicyAgent enforces rules:
   - Can't add buses if roads are gridlocked (>80% traffic)
   - Maximum 10 buses or 3 trains per district per step
   - Crowd management only when crowding is critical (>90%)

5. **Budget allocation** - The CoordinatorAgent distributes limited resources:
   - Only 40 extra buses and 12 extra trains available city-wide per step
   - Districts sorted by **urgency score** (most critical get resources first)
   - This creates realistic trade-offs and prevents one district hogging everything

6. **Actions executed** - Approved interventions are applied:
   - Capacities increase
   - Load factors improve
   - Crowding reduces

7. **Environment responds** - The city reacts:
   - Better transit → fewer cars → less traffic → cleaner air
   - Nudges reduce demand temporarily
   - System stabilizes until next demand wave

### What Can It Achieve?

**Without intervention** (if agents did nothing):
- Load factors would exceed 100% during rush hours
- Station crowding would hit dangerous levels
- Traffic would gridlock
- Air quality would plummet

**With the multi-agent system**:
- Load factors stay manageable (~85% target)
- Crowding kept below critical thresholds
- Resources distributed fairly across districts
- Liveability and Environment scores improve over time

### Watching the Demo

- **Liveability Score** (0-100): Higher = less crowding, shorter waits, smoother transit
- **Environment Score** (0-100): Higher = less traffic, better air quality
- **Action Feed**: Shows real-time decisions being made
- **Chart**: Tracks how scores change as agents adapt to demand waves

Click **Run 10** repeatedly to watch the city go through multiple "hours" - you'll see scores fluctuate with rush hours but the agents continuously adapt to maintain liveable conditions.

## Features

- **Multi-Agent Architecture**: MonitoringAgent, CapacityPlannerAgent, PolicyAgent, CoordinatorAgent, ExecutionAgent
- **City-wide KPIs**: Liveability and Environment scores (0-100)
- **Budget Constraints**: Limited bus and MRT resources allocated by urgency
- **Policy Enforcement**: Safety constraints and rules validation
- **Real-time Dashboard**: Interactive frontend with charts and action feed

## Quick Start

### 1. Install Dependencies

```bash
cd urbanpulse
pip install -r requirements.txt
```

### 2. Start the Backend

```bash
uvicorn backend.main:app --reload
```

The API will be available at `http://127.0.0.1:8000`

### 3. Open the Frontend

Open `frontend/index.html` using VS Code Live Server (or any static file server).

- In VS Code: Right-click `index.html` → "Open with Live Server"
- The frontend will connect to the backend API

### 4. Use the Dashboard

- **Step**: Advance simulation by 1 time step
- **Run 10**: Advance simulation by 10 time steps
- **Reset**: Reset simulation to initial state

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/state` | GET | Get current city state |
| `/api/step` | POST | Advance one simulation step |
| `/api/run?n=N` | POST | Run N simulation steps |
| `/api/reset` | POST | Reset to initial state |

## Architecture

```
urbanpulse/
├── backend/
│   ├── main.py          # FastAPI application
│   ├── models.py        # Data models (CityState, DistrictState)
│   ├── env.py           # Environment dynamics
│   ├── kpi.py           # KPI calculations
│   ├── orchestrator.py  # Main orchestration logic
│   └── agents/
│       ├── monitoring.py   # Observes city state
│       ├── planner.py      # Proposes actions
│       ├── policy.py       # Validates constraints
│       ├── coordinator.py  # Allocates budgets
│       └── executor.py     # Applies actions
└── frontend/
    ├── index.html       # Dashboard UI
    ├── app.js           # API calls and DOM updates
    └── styles.css       # Styling
```

## Agent Pipeline (each step)

1. **Observe** - MonitoringAgent reads city state
2. **Propose** - CapacityPlannerAgent generates action proposals with urgency scores
3. **Sanitize** - PolicyAgent validates against constraints
4. **Allocate** - CoordinatorAgent distributes limited budgets by urgency
5. **Execute** - ExecutionAgent applies approved actions
6. **Update** - Environment advances simulation dynamics

## Key Metrics

- **Liveability Score**: Based on station crowding, transit load factors, road traffic
- **Environment Score**: Based on traffic (emissions proxy) and air quality
- **Urgency Score**: Prioritizes districts needing intervention

## Districts

The simulation includes 5 districts: Central, North, South, East, West - each with unique population, transit capacity, and baseline conditions.

## Why This is "Agentic AI"

This system demonstrates the 6 key properties of agentic AI:

| Property | How UrbanPulse Demonstrates It |
|----------|-------------------------------|
| **State over time** | City state persists across steps; history tracked for charts |
| **Goals** | Maximize liveability (reduce crowding/wait) + environment (reduce emissions) |
| **Autonomous actions** | Agents decide and act without human prompting each step |
| **Coordination** | Multiple agents propose → PolicyAgent validates → CoordinatorAgent allocates |
| **Feedback loop** | Actions change environment → KPIs update → future decisions adapt |
| **Constraints/Safety** | Budget limits, max change rates, policy rules enforced |

The key insight: this isn't just reactive rules. The **CoordinatorAgent** makes genuine trade-offs when resources are scarce, prioritizing by urgency scores. Districts that don't receive resources in one step may get higher priority in the next (starvation prevention).


#my push