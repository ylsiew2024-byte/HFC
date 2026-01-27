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

        observations = self.monitor.observe(city)
        proposals = self.planner.propose(city, observations)
        sanitized = self.policy.sanitize(proposals, observations)
        approved = self.coordinator.allocate(city, sanitized)
        step_actions = self.executor.execute(city, approved)

        self.env.step(city)

        metrics = snapshot_metrics(city)
        scores = score(city)

        city.history.append({
            "t": city.t,
            "hour": city.hour_of_day,
            "day": city.day_index,
            "scores": scores.copy(),
            "metrics": metrics.copy(),
        })

        return self._build_payload(city, metrics, scores, step_actions)

    def get_state(self, city: CityState) -> Dict[str, Any]:
        """Get current state without stepping."""
        metrics = snapshot_metrics(city)
        scores = score(city)
        recent_actions = city.action_log[-20:] if city.action_log else []
        return self._build_payload(city, metrics, scores, recent_actions)

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
                "bus_fleet_remaining": city.bus_fleet_capacity,
                "train_slots_remaining": city.train_slot_capacity,
            },
            "environment": {
                "carbon_emissions": round(city.carbon_emissions, 1),
                "hourly_emissions": round(city.hourly_emissions, 1),
                "sustainability_score": round(city.sustainability_score, 1),
            },
            "active_events": [e.to_dict() for e in city.active_events],
            "history_tail": city.history[-50:],
        }
