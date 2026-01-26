"""
Data models for UrbanPulse city simulation.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any


# Constants
BUS_TARGET_LF = 0.85
MRT_TARGET_LF = 0.80
CROWDING_CRITICAL = 0.9
TRAFFIC_BUS_ADD_LIMIT = 0.8
BUS_MAX_EXTRA = 10
MRT_MAX_EXTRA = 3


@dataclass
class DistrictState:
    """State of a single district."""
    name: str
    population: int
    bus_capacity: int  # buses per hour
    mrt_capacity: int  # trains per hour
    bus_load_factor: float  # 0-1, ratio of demand to capacity
    mrt_load_factor: float  # 0-1
    station_crowding: float  # 0-1, crowding level at stations
    road_traffic: float  # 0-1, traffic congestion level
    air_quality: float  # 0-100, higher is better
    nudges_active: bool = False
    nudge_timer: int = 0  # steps remaining for nudge effect

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "population": self.population,
            "bus_capacity": self.bus_capacity,
            "mrt_capacity": self.mrt_capacity,
            "bus_load_factor": round(self.bus_load_factor, 3),
            "mrt_load_factor": round(self.mrt_load_factor, 3),
            "station_crowding": round(self.station_crowding, 3),
            "road_traffic": round(self.road_traffic, 3),
            "air_quality": round(self.air_quality, 1),
            "nudges_active": self.nudges_active,
        }


@dataclass
class CityState:
    """State of the entire city."""
    districts: List[DistrictState]
    t: int = 0  # current time step
    bus_budget: int = 40  # extra buses available globally per step
    mrt_budget: int = 12  # extra trains available globally per step
    action_log: List[Dict[str, Any]] = field(default_factory=list)
    history: List[Dict[str, Any]] = field(default_factory=list)

    # Track original budgets for reset
    _initial_bus_budget: int = 40
    _initial_mrt_budget: int = 12

    def to_dict(self) -> Dict[str, Any]:
        return {
            "t": self.t,
            "bus_budget": self.bus_budget,
            "mrt_budget": self.mrt_budget,
            "districts": [d.to_dict() for d in self.districts],
        }

    def reset_budgets(self):
        """Reset budgets at the start of each step."""
        self.bus_budget = self._initial_bus_budget
        self.mrt_budget = self._initial_mrt_budget
