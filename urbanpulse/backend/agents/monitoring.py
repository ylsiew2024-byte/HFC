"""
MonitoringAgent - Observes and reports city state.
"""
from typing import Dict, Any
from ..models import CityState


class MonitoringAgent:
    """Observes city state and produces observation reports."""

    def observe(self, city: CityState) -> Dict[str, Any]:
        observations = {
            "t": city.t,
            "hour": city.hour_of_day,
            "bus_fleet_available": city.bus_fleet_capacity,
            "train_slots_available": city.train_slot_capacity,
            "weather": city.weather.to_dict(),
            "districts": {},
            "train_lines": {},
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

        for line_id, line in city.train_lines.items():
            observations["train_lines"][line_id] = {
                "line_load": line.line_load,
                "frequency": line.frequency,
                "disruption_level": line.disruption_level,
            }

        return observations
