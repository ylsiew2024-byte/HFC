"""
Orchestrator v2 — Single source of truth for simulation control.
Integrates demand forecasting, cost tracking, and operator escalations.
"""
from typing import Dict, Any
from .models import (
    CityState, DistrictState, TrainLineState, TRAIN_LINE_DEFS,
    COST_BUS_ACTIVE, COST_TRAIN_ACTIVE, COST_RESERVE_IDLE,
    COST_CROWDING_PENALTY, COST_DELAY_PENALTY, CROWDING_CRITICAL,
)
from .env import MobilityEnvironment
from .kpi import snapshot_metrics, score
from .forecast import DemandForecaster
from .agents import (
    MonitoringAgent, CapacityPlannerAgent, PolicyAgent,
    CoordinatorAgent, ExecutionAgent,
)

# Hours where bus and train service is suspended
NO_SERVICE_HOURS = {1, 2, 3, 4, 5}

# Dynamic service unit scaling by hour (fraction of max units to deploy)
HOUR_SCALE = {
    0: 0.15, 1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0, 5: 0.0,
    6: 0.40, 7: 0.65, 8: 0.85, 9: 0.80, 10: 0.55, 11: 0.50,
    12: 0.55, 13: 0.50, 14: 0.50, 15: 0.55, 16: 0.60,
    17: 0.80, 18: 0.85, 19: 0.70, 20: 0.45, 21: 0.35,
    22: 0.25, 23: 0.18,
}


def make_city() -> CityState:
    """Create initial city state at midnight."""
    districts = [
        DistrictState(
            name="Central", population=500000,
            bus_capacity=120, mrt_capacity=40,
            base_bus_capacity=120, base_mrt_capacity=40,
            bus_load_factor=0.08, mrt_load_factor=0.06,
            station_crowding=0.05, road_traffic=0.12, air_quality=85,
        ),
        DistrictState(
            name="North", population=350000,
            bus_capacity=80, mrt_capacity=25,
            base_bus_capacity=80, base_mrt_capacity=25,
            bus_load_factor=0.05, mrt_load_factor=0.04,
            station_crowding=0.03, road_traffic=0.08, air_quality=88,
        ),
        DistrictState(
            name="East", population=380000,
            bus_capacity=85, mrt_capacity=28,
            base_bus_capacity=85, base_mrt_capacity=28,
            bus_load_factor=0.06, mrt_load_factor=0.05,
            station_crowding=0.04, road_traffic=0.09, air_quality=87,
        ),
        DistrictState(
            name="West", population=320000,
            bus_capacity=75, mrt_capacity=22,
            base_bus_capacity=75, base_mrt_capacity=22,
            bus_load_factor=0.05, mrt_load_factor=0.04,
            station_crowding=0.03, road_traffic=0.08, air_quality=86,
        ),
    ]

    # Create train lines
    train_lines = {}
    for line_id, defn in TRAIN_LINE_DEFS.items():
        train_lines[line_id] = TrainLineState(
            line_id=line_id,
            line_name=defn["name"],
            color=defn["color"],
            line_load=defn["base_load"],
            frequency=defn["base_freq"],
            base_frequency=defn["base_freq"],
        )

    # Compute initial service units and cost for hour 0
    initial_scale = HOUR_SCALE.get(0, 0.15)
    bus_active = round(50 * initial_scale)    # 50 = bus_service_units_max
    train_active = round(20 * initial_scale)  # 20 = train_service_units_max

    # Initial cost: active units + idle reserve
    idle_bus = max(0, 50 - bus_active)
    idle_train = max(0, 20 - train_active)
    initial_cost = (
        bus_active * COST_BUS_ACTIVE
        + train_active * COST_TRAIN_ACTIVE
        + (idle_bus + idle_train) * COST_RESERVE_IDLE
    )

    return CityState(
        districts=districts,
        train_lines=train_lines,
        t=0, hour_of_day=0, day_index=1,
        action_log=[], history=[],
        bus_service_units_active=bus_active,
        train_service_units_active=train_active,
        cost_this_hour=round(initial_cost, 1),
    )


def _is_no_service(hour: int) -> bool:
    return hour in NO_SERVICE_HOURS


