# UrbanPulse — Agentic Mobility Orchestrator (Hackathon Build Spec)

This document is a **coding blueprint** for implementing a hackathon-ready “Agentic AI” prototype based on our discussion. It is written to be fed into Claude (or another coding model) to generate the full codebase.

**Goal:** Extend the existing Python simulation into a proper **multi-agent system** with:
- clear city-wide KPIs (liveability + environment),
- memory/budget constraints,
- coordinator-based allocation and policy constraints,
- action logs + feedback loop,
- a backend API (FastAPI),
- a simple frontend dashboard you can run via **VS Code Live Server**.

---

## 0) Non-Negotiables (How the system must behave)

### Agentic requirements (must show in demo)
The system must demonstrate:
1. **State over time** (persistent city state, history, scores)
2. **Goals** (liveability + environmental targets)
3. **Autonomous actions** (no manual prompting each step)
4. **Coordination** (multiple agents propose; coordinator resolves conflicts)
5. **Feedback loop** (actions change environment; KPIs update; future actions adapt)
6. **Constraints / safety** (budgets, max change rates, and policy rules)

### Demo requirement
The system must be runnable locally:
- Backend: `uvicorn backend.main:app --reload`
- Frontend: static HTML/JS that calls the backend API, hosted with **Live Server**.

---

## 1) What you already have
You already have:
- `CityState`, `DistrictState`
- `MobilityEnvironment.step()` dynamics
- Agents: `MonitoringAgent`, `CapacityPlannerAgent`, `ExecutionAgent`
- A main loop that prints actions and metrics

We will build on this by:
- adding **scores**,
- changing the planner to produce **proposals** (not directly execute),
- adding a **CoordinatorAgent** to allocate limited budgets,
- adding **action logs**,
- exposing everything via **FastAPI**,
- adding a **frontend dashboard**.

---

## 2) Target architecture (final)

### Backend (FastAPI)
- Maintains one in-memory `CityState` (for demo).
- Provides endpoints to:
  - view state + metrics + scores,
  - advance 1 step,
  - reset simulation,
  - run N steps.

### Agents
- MonitoringAgent: observes state
- CapacityPlannerAgent: proposes actions per district (bus/train/crowd/nudge)
- PolicyAgent: validates proposals (rules/constraints)
- CoordinatorAgent: allocates global budgets fairly
- ExecutionAgent: applies approved actions and records action logs
- Environment: updates system with demand waves and response effects

### Frontend (static)
A single HTML page that shows:
- current time step
- city-wide scores (Liveability, Environment)
- district table with key fields
- action feed (latest decisions)
- charts (history over time, simple line plots)

---

## 3) Folder structure (create exactly)

urbanpulse/
backend/
main.py
models.py
env.py
kpi.py
orchestrator.py
agents/
monitoring.py
planner.py
policy.py
coordinator.py
executor.py
frontend/
index.html
app.js
styles.css
requirements.txt
README.md


---

## 4) Core data model changes

### A) Add budgets + logs to CityState
Add:
- `bus_budget: int` (total extra buses/hour available globally)
- `mrt_budget: int` (total extra trains/hour available globally)
- `action_log: list[dict]` (append each step’s approved actions)

Example fields:
- `bus_budget = 40`
- `mrt_budget = 12`

### B) Add per-district “nudges_active” flag
Add to `DistrictState`:
- `nudges_active: bool = False`

If nudges are active, the environment reduces demand slightly.

---

## 5) KPIs & Scores (must implement)

Create `backend/kpi.py` with:
- `snapshot_metrics(city: CityState) -> dict`
- `score(city: CityState) -> dict` returning:
  - `liveability_score` in [0, 100]
  - `environment_score` in [0, 100]

### City-wide score logic (use this exact formula first; tweak later if needed)
Let `snap = city.snapshot_metrics()`.

Liveability (higher is better):
- penalise station crowding heavily
- penalise overload above target LF
- penalise traffic



