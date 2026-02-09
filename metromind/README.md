# Contributors (not in any order)
Koh Qing Jia,  Wong Xuan Yu , Gwee Wei Lin , Anumitaa Murali , Etienne Wong , Siew Yuanlong

# MetroMind — Multi-Agent Mobility Orchestrator for Singapore

> **Five AI agents. One city. Real-time transit orchestration that balances service quality, operating cost, and sustainability — with demand forecasting, cost-aware dispatch, and human-in-the-loop escalation.**

MetroMind is an **agentic AI system** that autonomously manages Singapore's bus and MRT networks across 4 districts and 4 train lines. It simulates a realistic 24-hour transit cycle where coordinated agents must make **genuine trade-offs** — deploying limited resources under uncertainty, responding to weather and events, and knowing when to escalate to human operators.

---

## What Makes MetroMind Different

| Challenge | How MetroMind Solves It |
|-----------|------------------------|
| Transit operators **react** to overcrowding after it happens | **Demand forecasting** (1-3h lookahead) enables proactive reserve deployment |
| Deploying maximum capacity "just in case" is wasteful | **Cost-aware dispatch** tracks per-hour operating costs and optimises the liveability-cost tradeoff |
| AI recommends infrastructure changes operators can't execute in real-time | Every intervention is **operationally feasible** — short turns, headway holds, reserve deployment — used by SBS Transit/SMRT daily |
| Fully autonomous systems don't know their limits | **Human-in-the-loop escalation** for severe disruptions the AI shouldn't handle alone |
| Single-agent systems can't coordinate across competing districts | **Five specialised agents** with checks, balances, and urgency-based resource allocation |

---

## Table of Contents

