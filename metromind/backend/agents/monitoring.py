"""
MonitoringAgent v2 — Observes and reports city state including cost metrics.
"""
from typing import Dict, Any, List
from ..models import CityState, BUS_TARGET_LF, MRT_TARGET_LF, CROWDING_CRITICAL


class MonitoringAgent:
    """Observes city state and produces observation reports."""

    def observe(self, city: CityState) -> Dict[str, Any]:
        observations = {
            "t": city.t,
            "hour": city.hour_of_day,
            "bus_service_units_active": city.bus_service_units_active,
            "train_service_units_active": city.train_service_units_active,
            "weather": city.weather.to_dict(),
            "cost_this_hour": city.cost_this_hour,
            "cost_today": round(city.cost_today, 1),
            "districts": {},
            "train_lines": {},
            "alerts": self._generate_alerts(city),
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

    def _generate_alerts(self, city: CityState) -> List[str]:
        """Generate human-readable alerts for the current state."""
        alerts = []
        for d in city.districts:
            if d.station_crowding > CROWDING_CRITICAL:
                alerts.append(f"CRITICAL: {d.name} station crowding at {d.station_crowding*100:.0f}%")
            elif d.station_crowding > 0.7:
                alerts.append(f"WARNING: {d.name} station crowding at {d.station_crowding*100:.0f}%")
            if d.bus_load_factor > BUS_TARGET_LF:
                alerts.append(f"Bus overload in {d.name}: {d.bus_load_factor*100:.0f}% load")
            if d.road_traffic > 0.75:
                alerts.append(f"High traffic in {d.name}: {d.road_traffic*100:.0f}%")
            if d.air_quality < 60:
                alerts.append(f"Poor air quality in {d.name}: {d.air_quality:.0f}")
        for lid, line in city.train_lines.items():
            if line.line_load > MRT_TARGET_LF:
                alerts.append(f"{line.line_name} ({lid}) overloaded: {line.line_load*100:.0f}%")
            if line.disruption_level > 0.2:
                alerts.append(f"{line.line_name} ({lid}) disruption: {line.disruption_level*100:.0f}%")
        w = city.weather
        if w.condition in ("Heavy Rain", "Thunderstorm"):
            alerts.append(f"Severe weather: {w.condition} ({w.intensity*100:.0f}% intensity)")
        elif w.condition == "Haze":
            alerts.append(f"Haze alert: intensity {w.intensity*100:.0f}%")

        # Cost alert
        if city.cost_this_hour > 500:
            alerts.append(f"High operating cost: {city.cost_this_hour:.0f} CU this hour")

        # Road incident alerts
        for event in city.active_events:
            if event.road_incident:
                alerts.append(f"Road incident active in {', '.join(event.districts)}")

        return alerts
