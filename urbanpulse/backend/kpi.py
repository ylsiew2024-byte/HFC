"""
KPI calculations and scoring for the city simulation.
"""
from typing import Dict, Any
from .models import CityState, BUS_TARGET_LF, MRT_TARGET_LF


def snapshot_metrics(city: CityState) -> Dict[str, float]:
    """
    Compute aggregate metrics across all districts.
    Returns dict with avg_station, avg_bus_load, avg_mrt_load, avg_traffic, avg_air.
    """
    n = len(city.districts)
    if n == 0:
        return {
            "avg_station": 0.0,
            "avg_bus_load": 0.0,
            "avg_mrt_load": 0.0,
            "avg_traffic": 0.0,
            "avg_air": 0.0,
        }

    total_station = sum(d.station_crowding for d in city.districts)
    total_bus = sum(d.bus_load_factor for d in city.districts)
    total_mrt = sum(d.mrt_load_factor for d in city.districts)
    total_traffic = sum(d.road_traffic for d in city.districts)
    total_air = sum(d.air_quality for d in city.districts)

    return {
        "avg_station": round(total_station / n, 3),
        "avg_bus_load": round(total_bus / n, 3),
        "avg_mrt_load": round(total_mrt / n, 3),
        "avg_traffic": round(total_traffic / n, 3),
        "avg_air": round(total_air / n, 1),
    }


def score(city: CityState) -> Dict[str, float]:
    """
    Compute liveability and environment scores (0-100, higher is better).
    """
    snap = snapshot_metrics(city)

    # Liveability score
    # Penalizes: station crowding, bus overload, mrt overload, traffic
    # Values are 0-1, weights sum to 100 when all at max
    liveability = 100 - (
        35 * snap["avg_station"] +
        25 * max(0, snap["avg_bus_load"] - BUS_TARGET_LF) * 5 +  # Scale overload penalty
        25 * max(0, snap["avg_mrt_load"] - MRT_TARGET_LF) * 5 +  # Scale overload penalty
        15 * snap["avg_traffic"]
    )

    # Environment score
    # Penalizes: traffic (emissions proxy) and poor air quality
    environment = 100 - (
        0.6 * snap["avg_traffic"] * 100 +
        0.4 * (100 - snap["avg_air"])
    )

    # Clamp to [0, 100]
    liveability = max(0, min(100, liveability))
    environment = max(0, min(100, environment))

    return {
        "liveability_score": round(liveability, 1),
        "environment_score": round(environment, 1),
    }