1. [The Problem](#the-problem-service-planning-under-uncertainty)
2. [System Overview](#system-overview)
3. [Demo Walkthrough](#demo-walkthrough-a-day-in-singapores-transit)
4. [Multi-Agent Architecture](#multi-agent-architecture)
5. [Key Innovation 1: Forecast-Driven Planning](#key-innovation-1-forecast-driven-planning)
6. [Key Innovation 2: Cost-Aware Dispatch](#key-innovation-2-cost-aware-dispatch)
7. [Key Innovation 3: Feasible Interventions Only](#key-innovation-3-feasible-interventions-only)
8. [Key Innovation 4: Human-in-the-Loop Escalation](#key-innovation-4-human-in-the-loop-escalation)
9. [Detailed Agent Functions](#detailed-agent-functions)
10. [Simulation Environment](#simulation-environment)
11. [Scoring and KPIs](#scoring-and-kpis)
12. [Limitations and Future Work](#limitations-and-future-work)
13. [Why This is Agentic AI](#why-this-is-agentic-ai)
14. [Quick Start](#quick-start)
15. [API Reference](#api-reference)
16. [Project Structure](#project-structure)

---

## The Problem: Service Planning Under Uncertainty

Every day, Singapore's Land Transport Authority (LTA) faces a fundamental tension:

> **Deploy too many buses and trains** → waste fuel, crew hours, and operating budget
> **Deploy too few** → overcrowded stations, frustrated commuters, cascading delays

This tension is amplified by **uncertainty**. A thunderstorm at 5pm can spike MRT demand 15% in minutes. A concert at Marina Bay floods the Central district for 3 hours. A signal fault on the East-West Line displaces thousands onto buses and roads.

**Today's approach is largely reactive**: operators monitor dashboards, notice crowding, and scramble to deploy reserves. By the time extra buses arrive, the peak may have already passed — or worsened.

### What MetroMind Demonstrates

MetroMind shows how a **multi-agent AI system** could transform this from reactive firefighting to **proactive orchestration**:

1. **Forecast** demand 1-3 hours ahead using observed trends + base demand curves
2. **Plan** resource allocation based on both current conditions AND predicted future
3. **Validate** proposals against safety constraints and operational feasibility
4. **Allocate** limited resources across competing districts by urgency
5. **Execute** feasible interventions (reserve deployment, short turns, headway holds)
6. **Escalate** to human operators when the situation exceeds AI capability

All while tracking **operating costs** so the system doesn't just maximise service — it does so efficiently.

---

## System Overview

MetroMind simulates Singapore's public transit as a **realistic 24-hour cycle**:

- **4 districts**: Central (CBD, 500K pop), North (350K), East (380K, Changi Airport), West (320K, Jurong Industrial)
- **4 MRT lines**: North-South (NSL), East-West (EWL), North-East (NEL), Circle (CCL)
- **Service units**: 50 bus + 20 train capacity blocks (not individual vehicles — representing route bundles, crew shifts, and fleet segments)
- **Dynamic scaling**: 85% deployment at morning/evening peaks, 0% during 1-5am shutdown
- **Stochastic events**: Weather changes, concerts, airport rushes, signal faults, road accidents
- **Triple KPIs**: Liveability (0-100), Environment (0-100), Cost Efficiency (0-100)

Each simulation step = 1 hour. The dashboard shows real-time agent decisions, forecast predictions, cost tracking, and intervention logs.

---

## Demo Walkthrough: A Day in Singapore's Transit

Here's what happens when you run MetroMind through a typical day:

### 6:00 AM — Early Morning Ramp-Up
- Service units deploy at 40% capacity (20 bus, 8 train)
- Forecast predicts 85%+ load by 8am → **planner pre-positions reserves**
- Cost: ~220 CU/hour (low — efficient early morning)
- Planner reasoning: *"Central: forecast predicts 87% bus load in +2h — proactive reserve deployment"*

### 8:00 AM — Morning Peak
- 85% deployment (42 bus, 17 train units active)
- Demand surges across all districts, especially Central
- Agents deploy reserves, activate crowd management, hold headways
- **Policy blocks travel advisories** during peak: *"Blocked — passengers have no alternative during rush hour"*
- Cost: ~490 CU/hour (high but justified — avoids 25 CU crowding penalties per district)

### 2:00 PM — Afternoon + Thunderstorm
- Heavy rain triggers demand spike (+12% traffic, +8% station crowding)
- Forecast adjusts predictions upward by 15% for weather
- Agents deploy additional reserves proactively
- If MRT disruption occurs → **ESCALATE_TO_OPERATOR** triggered

### 6:00 PM — Evening Peak + Concert at Marina Bay
- Double pressure: commuter rush + event crowd in Central
- Coordinator faces genuine trade-off: Central demands +8 bus units, East needs +5, only 12 available after reserve
- **Central gets priority** (urgency 3.5) → East gets partial allocation (urgency 1.5)
- Cost peaks at ~550 CU/hour → cost efficiency score drops

### 10:00 PM — Wind-Down
- Demand eases. Forecast confirms low loads for next 3 hours
- Planner: *"Low demand (18%), forecast confirms easing — holding reserve to reduce cost"*
- Service units scale down to 25%
- Cost drops to ~150 CU/hour → cost efficiency recovers

### 1:00 AM — No Service
- All units go offline. Agents enter standby mode.
- Operating cost: **0 CU** (no active service)
- Dashboard shows red banner: "Out of Operating Hours"

---

## Multi-Agent Architecture

MetroMind uses a **sequential pipeline** of five specialised agents. No single agent has unchecked authority — proposals must survive validation, budget allocation, and execution.

```
                    ┌─────────────┐
                    │  Forecaster │  Predicts demand 1-3h ahead
                    └──────┬──────┘
                           ▼
┌─────────────┐    ┌──────────────┐    ┌─────────────┐    ┌──────────────┐    ┌─────────────┐
│   Monitor   │───▶│   Planner    │───▶│   Policy     │───▶│ Coordinator  │───▶│  Executor   │
│             │    │              │    │              │    │              │    │             │
│ Observes    │    │ Proposes     │    │ Validates    │    │ Allocates    │    │ Applies     │
│ city state  │    │ actions +    │    │ safety +     │    │ scarce       │    │ changes +   │
│ + alerts    │    │ reasoning    │    │ feasibility  │    │ resources    │    │ escalates   │
└─────────────┘    └──────────────┘    └─────────────┘    └──────────────┘    └─────────────┘
```

After agents act, the **MobilityEnvironment** advances the simulation: demand waves, weather, events, emissions, operating costs, and clock.

---

## Key Innovation 1: Forecast-Driven Planning

### The Problem with Reactive Dispatch

Without forecasting, agents can only respond **after** overcrowding occurs. By the time reserve buses are deployed, the surge may have passed — or worsened during the delay.

### How MetroMind Forecasts

The **DemandForecaster** uses exponential moving average (EMA) blended with base demand curves:

```
forecast[+h] = 0.3 * observed_trend + 0.7 * base_demand_curve[hour + h]
```

**Adjustments**:
- Weather boost: Heavy rain / thunderstorms increase predicted demand up to 15%
- Event multiplier: Active events (concerts, airport rushes) multiply the forecast
- Confidence bounds: Each prediction includes ±10-15% bands

### What This Enables

| Scenario | Without Forecast | With Forecast |
|----------|-----------------|---------------|
| Morning rush in 2 hours | Wait, react to overcrowding | Pre-position reserves now |
| Event ending soon | Keep extra capacity running | Hold reserves — demand about to ease, save cost |
| Thunderstorm starting | Scramble when demand spikes | Forecast already includes weather boost |
| Off-peak lull | Over-deploy "just in case" | Scale down to reduce cost |

### Forecast Alerts

When predicted load exceeds thresholds, the forecaster generates alerts visible in the planner trace and dashboard:
- *"Central bus demand forecast: 91% in +2h"*
- *"NSL load forecast: 84% in +1h"*

---

## Key Innovation 2: Cost-Aware Dispatch

### Why Cost Matters

Real transit authorities operate under budgets. Deploying every available bus at all times would maximise service but bankrupt the operator. MetroMind tracks **operating costs in Cost Units (CU) per hour**:

| Cost Component | Rate | When It Applies |
|---------------|------|-----------------|
| Active bus service unit | 8 CU/hour | Every deployed bus unit |
| Active train service unit | 12 CU/hour | Every deployed train unit |
| Idle reserve standby | 3 CU/unit/hour | Units available but not deployed (during operating hours) |
| Crowding penalty | 25 CU/district | Station crowding exceeds 90% (safety/brand cost) |
| Delay penalty | 15 CU/line | Train line disruption > 30% |
| Escalation penalty | 5 CU/event | Human operator intervention required |

### How Cost Influences Decisions

The planner and coordinator use cost signals:

- **Forecast confirms easing demand** → hold reserves instead of deploying → saves 8-12 CU/unit
- **Forecast predicts surge** → deploy proactively → avoids 25 CU crowding penalties that exceed unit costs
- **Multiple districts competing** → allocate to highest-urgency first → minimises total penalty
- **Low-demand hours** → fewer units deployed → lower cost → higher cost efficiency score

### Cost Efficiency Scoring

```
Cost Efficiency = max(0, 100 - (hourly_cost - 100) / 5)
```

| Hourly Cost | Score | Interpretation |
|-------------|-------|----------------|
| 100 CU | 100 | Efficient off-peak operation |
| 350 CU | 50 | Moderate peak deployment |
| 600+ CU | 0 | Over-deployed or penalty-heavy |

---

## Key Innovation 3: Feasible Interventions Only

Every intervention MetroMind recommends is something a Singapore transit operator **can actually execute in real-time**:

| Intervention | Type | Real-World Basis |
|-------------|------|-----------------|
| **DEPLOY_RESERVE** | Bus | Activate standby buses + crew from depot — done daily by SBS Transit |
| **SHORT_TURN** | Bus | Cut route short to boost frequency on congested segment — standard SMRT practice |
| **HOLD_AT_TERMINAL** | Bus | Hold buses at termini to regulate headway, reduce bunching |
| **REROUTE_AROUND_INCIDENT** | Bus | Divert buses around road accident — standard operations |
| **ADD_TRAINS** | Train | Run additional train sets from depot during peak |
| **HOLD_HEADWAY** | Train | Hold trains at stations for even spacing — used on MRT daily |
| **TRAVEL_ADVISORY** | Demand | App notification for off-peak travel — **only during off-peak hours** |
| **CROWD_MGMT** | Station | Barrier management, crowd announcements, flow control |
| **ESCALATE_TO_OPERATOR** | Human | Alert human operator for manual judgement |

### What We Removed (and Why)

- ~~**Dedicated bus lanes**~~ — requires months of urban planning and infrastructure changes. Not a real-time dispatch lever.
- ~~**Peak-hour nudges**~~ — telling commuters "travel off-peak" at 8am when they're heading to work is not actionable. Advisory now **blocked during 7-9am and 5-7pm** by the PolicyAgent.

---

## Key Innovation 4: Human-in-the-Loop Escalation

Fully autonomous systems should **know their limits**. MetroMind includes an explicit escalation path:

### When Escalation Triggers

- Station crowding > 95% **AND** bus load > 95% (district-level crisis)
- Train line disruption > 50% (severe service breakdown)

### What Happens

1. System records an **escalation event** with reason, target, and timestamp
2. Dashboard displays escalation prominently in the interventions panel
3. A **cost penalty** (5 CU) is applied to reflect operational overhead
4. The planner's reasoning trace explains why it escalated

### Why This Matters

Severe multi-modal disruptions — MRT signal fault during a thunderstorm at rush hour — may require human judgement: coordinating with emergency services, making policy decisions, or managing public communications. MetroMind is designed as an **AI assistant to human operators**, not a replacement.

---

## Detailed Agent Functions

### 1. MonitoringAgent — The Eyes and Ears

Observes the full city state every hour:
- Per-district: bus load, MRT load, station crowding, road traffic, air quality
- Per-train-line: load, frequency, disruption level
- System-wide: weather, operating cost, active events

Generates human-readable alerts (e.g., *"CRITICAL: Central station crowding at 94%"*, *"High operating cost: 523 CU this hour"*, *"Road incident active in West"*).

### 2. CapacityPlannerAgent — The Strategic Thinker

Analyses observations **and demand forecasts** to produce per-district bus proposals and per-line train proposals. Each proposal carries:
- **Action**: what to do (DEPLOY_RESERVE, SHORT_TURN, etc.)
- **Urgency score**: priority for resource allocation (+2.0 for critical crowding, +1.0 for overload, +0.5 for traffic/air quality)
- **Reasoning**: human-readable explanation of the decision

Forecast-aware behaviour:
- Forecast predicts high load → proactive deployment even if current load is fine
- Forecast confirms easing demand → holds reserves to reduce cost

### 3. PolicyAgent — The Safety Regulator

Validates all proposals against hard constraints:

| Rule | What It Does |
|------|-------------|
| Traffic limit | Blocks DEPLOY_RESERVE when roads are gridlocked (>80%) → converts to SHORT_TURN |
| Bus cap | Clamps bus additions to max 10 per district per hour |
| Train cap | Clamps train additions to max 3 per line per hour |
| Crowding gate | Removes CROWD_MGMT if crowding < 90% |
| **Peak advisory block** | **Blocks travel advisories during peak hours (7-9am, 5-7pm)** — passengers have no alternative |
| Advisory gate | Removes advisory if crowding < 70% AND traffic < 75% |

### 4. CoordinatorAgent — The Resource Allocator

The core of MetroMind's multi-agent coordination. Takes validated proposals from all districts and allocates **limited global resources**:

1. Compute available capacity = active units - 20% reserve buffer
2. Sort proposals by urgency (highest first)
3. Allocate: each district gets `min(requested, remaining)`
4. When capacity exhausts, lower-urgency districts are denied

**This creates real trade-offs**: at 8am with 42 bus units active (34 available after reserve), Central (urgency 3.5) gets full allocation, North (urgency 1.0) gets partial, West may be denied entirely.

### 5. ExecutionAgent — The Implementer

Applies approved actions to the city state in priority order:
1. Crowd management (safety first)
2. Bus actions (DEPLOY_RESERVE, SHORT_TURN, HOLD_AT_TERMINAL, REROUTE)
3. Train actions (ADD_TRAINS, HOLD_HEADWAY)
4. Travel advisory (off-peak only)
5. Escalation (records event, applies cost penalty)

Every action is logged as a structured event with timestamp, district/line, actions taken, and urgency.

---

## Simulation Environment

### Districts

| District | Population | Base Bus Cap | Base MRT Cap | Character |
|----------|-----------|-------------|-------------|-----------|
| **Central** | 500,000 | 120 | 40 | CBD core, highest density, most events |
| **North** | 350,000 | 80 | 25 | Residential, Woodlands border crossing |
| **East** | 380,000 | 85 | 28 | Changi Airport, tourism hub |
| **West** | 320,000 | 75 | 22 | Jurong industrial zone |

### Train Lines

| Line | Code | Colour | Base Freq | Key Stations |
|------|------|--------|-----------|--------------|
| North South Line | NSL | Red | 14/h | Woodlands → Orchard → City Hall → Marina South |
| East West Line | EWL | Green | 14/h | Tuas → Jurong → Dhoby Ghaut → Tampines → Changi |
| North East Line | NEL | Purple | 10/h | Punggol → Serangoon → Dhoby Ghaut → HarbourFront |
| Circle Line | CCL | Orange | 12/h | Bishan → Botanic Gardens → Bayfront → MacPherson (loop) |

All lines converge at **Dhoby Ghaut Interchange**.

### Service Unit Scaling

Service units deploy dynamically by hour of day:

| Period | Bus Active | Train Active | Notes |
|--------|-----------|-------------|-------|
| 01:00-05:00 | 0 (0%) | 0 (0%) | **No service** — mirrors real Singapore operations |
| 06:00 | 20 (40%) | 8 (40%) | Morning ramp-up |
| **08:00** | **42 (85%)** | **17 (85%)** | **Morning peak** |
| 12:00 | 28 (55%) | 11 (55%) | Midday |
| **18:00** | **42 (85%)** | **17 (85%)** | **Evening peak** |
| 22:00 | 12 (25%) | 4 (18%) | Late night wind-down |

### Events (Stochastic)

| Event | Districts | Demand Impact | Duration | Special |
|-------|-----------|--------------|----------|---------|
| Rush Hour Surge | Central | +30% | 2h | Standard peak |
| Concert at Marina Bay | Central | +40% | 3h | Entertainment |
| Changi Airport Rush | East | +50% | 2h | Highest spike |
| Jurong Industrial Event | West | +35% | 2h | Shift change |
| MRT Line Maintenance | North, Central | +20% | 2h | Reduces NSL capacity |
| Station Crowd Surge | Central | +45% | 1h | Severe crowding |
| Train Signal Fault | Central, East | +25% | 2h | Reduces EWL capacity |
| Road Incident (Accident) | West | +15% | 1h | Triggers REROUTE |

### Weather

Singapore's tropical patterns with persistence:

| Condition | Effect on Transit | Peak Probability |
|-----------|------------------|-----------------|
| Clear | None | Default |
| Light Rain | +5% traffic, +3% crowding | 10-20% |
| Heavy Rain | +12% traffic, +8% crowding, forecast boost | 15% afternoon |
| Thunderstorm | +15% traffic, +10% crowding, MRT disruption risk | 5% afternoon |
| Haze | -15 air quality | 8% morning |

---

## Scoring and KPIs

MetroMind tracks three composite scores (0-100, higher is better):

### Liveability Score
How well transit serves citizens:
- Station crowding penalty (35% weight)
- Bus overload above 85% target (25%)
- MRT overload above 80% target (25%)
- Road traffic congestion (15%)

### Environment Score
Environmental impact:
- Road traffic as emissions proxy (60%)
- Air quality degradation (40%)

### Cost Efficiency Score
Operating cost discipline:
- 100 CU/hour → 100 (efficient)
- 350 CU/hour → 50 (moderate)
- 600+ CU/hour → 0 (over-deployed)

### Carbon Emissions
- Bus: 50 kg CO2/unit/hour
- MRT: 10 kg CO2/unit/hour
- Traffic: 100 kg CO2 × traffic factor per district

---

## Limitations and Future Work

MetroMind is a **simulation prototype** demonstrating multi-agent transit orchestration architecture, not a production system.

### Current Limitations

| Limitation | What a Production System Would Need |
|-----------|-------------------------------------|
| Aggregate load factors per district | Origin-destination matrices, per-station passenger counts |
| Service unit abstraction | Route-level scheduling (specific bus routes, stops, timetables) |
| Probabilistic events | Real-time event feeds (LTA DataMall, social media, CCTV) |
| No passenger choice model | Mode switching simulation (bus ↔ MRT ↔ car based on service quality) |
| Simple EMA forecasting | ML-based demand prediction trained on historical ridership data |

### Future Extensions

- **Real LTA data integration**: DataMall API for live bus/train positions, ridership
- **ML demand forecasting**: Replace EMA with time-series models (Prophet, LSTM) trained on real data
- **Multi-modal passenger routing**: Simulate individual passenger decisions across modes
- **LLM-powered reasoning**: Use LLM agents for natural-language operator briefs and scenario planning
- **Real-time dashboard**: WebSocket-based live updates instead of polling

---

## Why This is Agentic AI

| Agentic Property | How MetroMind Demonstrates It |
|------------------|-------------------------------|
| **Persistent state** | City state accumulates across hours — load, events, costs, history. No step is independent. |
| **Multiple competing goals** | Maximise liveability, minimise environmental impact, **AND** optimise operating cost. These genuinely conflict. |
| **Autonomous reasoning** | Agents observe, forecast, reason, propose, validate, allocate, and execute — all without human prompting. |
| **Multi-agent coordination** | Five agents with distinct roles, checks, and balances. The coordinator makes genuine resource allocation trade-offs under scarcity. |
| **Environment feedback loop** | Actions change the city → KPIs update → future observations differ → agents adapt their reasoning. |
| **Safety constraints** | Service unit limits, per-step caps, policy rules, peak-hour blocks, reserve buffers, operating hours, **and human escalation**. |
| **Proactive planning** | Demand forecasting enables pre-positioning reserves **before** surges — not just reacting after the fact. |

**The key insight**: This is not rule-matching. The CoordinatorAgent makes **genuine resource allocation trade-offs** under scarcity. The PolicyAgent prevents unsafe actions even when urgency is high. The PlannerAgent adapts reasoning based on forecasts. Districts denied resources receive higher priority next step through urgency scoring. The system knows when to **escalate to humans** rather than acting beyond its capability.

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

API available at `http://127.0.0.1:8000`

### 3. Open the Frontend

**Option A — VS Code Live Server**: Open `frontend/index.html` → right-click → "Open with Live Server"

**Option B — Python HTTP Server**:
```bash
cd metromind/frontend
python -m http.server 5500
```
Open `http://localhost:5500`

### 4. Use the Dashboard

| Control | What It Does |
|---------|-------------|
| **Hour dropdown** | Select target hour — simulation runs to that time |
| **+/- buttons** | Step forward or backward 1 hour |
| **Reset** | Return to midnight, Day 1 |
| **Bus/Train Map tabs** | Switch between district load map and train line schematic |
| **Forecast panel** | Shows predicted demand (+1h, +2h, +3h) per district with colour-coded bars |
| **Cost card** | Current hour cost and daily total in Cost Units (CU) |
| **Agent Orchestra** | Real-time agent activation status during simulation |
| **Live Interventions** | Full agent decision trace (monitor alerts → planner reasoning → policy blocks → coordinator allocations → executor actions) |

---

## API Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/state` | GET | Current city state (scores, metrics, forecast, cost, events) |
| `/api/step` | POST | Advance 1 hour |
| `/api/simulate?hour=HH` | POST | Simulate forward to target hour (0-23) |
| `/api/step_hour?delta=1` | POST | Step +1 hour |
| `/api/step_hour?delta=-1` | POST | Step -1 hour (wraps via 23 forward steps) |
| `/api/run?n=N` | POST | Run N steps (1-100) |
| `/api/reset` | POST | Reset to midnight, Day 1 |

All endpoints return the full city state payload including scores, metrics, agent traces, forecast data, cost breakdown, and operator escalations.

---

## Project Structure

```
metromind/
├── backend/
│   ├── main.py            # FastAPI app — CORS, endpoints, global city state
│   ├── models.py          # Data models, cost constants, event definitions
│   ├── env.py             # Environment simulation (demand, weather, events, emissions, cost)
│   ├── kpi.py             # KPI scoring (liveability, environment, cost efficiency)
│   ├── forecast.py        # Demand forecaster (EMA + base curves, weather/event adjustments)
│   ├── orchestrator.py    # Main orchestration — service scaling, forecast+cost integration
│   └── agents/
│       ├── __init__.py        # Agent exports
│       ├── monitoring.py      # MonitoringAgent — city state observation, alerts
│       ├── planner.py         # CapacityPlannerAgent — forecast-driven, cost-aware proposals
│       ├── policy.py          # PolicyAgent — safety constraints, peak-hour advisory blocks
│       ├── coordinator.py     # CoordinatorAgent — urgency-based resource allocation
│       └── executor.py        # ExecutionAgent — action execution, operator escalation
├── frontend/
│   ├── index.html         # Dashboard (maps, forecast panel, cost card, agent panels)
│   ├── app.js             # API calls, DOM updates, forecast/cost rendering, animations
│   └── styles.css         # Dark theme, responsive layout
├── requirements.txt       # Python dependencies (fastapi, uvicorn)
└── README.md              # This file
```

---

*Built for the Hack for Cities 2025 Hackathon.*
