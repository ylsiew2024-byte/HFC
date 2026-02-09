"""
KPI calculations and scoring for the MetroMind v2 city simulation.
Includes liveability, environment, and cost efficiency scores.
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
    """Compute liveability, environment, and cost scores (0-100, higher is better)."""
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

    # Cost efficiency score (v2): lower cost_this_hour = better score
    # Baseline expectation ~500 CU at peak, ~100 CU off-peak
    # Score 100 = very efficient, 0 = very expensive
    cost = city.cost_this_hour
    if cost <= 0:
        cost_score = 100.0
    else:
        # Normalise: cost of 600+ CU = score 0, cost of 100 CU = score 100
        cost_score = max(0, min(100, 100 - (cost - 100) * (100 / 500)))

    liveability = max(0, min(100, liveability))
    environment = max(0, min(100, environment))
    cost_score = max(0, min(100, cost_score))

    return {
        "liveability_score": round(liveability, 1),
        "environment_score": round(environment, 1),
        "cost_score": round(cost_score, 1),
    }