class Orchestrator:
    """Main orchestration logic with forecast and cost integration."""

    def __init__(self):
        self.env = MobilityEnvironment()
        self.monitor = MonitoringAgent()
        self.planner = CapacityPlannerAgent()
        self.policy = PolicyAgent()
        self.coordinator = CoordinatorAgent()
        self.executor = ExecutionAgent()
        self.forecaster = DemandForecaster()

    def step(self, city: CityState) -> Dict[str, Any]:
        """Run one full simulation step."""
        city.reset_capacities()

        current_hour = city.hour_of_day
        no_service = _is_no_service(current_hour)

        scale = HOUR_SCALE.get(current_hour, 0.5)
        city.bus_service_units_active = round(city.bus_service_units_max * scale)
        city.train_service_units_active = round(city.train_service_units_max * scale)

        if no_service:
            city.bus_service_units_active = 0
            city.train_service_units_active = 0
            self._apply_no_service(city)

        observations = self.monitor.observe(city)

        # Generate demand forecast for planner (based on current hour before step)
        forecast_data = self.forecaster.forecast(city)

        agent_trace = {
            "hour": current_hour,
            "no_service": no_service,
            "monitoring": {"alerts": observations.get("alerts", [])},
        }

        if no_service:
            agent_trace["planner"] = {
                "bus_proposals": [], "train_proposals": [],
                "note": "Standby: out of operating hours (01:00-05:00)"
            }
            agent_trace["policy"] = {"adjustments": [], "blocked": [], "note": "Standby"}
            agent_trace["coordinator"] = {
                "allocations": [],
                "remaining_capacity": {"bus_service_units": 0, "train_service_units": 0},
                "note": "Standby"
            }
            agent_trace["executor"] = {
                "applied": ["OUT_OF_SERVICE"],
                "note": "No bus/train service"
            }

            oos_event = {
                "t": city.t, "hour": current_hour,
                "type": "system", "district": "ALL",
                "actions": ["OUT_OF_SERVICE"], "urgency": 0,
            }
            city.action_log.append(oos_event)
            step_actions = [oos_event]
        else:
            # Pass forecast to planner (v2)
            proposals = self.planner.propose(city, observations, forecast_data)
            agent_trace["planner"] = {
                "bus_proposals": proposals["district_proposals"],
                "train_proposals": proposals["train_proposals"],
                "reasoning": proposals.get("reasoning", []),
            }

            sanitized = self.policy.sanitize(proposals, observations)
            policy_trace = sanitized.pop("_trace", {"adjustments": [], "blocked": []})
            agent_trace["policy"] = policy_trace

            approved = self.coordinator.allocate(city, sanitized)
            coord_trace = approved.pop("_trace", {"allocations": [], "remaining_capacity": {}})
            agent_trace["coordinator"] = coord_trace

            step_actions = self.executor.execute(city, approved)
            agent_trace["executor"] = {
                "applied": [a["actions"] for a in step_actions] if step_actions else ["No actions needed"],
            }

            # Record escalations from planner
            escalations = proposals.get("escalations", [])
            if escalations:
                agent_trace["escalations"] = escalations

        # Environment always steps — this advances hour_of_day
        env_summary = self.env.step(city)
        agent_trace["env"] = {
            "events_triggered": [e.get("name", str(e)) for e in env_summary.get("events_triggered", [])],
            "emissions": round(env_summary.get("emissions", 0), 1),
            "cost_this_hour": round(env_summary.get("cost_this_hour", 0), 1),
        }
        agent_trace["hour"] = city.hour_of_day
        agent_trace["no_service"] = _is_no_service(city.hour_of_day)

        # Recompute service units for the NEW hour
        new_hour = city.hour_of_day
        new_scale = HOUR_SCALE.get(new_hour, 0.5)
        if _is_no_service(new_hour):
            city.bus_service_units_active = 0
            city.train_service_units_active = 0
            city.cost_this_hour = 0  # no operating cost during no-service hours
        else:
            city.bus_service_units_active = round(city.bus_service_units_max * new_scale)
            city.train_service_units_active = round(city.train_service_units_max * new_scale)
            # Restore train frequency after no-service hours
            for line in city.train_lines.values():
                if line.frequency < line.base_frequency:
                    line.frequency = line.base_frequency
            # Recalculate cost_this_hour to reflect the NEW hour's service level
            city.cost_this_hour = self._preview_hourly_cost(city)

        # Regenerate forecast for display (based on NEW hour after step)
        display_forecast = self.forecaster.forecast(city)

        metrics = snapshot_metrics(city)
        scores = score(city)

        city.history.append({
            "t": city.t,
            "hour": city.hour_of_day,
            "day": city.day_index,
            "scores": scores.copy(),
            "metrics": metrics.copy(),
        })

        payload = self._build_payload(city, metrics, scores, step_actions)
        payload["agent_trace"] = agent_trace
        # v2: include forecast and cost in payload
        payload["forecast"] = display_forecast
        payload["cost"] = {
            "cost_this_hour": round(city.cost_this_hour, 1),
            "cost_today": round(city.cost_today, 1),
            "cost_history": city.cost_history[-24:],
        }
        payload["operator_escalations"] = city.operator_escalations[-10:]
        return payload

    def get_state(self, city: CityState) -> Dict[str, Any]:
        """Get current state without stepping."""
        metrics = snapshot_metrics(city)
        scores = score(city)
        recent_actions = city.action_log[-20:] if city.action_log else []
        payload = self._build_payload(city, metrics, scores, recent_actions)
        payload["no_service"] = _is_no_service(city.hour_of_day)
        payload["cost"] = {
            "cost_this_hour": round(city.cost_this_hour, 1),
            "cost_today": round(city.cost_today, 1),
            "cost_history": city.cost_history[-24:],
        }
        payload["operator_escalations"] = city.operator_escalations[-10:]
        return payload

    def _preview_hourly_cost(self, city: CityState) -> float:
        """Calculate expected cost for the current hour based on active service units."""
        cost = 0.0
        cost += city.bus_service_units_active * COST_BUS_ACTIVE
        cost += city.train_service_units_active * COST_TRAIN_ACTIVE
        if city.bus_service_units_active > 0:
            idle_bus = max(0, city.bus_service_units_max - city.bus_service_units_active)
            idle_train = max(0, city.train_service_units_max - city.train_service_units_active)
            cost += (idle_bus + idle_train) * COST_RESERVE_IDLE
        for d in city.districts:
            if d.station_crowding > CROWDING_CRITICAL:
                cost += COST_CROWDING_PENALTY
        for line in city.train_lines.values():
            if line.disruption_level > 0.3:
                cost += COST_DELAY_PENALTY
        return round(cost, 1)

    def _apply_no_service(self, city: CityState):
        """Set bus freq and train freq to 0 during no-service hours."""
        for d in city.districts:
            d.bus_load_factor *= 0.3
            d.mrt_load_factor *= 0.3
            d.station_crowding *= 0.4
        for line in city.train_lines.values():
            line.frequency = 0
            line.line_load *= 0.3

    def _build_payload(self, city: CityState, metrics: dict, scores: dict,
                       actions: list) -> Dict[str, Any]:
        return {
            "time": {
                "t": city.t,
                "hour": city.hour_of_day,
                "day": city.day_index,
            },
            "scores": scores,
            "metrics": metrics,
            "weather": city.weather.to_dict(),
            "districts": {d.name: d.to_dict() for d in city.districts},
            "train_lines": {lid: l.to_dict() for lid, l in city.train_lines.items()},
            "actions": actions,
            "capacities": {
                "bus_service_units_active": city.bus_service_units_active,
                "bus_service_units_max": city.bus_service_units_max,
                "train_service_units_active": city.train_service_units_active,
                "train_service_units_max": city.train_service_units_max,
            },
            "environment": {
                "carbon_emissions": round(city.carbon_emissions, 1),
                "hourly_emissions": round(city.hourly_emissions, 1),
                "sustainability_score": round(city.sustainability_score, 1),
            },
            "active_events": [e.to_dict() for e in city.active_events],
            "history_tail": city.history[-50:],
            "no_service": _is_no_service(city.hour_of_day),
        }