liveability = 100 - (
35 * snap["avg_station"] +
25 * max(0, snap["avg_bus_load"] - BUS_TARGET_LF) +
25 * max(0, snap["avg_mrt_load"] - MRT_TARGET_LF) +
15 * snap["avg_traffic"]
) * 100


Environment (higher is better):
- penalise traffic (proxy emissions) and poor air quality



environment = 100 - (
0.6 * snap["avg_traffic"] * 100 +
0.4 * (100 - snap["avg_air"])
)


Clamp both into [0, 100].

---

## 6) Planner → Proposals (key refactor)

### Current problem
Your `CapacityPlannerAgent` decides and `ExecutionAgent` immediately applies.

### Required change
Planner must output a **proposal object** for each district, e.g.:



{
"district": "Central",
"bus_action": "ADD_BUSES" | "USE_BUS_PRIORITY" | "NO_CHANGE",
"bus_extra": int,
"mrt_action": "ADD_TRAINS" | "NO_CHANGE",
"mrt_extra": int,
"do_crowd_mgmt": bool,
"do_nudge": bool,
"urgency": float
}


### Urgency score (simple, judge-friendly)
Compute urgency as:
- +2.0 if station crowding > critical
- +1.0 if bus_load > BUS_TARGET_LF
- +1.0 if mrt_load > MRT_TARGET_LF
- +0.5 if road_traffic high (> 0.75)
- +0.5 if air_quality low (< 60)

This will be used by the coordinator.

---

## 7) Add PolicyAgent (safety constraints)

Create `backend/agents/policy.py`.

Policy rules to enforce:
1. If `road_traffic > TRAFFIC_BUS_ADD_LIMIT`, planner may propose `USE_BUS_PRIORITY` but should not add buses.
2. `bus_extra` must be clamped to `[0, BUS_MAX_EXTRA]`.
3. `mrt_extra` clamped to `[0, MRT_MAX_EXTRA]`.
4. If `station_crowding > CROWDING_CRITICAL`, allow crowd management.
5. Nudges can only activate when crowding OR traffic is high.

PolicyAgent should take proposals and return **sanitised proposals**.

---

## 8) Add CoordinatorAgent (global allocation)

Create `backend/agents/coordinator.py`.

### Why it matters
This is what makes the system “multi-agent coordination” and not just reactive rules.

### Allocation algorithm (implement exactly first)
Input: `city` and `proposals_by_district`.

Steps:
1. Sort districts by `urgency` descending.
2. Allocate from `city.bus_budget` and `city.mrt_budget`:
   - `approved_bus_extra = min(proposed_bus_extra, bus_left)`
   - `approved_mrt_extra = min(proposed_mrt_extra, mrt_left)`
3. Reduce remaining budgets.
4. Return `approved_proposals`.

### Fairness improvement (optional but recommended)
Add a “starvation guard”:
- track if a district has not received resources for last N steps
- add small urgency bonus if starved

This can be implemented later; keep the first version simple.

---

## 9) ExecutionAgent changes (apply approved actions + log)

Create `backend/agents/executor.py`.

ExecutionAgent must:
- Apply crowd mgmt first (safety)
- Apply MRT changes
- Apply bus changes or bus priority
- Apply nudges (`nudges_active = True` for that district) if approved
- Write a structured action event into `city.action_log` like:



{
"t": city.t,
"district": "Central",
"actions": [
"CROWD_MGMT",
"ADD_TRAINS +2",
"BUS_PRIORITY"
]
}


---

## 10) Environment changes (nudges + better feedback)

In `backend/env.py`, modify step logic:
- If `nudges_active`, reduce demand wave by `0.03` (or similar).
- Optionally: nudges decay after a few steps (e.g., deactivate after 3 steps).

Keep it simple:
- add `nudge_timer: int` in DistrictState or store a dict in CityState.
- If too complex, just let nudges last 1 step.

---

## 11) Orchestrator (single source of truth)

Create `backend/orchestrator.py`.

Provide functions:
- `make_city() -> CityState` (your existing function)
- `step(city: CityState) -> dict` runs:
  1. observe
  2. propose (planner)
  3. policy sanitisation
  4. coordination allocation
  5. execute approved actions
  6. environment step
  7. compute metrics + scores
  8. return payload for API

