"""
Orchestrator - Single source of truth for simulation control.
"""
from typing import Dict, Any
from .models import CityState, DistrictState, TrainLineState, TRAIN_LINE_DEFS
from .env import MobilityEnvironment
from .kpi import snapshot_metrics, score
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

    return CityState(
        districts=districts,
        train_lines=train_lines,
        t=0, hour_of_day=0, day_index=1,
        action_log=[], history=[],
    )


def _is_no_service(hour: int) -> bool:
    return hour in NO_SERVICE_HOURS


class Orchestrator:
    """Main orchestration logic."""

    def __init__(self):
        self.env = MobilityEnvironment()
        self.monitor = MonitoringAgent()
        self.planner = CapacityPlannerAgent()
        self.policy = PolicyAgent()
        self.coordinator = CoordinatorAgent()
        self.executor = ExecutionAgent()

    def step(self, city: CityState) -> Dict[str, Any]:
        """Run one full simulation step."""
        city.reset_capacities()

        # Check the hour BEFORE env.step advances time
        current_hour = city.hour_of_day
        no_service = _is_no_service(current_hour)

        # Compute baseline active service units for this hour
        scale = HOUR_SCALE.get(current_hour, 0.5)
        city.bus_service_units_active = round(city.bus_service_units_max * scale)
        city.train_service_units_active = round(city.train_service_units_max * scale)

        # Apply no-service state
        if no_service:
            city.bus_service_units_active = 0
            city.train_service_units_active = 0
            self._apply_no_service(city)

        observations = self.monitor.observe(city)
        agent_trace = {
            "hour": current_hour,
            "no_service": no_service,
            "monitoring": {"alerts": observations.get("alerts", [])},
        }

        if no_service:
            # Agents in standby - no proposals, no allocation, no execution
            agent_trace["planner"] = {"bus_proposals": [], "train_proposals": [], "note": "Standby: out of operating hours (01:00-05:00)"}
            agent_trace["policy"] = {"adjustments": [], "blocked": [], "note": "Standby"}
            agent_trace["coordinator"] = {"allocations": [], "remaining_capacity": {"bus_service_units": 0, "train_service_units": 0}, "note": "Standby"}
            agent_trace["executor"] = {"applied": ["OUT_OF_SERVICE"], "note": "No bus/train service"}

            # Log out-of-service
            oos_event = {
                "t": city.t,
                "hour": current_hour,
                "type": "system",
                "district": "ALL",
                "actions": ["OUT_OF_SERVICE"],
                "urgency": 0,
            }
            city.action_log.append(oos_event)
            step_actions = [oos_event]
        else:
            proposals = self.planner.propose(city, observations)
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

        # Environment always steps (weather, demand, etc.) — this advances hour_of_day
        env_summary = self.env.step(city)
        agent_trace["env"] = {
            "events_triggered": [e.get("name", str(e)) for e in env_summary.get("events_triggered", [])],
            "emissions": round(env_summary.get("emissions", 0), 1),
        }
        # Update trace hour to match the displayed hour (after env.step)
        agent_trace["hour"] = city.hour_of_day
        agent_trace["no_service"] = _is_no_service(city.hour_of_day)

        # Recompute service units for the NEW hour (for display accuracy)
        new_hour = city.hour_of_day
        new_scale = HOUR_SCALE.get(new_hour, 0.5)
        if _is_no_service(new_hour):
            city.bus_service_units_active = 0
            city.train_service_units_active = 0
        else:
            city.bus_service_units_active = round(city.bus_service_units_max * new_scale)
            city.train_service_units_active = round(city.train_service_units_max * new_scale)

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
        return payload

    def get_state(self, city: CityState) -> Dict[str, Any]:
        """Get current state without stepping."""
        metrics = snapshot_metrics(city)
        scores = score(city)
        recent_actions = city.action_log[-20:] if city.action_log else []
        payload = self._build_payload(city, metrics, scores, recent_actions)
        payload["no_service"] = _is_no_service(city.hour_of_day)
        return payload

    def _apply_no_service(self, city: CityState):
        """Set bus freq and train freq to 0 during no-service hours."""
        for d in city.districts:
            # Loads decay toward 0
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
