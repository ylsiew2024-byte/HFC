# Contributors (not in any order)
Koh Qing Jia,  Wong Xuan Yu , Gwee Wei Lin , Anumitaa Murali , Etienne Wong , Siew Yuanlong
# MetroMind - Agentic Mobility Orchestrator

A multi-agent AI system for autonomous urban transit management in Singapore. MetroMind demonstrates how coordinated AI agents can improve urban liveability and environmental outcomes by dynamically managing buses, trains, and passenger flow across multiple districts in real time.

---

## Table of Contents

1. [Overview](#overview)
2. [The Problem Being Solved](#the-problem-being-solved)
3. [Multi-Agent Architecture](#multi-agent-architecture)
4. [Agent Pipeline (Per Simulation Step)](#agent-pipeline-per-simulation-step)
5. [Detailed Agent Functions](#detailed-agent-functions)
6. [Dynamic Service Unit System](#dynamic-service-unit-system)
7. [Active Events System](#active-events-system)
8. [Weather System](#weather-system)
9. [Out-of-Service Hours](#out-of-service-hours)
10. [Key Metrics and Scoring](#key-metrics-and-scoring)
11. [Districts](#districts)
12. [Train Lines](#train-lines)
13. [Why This is Agentic AI](#why-this-is-agentic-ai)
14. [Quick Start](#quick-start)
15. [API Endpoints](#api-endpoints)
16. [Project Structure](#project-structure)

---

## Overview

MetroMind simulates a **smart city's public transit system** where five specialised AI agents autonomously manage bus and train services across four districts (Central, North, East, West) and four MRT lines (NSL, EWL, NEL, CCL). Each simulation step represents **1 hour of city operation**, running a full 24-hour cycle with realistic demand patterns, weather effects, random city events, and resource constraints.

The system uses a **service unit abstraction** where operational capacity is measured in service units (representing route bundles, crew shifts, and fleet segments) rather than individual vehicles, providing a realistic model of how transit authorities manage capacity at scale.

---

## The Problem Being Solved

Cities face complex, interconnected mobility challenges that cannot be solved by simple rules:

- **Rush hour overload**: Morning (8am) and evening (6pm) peaks overwhelm transit capacity, with demand reaching 80% of maximum.
- **Limited resources**: Only 50 bus service units and 20 train service units are available system-wide — not every district can be served at full capacity simultaneously.
- **Competing priorities**: All districts need resources, but the system must make trade-offs. A surge in Central means fewer resources for East.
- **Cascading effects**: Poor transit service leads to more private car usage, which increases road traffic, which degrades air quality, which lowers the overall liveability score.
- **Dynamic conditions**: Weather events, concerts, airport rushes, and MRT maintenance create unpredictable demand spikes that agents must respond to in real time.

---

## Multi-Agent Architecture

MetroMind employs a **sequential pipeline** of five specialised agents, each with a distinct responsibility. This separation of concerns ensures that no single agent has unchecked power — proposals must pass through validation, budget allocation, and execution before taking effect.

```
MonitoringAgent -> CapacityPlannerAgent -> PolicyAgent -> CoordinatorAgent -> ExecutionAgent
     |                    |                   |                |                 |
  Observes           Proposes            Validates         Allocates          Applies
  city state         actions             constraints       resources          changes
```

After all agents have acted, the **MobilityEnvironment** advances the simulation: updating demand waves, processing weather changes, triggering random events, computing emissions, and advancing the clock.

---

## Agent Pipeline (Per Simulation Step)

Each simulation step executes the following sequence:

1. **Reset** — Per-hour train line action logs are cleared.
2. **Scale** — Service units are dynamically scaled to match the current hour's demand profile (e.g., 85% deployment at 8am peak, 15% at midnight).
3. **Observe** — MonitoringAgent reads all city metrics and generates alerts.
4. **Propose** — CapacityPlannerAgent generates per-district bus proposals and per-line train proposals, each with an urgency score and human-readable reasoning.
5. **Validate** — PolicyAgent enforces safety constraints, blocking or adjusting proposals that violate rules.
6. **Allocate** — CoordinatorAgent distributes limited resources across districts and train lines by urgency, maintaining a ~20% reserve buffer.
7. **Execute** — ExecutionAgent applies approved actions to the city state and logs all interventions.
8. **Environment Step** — Demand waves update, weather evolves, events trigger/expire, emissions are computed, and the clock advances by 1 hour.
9. **Score** — Liveability and Environment KPIs are recalculated based on the new state.

---

## Detailed Agent Functions

### 1. MonitoringAgent (`agents/monitoring.py`)

**Role**: The system's eyes and ears. Observes the entire city state and produces a structured observation report consumed by all downstream agents.

**What it observes per district**:
- `bus_load_factor` — fraction of bus capacity in use (0.0-1.0)
- `mrt_load_factor` — fraction of MRT capacity in use (0.0-1.0)
- `station_crowding` — how crowded stations are (0.0-1.0, critical above 0.9)
- `road_traffic` — road congestion level (0.0-1.0)
- `air_quality` — air quality index (0-100, lower is worse)
- `nudges_active` — whether demand-reduction nudges are currently active

**What it observes per train line**:
- `line_load` — current load on the line (0.0-1.0)
- `frequency` — trains per hour
- `disruption_level` — level of service disruption (0.0-1.0)

**Alert generation**: The MonitoringAgent also generates human-readable alerts:
- `CRITICAL` alert when station crowding exceeds 90%
- `WARNING` alert when station crowding exceeds 70%
- Bus overload alerts when load factor exceeds 85% target
- High traffic alerts when road traffic exceeds 75%
- Poor air quality alerts when AQI drops below 60
- Train line overload alerts when line load exceeds 80% target
- Severe weather alerts for heavy rain, thunderstorms, and haze

---

### 2. CapacityPlannerAgent (`agents/planner.py`)

**Role**: The strategic thinker. Analyses observations and generates concrete action proposals for each district and train line, along with urgency scores and reasoning.

**District proposals** — for each of the 4 districts, the planner decides:

| Action | Condition | Effect |
|--------|-----------|--------|
| `ADD_BUSES` | Bus load > 85% AND road traffic <= 80% | Requests additional bus service units (1-10 based on overload severity) |
| `USE_BUS_PRIORITY` | Bus load > 85% AND road traffic > 80% | Recommends dedicated bus lanes instead of adding vehicles to congested roads |
| `CROWD_MGMT` | Station crowding > 90% (critical) | Activates crowd management protocols at stations |
| `NUDGE` | Crowding > 70% OR traffic > 75% (and nudges not already active) | Sends app notifications to passengers encouraging off-peak travel |
| `NO_CHANGE` | All metrics within targets | No intervention needed |

**Train line proposals** — for each of the 4 MRT lines:

| Action | Condition | Effect |
|--------|-----------|--------|
| `ADD_TRAINS` | Line load > 80% | Requests additional train service units (1-3 based on overload severity) |
| `NO_CHANGE` | Load within target | No change to frequency |

**Urgency scoring** — each proposal carries an urgency score that determines resource allocation priority:
- +2.0 if station crowding > 90% (critical)
- +1.0 if bus load > 85% target
- +1.0 if MRT load > 80% target
- +0.5 if road traffic > 75%
- +0.5 if air quality < 60

**Reasoning output** — the planner generates human-readable reasoning strings explaining each decision, e.g.:
- *"Central: Bus load 92% exceeds target — requesting +3 service units"*
- *"North: Low bus demand (14%) — scale-down appropriate"*
- *"CCL: Load 85% exceeds threshold — requesting +2 train service units"*

---

### 3. PolicyAgent (`agents/policy.py`)

**Role**: The safety regulator. Validates all proposals against hard constraints and safety rules before they reach the coordinator. This prevents dangerous or wasteful actions.

**Policy rules enforced**:

| Rule | Constraint | Action Taken |
|------|-----------|--------------|
| Traffic limit | If road traffic > 80%, block `ADD_BUSES` | Converts to `USE_BUS_PRIORITY` (adding buses to gridlocked roads worsens congestion) |
| Bus cap | `bus_extra` must be in [0, 10] | Clamps to maximum 10 additional bus units per district per step |
| Train cap | `mrt_extra` must be in [0, 3] | Clamps to maximum 3 additional train units per line per step |
| Crowding gate | `CROWD_MGMT` only when crowding > 90% | Removes crowd management if crowding is below critical threshold |
| Nudge gate | `NUDGE` only when crowding > 70% OR traffic > 75% | Removes nudges if conditions don't warrant demand reduction |

**Trace output**: The PolicyAgent returns a detailed trace of all adjustments and blocked actions, e.g.:
- *"Blocked ADD_BUSES for Central: road traffic 84% > 80% limit"*
- *"Clamped East bus_extra from 12 to 10"*

---

### 4. CoordinatorAgent (`agents/coordinator.py`)

**Role**: The resource allocator. This is the core coordination mechanism that makes MetroMind a true multi-agent system. It takes validated proposals from all districts and train lines, then distributes limited global resources fairly based on urgency.

**Allocation algorithm**:
1. Compute available capacity = active service units minus ~20% reserve buffer (reserves ensure the system can respond to sudden demand spikes)
2. Sort all district bus proposals by urgency score (descending — most critical first)
3. Allocate bus service units from the available pool:
   - Each district gets `min(requested, remaining)` units
   - Remaining capacity decreases with each allocation
   - If capacity is exhausted, lower-urgency districts are denied
4. Repeat for train line proposals using the train service unit pool

**What makes this meaningful**: When resources are scarce (e.g., 8am rush hour with 42 bus units active but only ~32 available after reserve), the coordinator must make genuine trade-offs. A high-urgency district with critical crowding will receive resources before a moderate-urgency district. This creates realistic resource competition and prioritisation.

**Trace output**: The coordinator logs every allocation decision:
- *"Central: allocated +5 bus service units"*
- *"North: requested +3 units, allocated +2 (partial)"*
- *"West: requested +4 units, denied (reserve limit)"*
- *"Available: 12 bus units, 3 train units (after reserve)"*

---

### 5. ExecutionAgent (`agents/executor.py`)

**Role**: The implementer. Takes approved, allocated proposals and applies them to the city state in a specific order to maximise safety and effectiveness.

**Execution order** (per district):
1. **Crowd management first** (safety priority) — reduces station crowding by 15% (x0.85)
2. **Bus actions**:
   - `ADD_BUSES`: increases district bus capacity and reduces load factor by 5% (x0.95)
   - `USE_BUS_PRIORITY`: reduces bus load by 3% and road traffic by 2%
3. **Nudge activation**: sets `nudges_active = True` with a 3-hour timer, which reduces future demand

**Train line execution**:
- `ADD_TRAINS`: increases line frequency and reduces line load by 5% (x0.95)

**Action logging**: Every action is recorded as a structured event:
```json
{
  "t": 8,
  "hour": 8,
  "type": "district",
  "district": "Central",
  "actions": ["CROWD_MGMT", "ADD_BUSES +5", "NUDGE_ACTIVATED"],
  "urgency": 3.5
}
```

---

## Dynamic Service Unit System

MetroMind uses a **service unit abstraction** rather than literal vehicle counts. Service units represent operational capacity blocks — a combination of route bundles, crew shifts, and fleet segments that a transit authority deploys.

**Maximum capacity**: 50 bus service units, 20 train service units system-wide.

**Hourly scaling profile** — service units are dynamically deployed based on time of day:

| Time of Day | Bus Units Active | Train Units Active | Rationale |
|-------------|-----------------|-------------------|-----------|
| 00:00 | 8 (15%) | 3 (15%) | Late night minimal service |
| 01:00-05:00 | 0 (0%) | 0 (0%) | **Out of service** — no public transit |
| 06:00 | 20 (40%) | 8 (40%) | Early morning ramp-up |
| 07:00 | 32 (65%) | 13 (65%) | Pre-peak buildup |
| **08:00** | **42 (85%)** | **17 (85%)** | **Morning peak** |
| 09:00 | 40 (80%) | 16 (80%) | Post-peak sustained |
| 10:00-11:00 | 28 (55%) | 10 (50%) | Midday reduction |
| 12:00 | 28 (55%) | 11 (55%) | Lunch period |
| 13:00-15:00 | 25 (50%) | 10 (50%) | Afternoon low |
| 16:00 | 30 (60%) | 12 (60%) | Pre-evening buildup |
| 17:00 | 40 (80%) | 16 (80%) | Evening peak begins |
| **18:00** | **42 (85%)** | **17 (85%)** | **Evening peak** |
| 19:00 | 35 (70%) | 14 (70%) | Post-peak decline |
| 20:00-21:00 | 22 (45%) | 7 (35%) | Evening wind-down |
| 22:00-23:00 | 12 (25%) | 4 (18%) | Late night minimal |

The coordinator maintains a ~20% reserve buffer from active units, ensuring capacity for sudden demand spikes from events or weather.

**Capacity bar colour coding** in the UI:
- **Green**: < 70% of max deployed
- **Yellow**: 70-90% of max deployed
- **Red**: > 90% of max deployed

---

## Active Events System

MetroMind simulates random city events that create demand surges in specific districts. Events are triggered probabilistically based on the time of day and add complexity that the agents must adapt to.

### Event Trigger Probability

| Time Period | Base Chance | Rationale |
|-------------|-------------|-----------|
| Off-peak (night) | 5% per hour | Rare events at night |
| Peak hours (7-9am, 5-7pm) | 15% per hour | High activity periods have more events |
| Midday (10am-4pm) | 8% per hour | Moderate daytime activity |

If 2 or more events are already active, the trigger chance is reduced to 30% of base (to prevent event overload).

### Implemented Events

| Event | Affected Districts | Demand Multiplier | Duration | Special Effects |
|-------|-------------------|-------------------|----------|----------------|
| **Rush Hour Surge** | Central | x1.30 (+30% demand) | 2 hours | Standard demand spike during commute peaks |
| **Concert at Marina Bay** | Central, South | x1.40 (+40% demand) | 3 hours | Entertainment event draws crowds to waterfront districts |
| **Changi Airport Rush** | East | x1.50 (+50% demand) | 2 hours | Flight arrivals/departures create the highest single-district demand spike |
| **Jurong Industrial Event** | West | x1.35 (+35% demand) | 2 hours | Industrial district shift changes or factory events |
| **Sentosa Weekend Crowd** | South | x1.40 (+40% demand) | 3 hours | Recreational island draws weekend visitors |
| **MRT Line Maintenance** | North, Central | x1.20 (+20% demand) | 2 hours | Also reduces MRT capacity on NSL (North South Line), forcing passengers onto buses and increasing road traffic |

### Event Lifecycle

1. **Trigger**: Each hour, the system rolls against the trigger probability. If successful, a random event is selected.
2. **Active**: The event's `demand_mult` is applied to all affected districts' demand calculations. Multiple events can stack multiplicatively.
3. **Expire**: Each hour, the event's `remaining_hours` decreases by 1. When it reaches 0, the event ends and its effects are removed.
4. **Agent response**: The planner observes increased load factors caused by events and proposes additional resources. The coordinator allocates based on urgency.

---

## Weather System

MetroMind simulates Singapore's tropical weather patterns with persistence and time-of-day variation.

### Weather Types

| Condition | Intensity Range | Effect on Transit | Frequency |
|-----------|----------------|-------------------|-----------|
| **Clear** | 0% | No impact | Most common |
| **Light Rain** | 20-50% | Mild demand increase (people avoid walking) | Moderate |
| **Heavy Rain** | 60-90% | Significant demand surge, reduced road speeds | Afternoon peak |
| **Thunderstorm** | 70-100% | Major disruption, high demand, dangerous conditions | Rare, afternoon |
| **Haze** | 30-70% | Reduced air quality, health concerns | Rare, morning |

### Weather Patterns by Time of Day

- **Afternoon (2-6pm)**: Highest chance of heavy rain (15%), thunderstorms (5%), light rain (20%) — reflecting Singapore's tropical afternoon convection pattern.
- **Morning (8-11am)**: Haze possibility (8%), light rain (10%) — morning haze dissipates by midday.
- **Other hours**: Mostly clear with occasional light rain (10%).

Weather conditions persist for 1-5 hours before transitioning.

---

## Out-of-Service Hours

Between **01:00 and 05:00**, MetroMind simulates Singapore's actual transit operating hours:

- All bus and train service units are set to **0 active**.
- Agent pipeline enters **standby mode** — no proposals, no allocation, no execution.
- Existing loads decay rapidly (x0.3 for bus/MRT loads, x0.4 for station crowding).
- Train frequencies are set to 0.
- The UI displays a prominent red banner: *"Out of Operating Hours: No Bus/Train Service (01:00-05:00)"*.
- District map shows "No Service" labels, train map shows dashed lines with reduced opacity.
- Live Interventions panel shows all agents in standby with explanatory notes.

At **06:00**, service resumes at 40% capacity and ramps up toward peak hours.

---

## Key Metrics and Scoring

### Liveability Score (0-100, higher is better)

Measures how well the transit system serves citizens. Penalises:
- Station crowding (35% weight) — heavily penalised as it affects safety
- Bus overload above 85% target (25% weight)
- MRT overload above 80% target (25% weight)
- Road traffic congestion (15% weight)

```
liveability = 100 - (
    35 * avg_station_crowding +
    25 * max(0, avg_bus_load - 0.85) +
    25 * max(0, avg_mrt_load - 0.80) +
    15 * avg_traffic
) * 100
```

### Environment Score (0-100, higher is better)

Measures environmental impact:
- Road traffic as emissions proxy (60% weight)
- Air quality degradation (40% weight)

```
environment = 100 - (
    0.6 * avg_traffic * 100 +
    0.4 * (100 - avg_air_quality)
)
```

### Carbon Emissions Tracking

- Bus emissions: 50 kg CO2 per unit per hour
- MRT emissions: 10 kg CO2 per unit per hour
- Traffic emissions: 100 kg CO2 x traffic factor per district

---

## Districts

| District | Population | Base Bus Capacity | Base MRT Capacity | Characteristics |
|----------|-----------|-------------------|-------------------|-----------------|
| **Central** | 500,000 | 120 | 40 | CBD area, highest density, most event-prone |
| **North** | 350,000 | 80 | 25 | Residential, connects to Malaysia via Woodlands |
| **East** | 380,000 | 85 | 28 | Airport district (Changi), tourism |
| **West** | 320,000 | 75 | 22 | Industrial (Jurong), manufacturing |

---

## Train Lines

| Line | Code | Colour | Base Frequency | Key Stations |
|------|------|--------|---------------|--------------|
| **North South Line** | NSL | Red | 14/hour | Woodlands, Yishun, Orchard, City Hall, Marina South |
| **East West Line** | EWL | Green | 14/hour | Tuas, Jurong, Dhoby Ghaut, Tampines, Changi |
| **North East Line** | NEL | Purple | 10/hour | Punggol, Serangoon, Dhoby Ghaut, HarbourFront |
| **Circle Line** | CCL | Orange | 12/hour | Bishan, Botanic Gardens, Bayfront, MacPherson (loop) |

All lines converge at **Dhoby Ghaut Interchange**.

---

## Why This is Agentic AI

MetroMind demonstrates the six key properties that define an agentic AI system:

| Property | How MetroMind Demonstrates It |
|----------|-------------------------------|
| **State over time** | City state persists across steps — districts accumulate load, events progress, weather evolves, emissions compound. Full history tracked for trend analysis. |
| **Goals** | Dual objectives: maximise liveability (reduce crowding, improve transit) AND maximise environmental sustainability (reduce emissions, improve air quality). These sometimes conflict. |
| **Autonomous actions** | Agents observe, reason, and act every step without human prompting. The planner generates reasoning, the coordinator makes trade-offs, the executor implements — all autonomously. |
| **Coordination** | Five agents with distinct roles coordinate through a structured pipeline. The planner proposes, policy validates, coordinator allocates scarce resources, executor implements. No single agent has unchecked authority. |
| **Feedback loop** | Actions change the environment, KPIs update, future observations differ, agents adapt. Adding buses reduces load, planner sees improvement, proposes fewer additions next step. |
| **Constraints/Safety** | Service unit limits (50 bus, 20 train), per-step caps (10 bus, 3 train), policy rules (no buses on gridlocked roads), reserve buffers (20%), and operating hour restrictions (01:00-05:00 shutdown). |

**Key insight**: This is not reactive rule-matching. The CoordinatorAgent makes genuine resource allocation trade-offs under scarcity, the PolicyAgent prevents unsafe actions even when urgency is high, and the PlannerAgent adapts its reasoning based on current conditions. Districts denied resources in one step receive higher priority in subsequent steps through the urgency scoring mechanism.

---

## Quick Start

### 1. Install Dependencies

```bash
cd metromind
pip install -r requirements.txt
```

### 2. Start the Backend

```bash
uvicorn backend.main:app --reload
```

The API will be available at `http://127.0.0.1:8000`

### 3. Open the Frontend

**Method 1 — VS Code Live Server**:
Open `frontend/index.html` then right-click and select "Open with Live Server"

**Method 2 — Python HTTP Server**:
```bash
cd metromind/frontend
python -m http.server 5500
```
Then open `http://localhost:5500`

### 4. Use the Dashboard

- **Hour dropdown**: Select a target hour — simulation auto-runs to that time
- **+/- buttons**: Step forward or backward by 1 hour
- **Reset**: Reset simulation to midnight, Day 1

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/state` | GET | Get current city state without advancing time |
| `/api/step` | POST | Advance simulation by 1 hour |
| `/api/simulate?hour=HH` | POST | Simulate forward to the specified hour (0-23) |
| `/api/step_hour?delta=1` | POST | Step forward 1 hour |
| `/api/step_hour?delta=-1` | POST | Step backward 1 hour (wraps via 23 forward steps) |
| `/api/run?n=N` | POST | Run N simulation steps (1-100) |
| `/api/reset` | POST | Reset city to initial state (midnight, Day 1) |

---

## Project Structure

```
metromind/
├── backend/
│   ├── main.py          # FastAPI application with CORS, endpoints, global city state
│   ├── models.py        # Data models (CityState, DistrictState, TrainLineState, WeatherState, ActiveEvent)
│   ├── env.py           # Environment dynamics (demand waves, weather, events, emissions)
│   ├── kpi.py           # KPI calculations (liveability score, environment score)
│   ├── orchestrator.py  # Main orchestration logic, service unit scaling, agent pipeline
│   └── agents/
│       ├── __init__.py      # Agent exports
│       ├── monitoring.py    # MonitoringAgent — observes city state, generates alerts
│       ├── planner.py       # CapacityPlannerAgent — proposes actions with urgency and reasoning
│       ├── policy.py        # PolicyAgent — validates constraints, blocks unsafe proposals
│       ├── coordinator.py   # CoordinatorAgent — allocates limited resources by urgency
│       └── executor.py      # ExecutionAgent — applies approved actions, logs interventions
├── frontend/
│   ├── index.html       # Dashboard UI (maps, controls, metrics, agent panels)
│   ├── app.js           # API calls, DOM updates, chart rendering, agent animations
│   └── styles.css       # Dark theme styling, responsive layout, capacity bar colours
├── requirements.txt     # Python dependencies (fastapi, uvicorn)
└── README.md            # This file
```
