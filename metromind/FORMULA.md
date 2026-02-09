# MetroMind v2 — Mathematical Formulas & Decision Logic

This document explains every formula, threshold, and decision rule used in the MetroMind multi-agent mobility orchestrator. It covers the simulation environment, demand forecasting, agent decision-making, cost model, and KPI scoring.

---

## Table of Contents

1. [Constants](#1-constants)
2. [Demand Wave (Time-of-Day Pattern)](#2-demand-wave-time-of-day-pattern)
3. [Weather Modifiers](#3-weather-modifiers)
4. [District Dynamics](#4-district-dynamics)
5. [Train Line Dynamics](#5-train-line-dynamics)
6. [Demand Forecasting (EMA Model)](#6-demand-forecasting-ema-model)
7. [Operating Cost Model](#7-operating-cost-model)
8. [Carbon Emissions Model](#8-carbon-emissions-model)
9. [KPI Scoring (Triple Score)](#9-kpi-scoring-triple-score)
10. [Agent Decision Logic](#10-agent-decision-logic)
11. [Capacity Decay & Sustainability](#11-capacity-decay--sustainability)
12. [Service Unit Scaling](#12-service-unit-scaling)

---

## 1. Constants

| Constant | Value | Description |
|----------|-------|-------------|
| `BUS_TARGET_LF` | 0.85 | Target bus load factor (85%) |
| `MRT_TARGET_LF` | 0.80 | Target MRT load factor (80%) |
| `CROWDING_CRITICAL` | 0.90 | Critical station crowding threshold |
| `TRAFFIC_BUS_ADD_LIMIT` | 0.80 | Road traffic level above which bus deployment is blocked |
| `BUS_MAX_EXTRA` | 10 | Max additional bus units per district per hour |
| `MRT_MAX_EXTRA` | 3 | Max additional train units per line per hour |
| `CAPACITY_DECAY_RATE` | 0.05 | Rate at which added capacity decays back to baseline (5%/hour) |
| `BUS_EMISSIONS` | 50 | kg CO2 per bus unit per hour |
| `MRT_EMISSIONS` | 10 | kg CO2 per train unit per hour |
| `TRAFFIC_EMISSIONS_FACTOR` | 100 | Emissions factor for road traffic |
| `COST_BUS_ACTIVE` | 8.0 | Cost units per active bus service unit per hour |
| `COST_TRAIN_ACTIVE` | 12.0 | Cost units per active train service unit per hour |
| `COST_RESERVE_IDLE` | 3.0 | Cost units per idle reserve unit per hour (standby) |
| `COST_CROWDING_PENALTY` | 25.0 | Penalty per district with crowding > 90% |
| `COST_DELAY_PENALTY` | 15.0 | Penalty per train line with disruption > 30% |
| `COST_ESCALATION_PENALTY` | 5.0 | Cost per escalation event |
| `PEAK_HOURS` | {7,8,9,17,18,19} | Hours during which travel advisories are blocked |
| `NO_SERVICE_HOURS` | {1,2,3,4,5} | Hours with no bus/train service |
| `ALPHA` (forecast) | 0.3 | EMA smoothing parameter |

---

## 2. Demand Wave (Time-of-Day Pattern)

The base demand multiplier `D(h)` models Singapore's bimodal commute pattern:

```
For h in [1, 5):   D(h) = 0.02      (near-zero demand overnight)
For h = 0:          D(h) = 0.08      (late-night residual)
For h = 5:          D(h) = 0.15      (early morning ramp-up)

For h in [6, 23]:
    morning_rush  = exp(-(h - 8)^2 / 4)       Gaussian peak at 08:00
    evening_rush  = exp(-(h - 18)^2 / 4)      Gaussian peak at 18:00
    midday        = 0.4  if 10 <= h <= 16      Flat midday plateau
    late_decline  = max(0, 0.3 - 0.1*(h-21))  if h >= 21, linear decline

    D(h) = min(1.0, max(morning_rush, evening_rush, midday, late_decline))
```

**Key values:**

| Hour | D(h) | Period |
|------|------|--------|
| 00:00 | 0.08 | Late night |
| 01-04 | 0.02 | No service |
| 05:00 | 0.15 | Early morning |
| 08:00 | 1.00 | Morning peak (Gaussian max) |
| 12:00 | 0.40 | Midday plateau |
| 18:00 | 1.00 | Evening peak (Gaussian max) |
| 23:00 | ~0.10 | Late decline |

---

## 3. Weather Modifiers

Weather affects traffic, crowding, bus performance, air quality, and train disruptions. Intensity `I` ranges from 0.0 to 1.0.

| Condition | Traffic Mod | Crowding Mod | Bus Penalty | Air Penalty | Disruption Boost |
|-----------|-------------|--------------|-------------|-------------|------------------|
| Clear | 0 | 0 | 0 | 0 | 0 |
| Light Rain | 0.05 * I | 0.03 * I | 0.02 * I | 0 | 0 |
| Heavy Rain | 0.12 * I | 0.08 * I | 0.06 * I | 0 | 0 |
| Thunderstorm | 0.15 * I | 0.10 * I | 0.08 * I | 0 | 0.15 * I |
| Haze | 0 | 0 | 0 | 15 * I | 0 |

**Disruption boost** (Thunderstorm only): Each train line has a `disruption_boost * 0.3` probability of gaining +0.1 disruption level per hour.

---

## 4. District Dynamics

Each district is processed every simulation step using exponential smoothing. The core smoothing function is:

```
smooth(current, target, rate) = current + rate * (target - current)
```

This is a first-order exponential filter where `rate` controls responsiveness (0 = no change, 1 = instant snap).

### 4.1 Bus Load Factor

```
effective_demand = D(h) * event_demand_multiplier

nudge_reduction = 0.03  if travel_advisory_active, else 0.0

base_bus_demand = effective_demand * 0.85 + 0.05 - nudge_reduction + weather_bus_penalty

target_bus_load = base_bus_demand * (90 / bus_capacity)

bus_load_factor = smooth(bus_load_factor, target_bus_load, rate=0.4)
bus_load_factor = clamp(0.02, 1.2)
```

**Interpretation:** Higher capacity lowers the load factor (more buses spread the demand). The constant `90` is the reference capacity; when `bus_capacity = 90`, load equals demand directly.

### 4.2 MRT Load Factor

```
base_mrt_demand = effective_demand * 0.80 + 0.05 - nudge_reduction

target_mrt_load = base_mrt_demand * (40 / mrt_capacity)

mrt_load_factor = smooth(mrt_load_factor, target_mrt_load, rate=0.4)
mrt_load_factor = clamp(0.02, 1.2)
```

### 4.3 Station Crowding

```
target_crowding = 0.5 * mrt_load_factor + 0.4 * effective_demand + weather_crowding_mod

station_crowding = smooth(station_crowding, target_crowding, rate=0.35)
station_crowding = clamp(0.0, 1.0)
```

**Interpretation:** Station crowding is driven 50% by MRT load (trains full = platforms full) and 40% by overall demand, plus weather effects.

### 4.4 Road Traffic

```
transit_spillover = max(0, bus_load_factor - 0.9) * 0.5

road_incident_traffic = 0.15  if road_incident_active, else 0.0

base_traffic = 0.08 + 0.5 * effective_demand + transit_spillover
             + weather_traffic_mod + road_incident_traffic

road_traffic = smooth(road_traffic, base_traffic, rate=0.3)
road_traffic = clamp(0.05, 1.0)
```

**Transit spillover:** When buses are >90% full, excess riders spill onto roads (take taxis/private cars).

### 4.5 Air Quality

```
target_air = 90 - 40 * road_traffic - weather_air_penalty

air_quality = smooth(air_quality, target_air, rate=0.15)
air_quality = clamp(20, 100)
```

**Interpretation:** Air quality degrades with road traffic (vehicle emissions) and haze conditions.

---

## 5. Train Line Dynamics

Each train line (CCL, NEL, EWL, NSL) has independent load and disruption levels.

### 5.1 Train Load

```
target_load = D(h) * 0.85 + 0.05

# Event disruptions (e.g., signal fault on EWL)
if line is affected by MRT-reducing event:
    target_load *= 1.2
    disruption_level += 0.3

# Disruption effect (fewer trains running = more crowded per train)
target_load *= (1 + disruption_level * 0.3)

# Frequency effect (adding trains reduces per-train load)
freq_ratio = base_frequency / max(current_frequency, 1)
target_load *= freq_ratio

# Weather pushes more people to trains
target_load += weather_crowding_mod * 0.5

line_load = smooth(line_load, target_load, rate=0.4)
line_load = clamp(0.02, 1.2)
```

**Key insight:** The `freq_ratio` formula means adding trains (increasing frequency above baseline) directly reduces the load per train.

### 5.2 Disruption Decay

```
disruption_level = max(0, disruption_level - 0.05)   per hour
```

Disruptions heal at 5% per hour naturally.

### 5.3 Frequency Decay

```
if frequency > base_frequency:
    decay = (frequency - base_frequency) * CAPACITY_DECAY_RATE
    frequency = max(base_frequency, frequency - max(1, int(decay)))
```

Extra trains added by the planner gradually return to depot.

---

## 6. Demand Forecasting (EMA Model)

The forecaster predicts demand 1-3 hours ahead using **Exponential Moving Average (EMA)** blended with the known time-of-day demand curve.

### 6.1 EMA Update

```
observed = (bus_load_factor + mrt_load_factor + station_crowding) / 3

EMA_new = ALPHA * observed + (1 - ALPHA) * EMA_prev
```

Where `ALPHA = 0.3`. This gives ~70% weight to historical trend and ~30% to the latest observation.

### 6.2 Forecast for Hour h+k

```
For each offset k in {1, 2, 3}:
    future_hour = (current_hour + k) mod 24

    if future_hour in NO_SERVICE_HOURS:
        forecast[k] = 0.0      (no service = no demand)
    else:
        base = D(future_hour)   (demand wave for that hour)
        predicted = 0.6 * base + 0.4 * EMA + weather_boost

        if k <= 2 and active_events:
            predicted *= event_multiplier

        forecast[k] = clamp(0.0, 1.2, predicted)
```

**Blend ratio:** 60% from the known daily pattern (structural), 40% from the observed trend (real-time adaptation).

### 6.3 Weather Boost on Forecast

| Weather | Boost |
|---------|-------|
| Light Rain | +0.03 |
| Heavy Rain | +0.08 |
| Thunderstorm | +0.12 |

### 6.4 Train Line Forecast

```
base = D(future_hour) * 0.85 + 0.05
predicted = 0.6 * base + 0.4 * EMA + weather_boost * 0.5

if disruption_level > 0.1:
    predicted *= (1 + disruption_level * 0.2)
```

### 6.5 Confidence Bounds

```
peak = max(forecast[1], forecast[2], forecast[3])

District:     [peak - 0.12, peak + 0.12]
Train line:   [peak - 0.10, peak + 0.10]
```

### 6.6 Forecast Alerts

- District alert: triggered when any `forecast[k] > 0.85`
- Train line alert: triggered when any `forecast[k] > 0.80`

---

## 7. Operating Cost Model

Cost is measured in **Cost Units (CU)** per hour.

```
Cost_hour = (bus_active * 8.0)           Active bus service
          + (train_active * 12.0)        Active train service
          + (idle_reserve * 3.0)         Standby reserve (operating hours only)
          + (crowding_penalties * 25.0)  Per district with crowding > 90%
          + (delay_penalties * 15.0)     Per train line with disruption > 30%
          + (escalations * 5.0)          Per escalation event
```

Where:
```
idle_reserve = (bus_max - bus_active) + (train_max - train_active)
               Only counted when bus_active > 0 (operating hours)
```

**Example at midnight (00:00):**
```
bus_active = 8,  train_active = 3  (15% of max)
idle_bus = 50 - 8 = 42,  idle_train = 20 - 3 = 17

Cost = (8 * 8) + (3 * 12) + (42 + 17) * 3 = 64 + 36 + 177 = 277 CU
```

**Example at morning peak (08:00):**
```
bus_active = 43,  train_active = 17  (85% of max)
idle_bus = 7,  idle_train = 3

Cost = (43 * 8) + (17 * 12) + (7 + 3) * 3 = 344 + 204 + 30 = 578 CU
       + potential crowding/delay penalties
```

---

## 8. Carbon Emissions Model

```
For each district:
    bus_emissions  = bus_capacity * bus_load_factor * BUS_EMISSIONS * 0.01
    traffic_emissions = road_traffic * TRAFFIC_EMISSIONS_FACTOR * 0.1

For each train line:
    train_emissions = frequency * line_load * MRT_EMISSIONS * 0.05

Total hourly emissions = sum(all bus + traffic + train emissions)
```

**Interpretation:** Bus and train emissions scale with both how many units are running and how loaded they are. Road traffic generates additional emissions from private vehicles.

---

## 9. KPI Scoring (Triple Score)

All scores range from 0 (worst) to 100 (best).

### 9.1 Liveability Score

```
Liveability = 100 - (
    30 * avg_station_crowding
  + 20 * max(0, avg_bus_load - 0.85) * 5
  + 20 * max(0, avg_mrt_load - 0.80) * 5
  + 15 * avg_traffic
  + 15 * max(0, avg_train_load - 0.80) * 3
)
```

| Component | Weight | What it Penalises |
|-----------|--------|-------------------|
| Station crowding | 30% | Crowded platforms reduce liveability |
| Bus overload | 20% | Only penalises load ABOVE 85% target |
| MRT overload | 20% | Only penalises load ABOVE 80% target |
| Road traffic | 15% | General congestion |
| Train overload | 15% | Only penalises load ABOVE 80% target |

### 9.2 Environment Score

```
Environment = 100 - (
    0.6 * avg_traffic * 100
  + 0.4 * (100 - avg_air_quality)
)
```

60% weight on traffic-driven emissions, 40% on air quality degradation.

### 9.3 Cost Efficiency Score

```
if cost_this_hour <= 0:
    cost_score = 100

else:
    cost_score = 100 - (cost_this_hour - 100) * (100 / 500)
    cost_score = clamp(0, 100)
```

| Cost (CU/hour) | Score |
|----------------|-------|
| 100 or less | 100 |
| 300 | 60 |
| 500 | 20 |
| 600+ | 0 |

This is a linear scale where 100 CU = perfect efficiency, 600 CU = zero efficiency.

---

## 10. Agent Decision Logic

### 10.1 Monitoring Agent

Generates alerts based on threshold crossings:

| Metric | Warning | Critical |
|--------|---------|----------|
| Station crowding | > 70% | > 90% |
| Bus load | - | > 85% |
| Road traffic | - | > 75% |
| Air quality | - | < 60 |
| Train load | - | > 80% |
| Train disruption | - | > 20% |
| Hourly cost | - | > 500 CU |

### 10.2 Capacity Planner Agent

Uses a **proactive + reactive** decision tree:

**District urgency score:**
```
urgency = 0
if station_crowding > 0.90:  urgency += 2.0
if bus_load > 0.85:          urgency += 1.0
if mrt_load > 0.80:          urgency += 1.0
if road_traffic > 0.75:      urgency += 0.5
if air_quality < 60:         urgency += 0.5
```

**Train urgency score:**
```
urgency = 0
if line_load > 0.80:          urgency += 2.0
if disruption_level > 0.30:   urgency += 1.5
if line_load > 0.60:          urgency += 0.5
```

**Decision rules:**

| Condition | Action | Formula for Extra Units |
|-----------|--------|-------------------------|
| Forecast peak > 85% AND current load <= 85% | DEPLOY_RESERVE (proactive) | `min(5, max(1, int((fc_peak - 0.85) * 15)))` |
| Bus load > 85% + road incident | REROUTE + DEPLOY_RESERVE | `min(8, max(1, int((load - 0.85) * 20)))` |
| Bus load > 85% + traffic > 80% | SHORT_TURN | (no extra units) |
| Bus load > 85% (standard) | DEPLOY_RESERVE | `min(10, max(1, int((load - 0.85) * 20)))` |
| Load < 40% + forecast < 40% | Hold reserves (cost saving) | 0 |
| Bus load 70-85% | HOLD_AT_TERMINAL | (headway regulation) |
| Station crowding > 90% | CROWD_MGMT | (crowd control) |
| Crowding > 95% AND load > 95% | ESCALATE_TO_OPERATOR | (human required) |
| Off-peak + crowding > 70% + forecast > 75% | TRAVEL_ADVISORY | (3-hour duration) |

**Train-specific:**

| Condition | Action | Formula |
|-----------|--------|---------|
| Forecast peak > 80% AND load <= 80% | ADD_TRAINS (proactive) | `min(2, max(1, int((fc_peak - 0.80) * 8)))` |
| Line load > 80% | ADD_TRAINS (reactive) | `min(3, max(1, int((load - 0.80) * 10)))` |
| Load 60-80% | HOLD_HEADWAY | (spacing control) |
| Disruption > 50% | ESCALATE_TO_OPERATOR | (human required) |

### 10.3 Policy Agent

Enforces operational constraints (rules applied in order):

| Rule | Condition | Action |
|------|-----------|--------|
| Cap bus units | bus_extra > BUS_MAX_EXTRA (10) | Clamp to 10 |
| Block deploy on gridlock | traffic > 80% AND deploying reserves | Convert to SHORT_TURN |
| Crowd mgmt gate | crowding <= 90% | Remove CROWD_MGMT |
| Peak advisory block | Peak hour (7-9, 17-19) | Block TRAVEL_ADVISORY |
| Advisory conditions | crowding <= 70% AND traffic <= 75% | Remove advisory |
| Cap train units | mrt_extra > MRT_MAX_EXTRA (3) | Clamp to 3 |

### 10.4 Coordinator Agent

Allocates limited global resources by **urgency priority**:

```
bus_available = bus_active - floor(bus_max * 0.20)     (reserve 20% buffer)
train_available = train_active - floor(train_max * 0.20)

Sort proposals by urgency (descending)

For each proposal:
    allocated = min(requested, remaining_available)
    remaining_available -= allocated
```

Higher-urgency districts/lines are served first. Once the pool is exhausted, lower-priority requests are denied.

### 10.5 Executor Agent

Applies approved actions with specific effects:

| Action | Effect on State |
|--------|----------------|
| CROWD_MGMT | `station_crowding *= 0.85` (15% reduction) |
| DEPLOY_RESERVE +N | `bus_capacity += N`, `bus_load *= 0.95` |
| SHORT_TURN | `bus_load *= 0.94`, `road_traffic *= 0.97` |
| HOLD_AT_TERMINAL | `bus_load *= 0.98` |
| REROUTE_AROUND_INCIDENT | `road_traffic *= 0.95` |
| TRAVEL_ADVISORY | `nudges_active = true`, timer = 3 hours |
| ADD_TRAINS +N | `frequency += N`, `line_load *= 0.95` |
| HOLD_HEADWAY | `line_load *= 0.98` |
| ESCALATE_TO_OPERATOR | Logged + `cost += 5.0 CU` penalty |

---

## 11. Capacity Decay & Sustainability

### 11.1 Capacity Decay

Added capacity (from DEPLOY_RESERVE) decays back to baseline each hour:

```
if bus_capacity > base_bus_capacity:
    decay = (bus_capacity - base_bus_capacity) * 0.05
    bus_capacity = max(base, bus_capacity - max(1, decay))
```

This models buses returning to depot after their extra deployment. At 5% decay rate, extra capacity halves in ~14 hours.

### 11.2 Sustainability Score

```
if hourly_emissions < 50 kg:
    sustainability += 0.1  (slowly improves)

if hourly_emissions > 150 kg:
    sustainability -= 0.2  (degrades faster)
```

Range: 0-100. Starts at 100. Rewards consistently low emissions.

---

## 12. Service Unit Scaling

The number of active service units follows a time-of-day profile:

| Hour | Scale | Bus Active (of 50) | Train Active (of 20) |
|------|-------|---------------------|----------------------|
| 00:00 | 15% | 8 | 3 |
| 01-05 | 0% | 0 (no service) | 0 (no service) |
| 06:00 | 40% | 20 | 8 |
| 07:00 | 65% | 33 | 13 |
| 08:00 | 85% | 43 | 17 |
| 09:00 | 80% | 40 | 16 |
| 10-11 | 50-55% | 25-28 | 10-11 |
| 12:00 | 55% | 28 | 11 |
| 13-14 | 50% | 25 | 10 |
| 15:00 | 55% | 28 | 11 |
| 16:00 | 60% | 30 | 12 |
| 17:00 | 80% | 40 | 16 |
| 18:00 | 85% | 43 | 17 |
| 19:00 | 70% | 35 | 14 |
| 20:00 | 45% | 23 | 9 |
| 21:00 | 35% | 18 | 7 |
| 22:00 | 25% | 13 | 5 |
| 23:00 | 18% | 9 | 4 |

---

## Summary: Data Flow per Simulation Step

```
1. Orchestrator sets service units for current hour (HOUR_SCALE)
2. Monitor observes all district + train metrics
3. Forecaster predicts demand +1h, +2h, +3h using EMA + demand curve
4. Planner proposes actions (proactive from forecast, reactive from current state)
5. Policy validates proposals (caps, blocks, constraints)
6. Coordinator allocates limited resources by urgency priority
7. Executor applies approved actions to city state
8. Environment step:
   a. Update weather (stochastic transitions)
   b. Trigger/expire random events
   c. Compute demand wave D(h)
   d. Process all districts (bus load, MRT load, crowding, traffic, air)
   e. Process all train lines (load, disruption, frequency)
   f. Calculate emissions
   g. Calculate operating cost
   h. Decay extra capacity toward baseline
   i. Update sustainability score
   j. Advance time (h → h+1)
9. Orchestrator recomputes service units and cost preview for new hour
10. Forecaster regenerates display forecast for new hour
11. KPI scores computed and returned to frontend
```
