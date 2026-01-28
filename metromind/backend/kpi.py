"""
KPI calculations and scoring for the city simulation.
"""
from typing import Dict, Any
from .models import CityState, BUS_TARGET_LF, MRT_TARGET_LF


def snapshot_metrics(city: CityState) -> Dict[str, float]:
    """Compute aggregate metrics across all districts."""
    n = len(city.districts)
    if n == 0:
        return {
            "avg_station": 0.0, "avg_bus_load": 0.0,
            "avg_mrt_load": 0.0, "avg_traffic": 0.0, "avg_air": 0.0,
        }

    return {
        "avg_station": round(sum(d.station_crowding for d in city.districts) / n, 3),
        "avg_bus_load": round(sum(d.bus_load_factor for d in city.districts) / n, 3),
        "avg_mrt_load": round(sum(d.mrt_load_factor for d in city.districts) / n, 3),
        "avg_traffic": round(sum(d.road_traffic for d in city.districts) / n, 3),
        "avg_air": round(sum(d.air_quality for d in city.districts) / n, 1),
    }


def score(city: CityState) -> Dict[str, float]:
    """Compute liveability and environment scores (0-100, higher is better)."""
    snap = snapshot_metrics(city)

    # Also factor in train line loads
    train_load_avg = 0.0
    if city.train_lines:
        train_load_avg = sum(l.line_load for l in city.train_lines.values()) / len(city.train_lines)

    liveability = 100 - (
        30 * snap["avg_station"] +
        20 * max(0, snap["avg_bus_load"] - BUS_TARGET_LF) * 5 +
        20 * max(0, snap["avg_mrt_load"] - MRT_TARGET_LF) * 5 +
        15 * snap["avg_traffic"] +
        15 * max(0, train_load_avg - MRT_TARGET_LF) * 3
    )

    environment = 100 - (
        0.6 * snap["avg_traffic"] * 100 +
        0.4 * (100 - snap["avg_air"])
    )

    liveability = max(0, min(100, liveability))
    environment = max(0, min(100, environment))

    return {
        "liveability_score": round(liveability, 1),
        "environment_score": round(environment, 1),
    }