Return payload example:


{
"t": city.t,
"scores": {...},
"metrics": {...},
"districts": {...},
"actions": [... last step actions ...],
"history_tail": [... last 50 snapshots ...]
}


---

## 12) FastAPI backend

Create `backend/main.py` with:
- global `city = make_city()`
- endpoints:

### Endpoints (required)
1. `GET /api/state`
   - return current payload (no stepping)

2. `POST /api/step`
   - advance 1 step, return payload

3. `POST /api/run?n=10`
   - run N steps, return payload

4. `POST /api/reset`
   - reset the city to initial state

### CORS
Enable CORS for `http://127.0.0.1:5500` (Live Server default).

---

## 13) Frontend (static, Live Server)

Create `frontend/index.html` with:
- Title + description
- Buttons: “Step”, “Run 10”, “Reset”
- Cards for Liveability + Environment scores
- Table for districts
- Action feed (latest 20 actions)
- A simple chart area:
  - Use Chart.js via CDN (fastest)
  - Plot liveability and environment over time

### frontend/app.js behavior
- `fetchState()` calls `/api/state`
- `step()` calls `/api/step`
- `run10()` calls `/api/run?n=10`
- `reset()` calls `/api/reset`
- Update DOM:
  - scores
  - district table
  - action feed
  - charts (append datapoints)

### How to run
1. In terminal:
   - `pip install -r requirements.txt`
   - `uvicorn backend.main:app --reload`
2. Open `frontend/index.html` using **Live Server**
3. Click Step / Run 10 and watch metrics + actions update

---

## 14) requirements.txt (minimum)
Include:
- `fastapi`
- `uvicorn`
- `pydantic` (if needed)
- (optional) `numpy` (only if you use it)

---

## 15) “Self-fixing” coding instructions for Claude (IMPORTANT)

When generating and running code, Claude must follow this loop:

### Debug & Fix Loop (must obey)
1. Generate code changes.
2. Run the code locally (simulate by reasoning if no runtime is available).
3. If errors occur:
   - Read the full traceback / console errors.
   - Identify the root cause.
   - Apply the smallest correct fix.
   - Re-run.
4. Repeat until:
   - Backend starts without errors,
   - Frontend can successfully fetch and render state,
   - Step/Run/Reset work.

### Output format rules (for Claude)
- Claude should output:
  1. full file contents for any new files
  2. patch-style diffs or full replacements for modified files
  3. clear run commands
- Claude must NOT leave “TODO” placeholders for critical logic.

### Common issues Claude must handle
- CORS errors → fix FastAPI CORS middleware
- Chart.js rendering bugs → ensure canvas exists and chart instance is reused/updated
- JSON serialization issues (dataclasses) → convert to dicts explicitly
- State mutation bugs → ensure `city.t` increments and history appended correctly
- Frontend fetch failing → check URL/port and endpoint paths

---

## 16) Acceptance checklist (definition of “done”)

### Backend
- [ ] `GET /api/state` works
- [ ] `POST /api/step` advances time and returns updated payload
- [ ] `POST /api/reset` resets time and history
- [ ] `POST /api/run?n=10` runs multiple steps
- [ ] Action logs appear and match decisions
- [ ] Scores are returned and move over time

### Frontend
- [ ] Opens via Live Server
- [ ] Buttons call backend and update UI
- [ ] District table updates live
- [ ] Action feed shows latest actions
- [ ] Chart shows liveability/environment history

### Agentic proof
- [ ] Planner proposes actions per district
- [ ] Policy sanitises proposals
- [ ] Coordinator allocates limited budgets across districts
- [ ] Execution applies approved actions
- [ ] Environment updates and affects next decisions

---

## 17) Reference (hackathon context)
This build is aligned with the hackathon requirement for **Agentic AI** improving **urban liveability** and **environmental outcomes** at district/nationwide level. :contentReference[oaicite:0]{index=0}