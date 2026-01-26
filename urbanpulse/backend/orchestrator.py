"""
Orchestrator - Single source of truth for simulation control.
"""
from typing import Dict, Any, List
from .models import CityState, DistrictState
from .env import MobilityEnvironment
from .kpi import snapshot_metrics, score
from .agents import (
    MonitoringAgent,
    CapacityPlannerAgent,
    PolicyAgent,
    CoordinatorAgent,
    ExecutionAgent,
)


def make_city() -> CityState:
    """
    Create initial city state with Singapore-inspired districts.
    Starts at midnight (Hour 0) with appropriately low activity levels.
    """
    # At midnight: transit is winding down, very low loads
    districts = [
        DistrictState(
            name="Central",  # CBD/Marina Bay area
            population=500000,
            bus_capacity=120,
            mrt_capacity=40,
            bus_load_factor=0.08,  # Very low at midnight
            mrt_load_factor=0.06,
            station_crowding=0.05,
            road_traffic=0.12,  # Some taxis, night traffic
            air_quality=85,  # Good air at night
        ),
        DistrictState(
            name="North",  # Woodlands/Yishun area
            population=350000,
            bus_capacity=80,
            mrt_capacity=25,
            bus_load_factor=0.05,
            mrt_load_factor=0.04,
            station_crowding=0.03,
            road_traffic=0.08,
            air_quality=88,
        ),
        DistrictState(
            name="South",  # Harbourfront/Sentosa area
            population=400000,
            bus_capacity=90,
            mrt_capacity=30,
            bus_load_factor=0.07,
            mrt_load_factor=0.05,
            station_crowding=0.04,
            road_traffic=0.10,
            air_quality=86,
        ),
        DistrictState(
            name="East",  # Tampines/Changi area
            population=380000,
            bus_capacity=85,
            mrt_capacity=28,
            bus_load_factor=0.06,
            mrt_load_factor=0.05,
            station_crowding=0.04,
            road_traffic=0.09,
            air_quality=87,
        ),
        DistrictState(
            name="West",  # Jurong area
            population=320000,
            bus_capacity=75,
            mrt_capacity=22,
            bus_load_factor=0.05,
            mrt_load_factor=0.04,
            station_crowding=0.03,
            road_traffic=0.08,
            air_quality=86,
        ),
    ]

    return CityState(
        districts=districts,
        t=0,
        bus_budget=40,
        mrt_budget=12,
        action_log=[],
        history=[],
    )


class Orchestrator:
    """Main orchestration logic for the simulation."""

    def __init__(self):
        self.env = MobilityEnvironment()
        self.monitor = MonitoringAgent()
        self.planner = CapacityPlannerAgent()
        self.policy = PolicyAgent()
        self.coordinator = CoordinatorAgent()
        self.executor = ExecutionAgent()

    def step(self, city: CityState) -> Dict[str, Any]:
        """
        Run one full simulation step.
        Returns payload with current state, metrics, scores, and actions.
        """
        # Reset budgets at start of each step
        city.reset_budgets()

        # 1. Observe
        observations = self.monitor.observe(city)

        # 2. Propose (planner generates proposals)
        proposals = self.planner.propose(city, observations)

        # 3. Policy sanitization
        sanitized_proposals = self.policy.sanitize(proposals, observations)

        # 4. Coordination allocation
        approved_proposals = self.coordinator.allocate(city, sanitized_proposals)

        # 5. Execute approved actions
        step_actions = self.executor.execute(city, approved_proposals)

        # 6. Environment step (advance simulation)
        self.env.step(city)

        # 7. Compute metrics and scores
        metrics = snapshot_metrics(city)
        scores = score(city)

        # Record history snapshot
        history_entry = {
            "t": city.t,
            "scores": scores.copy(),
            "metrics": metrics.copy(),
        }
        city.history.append(history_entry)

        # 8. Build return payload
        payload = {
            "t": city.t,
            "scores": scores,
            "metrics": metrics,
            "districts": {d.name: d.to_dict() for d in city.districts},
            "actions": step_actions,
            "budgets": {
                "bus_remaining": city.bus_budget,
                "mrt_remaining": city.mrt_budget,
            },
            "history_tail": city.history[-50:],  # Last 50 snapshots
        }

        return payload

    def get_state(self, city: CityState) -> Dict[str, Any]:
        """Get current state without stepping."""
        metrics = snapshot_metrics(city)
        scores = score(city)

        return {
            "t": city.t,
            "scores": scores,
            "metrics": metrics,
            "districts": {d.name: d.to_dict() for d in city.districts},
            "actions": city.action_log[-20:] if city.action_log else [],
            "budgets": {
                "bus_remaining": city.bus_budget,
                "mrt_remaining": city.mrt_budget,
            },
            "history_tail": city.history[-50:],
        }
