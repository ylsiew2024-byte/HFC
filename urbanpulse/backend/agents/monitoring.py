"""
MonitoringAgent - Observes and reports city state.
"""
from typing import Dict, Any
from ..models import CityState


class MonitoringAgent:
    """Observes city state and produces observation reports."""

    def observe(self, city: CityState) -> Dict[str, Any]:
        """
        Observe the current city state.
        Returns a dict with observations for each district.
        """
        observations = {
            "t": city.t,
            "bus_budget_available": city.bus_budget,
            "mrt_budget_available": city.mrt_budget,
            "districts": {}
        }

        for district in city.districts:
            observations["districts"][district.name] = {
                "bus_load_factor": district.bus_load_factor,
                "mrt_load_factor": district.mrt_load_factor,
                "station_crowding": district.station_crowding,
                "road_traffic": district.road_traffic,
                "air_quality": district.air_quality,
                "bus_capacity": district.bus_capacity,
                "mrt_capacity": district.mrt_capacity,
                "nudges_active": district.nudges_active,
            }

        return observations
