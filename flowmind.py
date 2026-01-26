from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Tuple
import random
import math
####

# -----------------------------
# Singapore-specific assumptions (prototype)
# -----------------------------

# Bus assumptions
BUS_CAPACITY = 80
BUS_TARGET_LF = 0.85
BUS_BASE_FREQ = 12           # buses/hour (every 5 min)
BUS_MAX_EXTRA = 10
TRAFFIC_BUS_ADD_LIMIT = 0.80 # if roads too jammed, don't add buses

# MRT assumptions
TRAIN_CAPACITY = 1200
MRT_TARGET_LF = 0.85
MRT_BASE_FREQ = 24           # trains/hour (~2.5 min)
MRT_MAX_EXTRA = 6            # signalling/headway constraints (prototype cap)

# Crowd management
CROWDING_CRITICAL = 0.80     # if stations are dangerously packed


# -----------------------------
# Data models
# -----------------------------

@dataclass
class DistrictState:
    name: str
    road_traffic: float      # 0.0 -> 1.0
    bus_load: float          # 0.0 -> 1.0
    mrt_load: float          # 0.0 -> 1.0
    station_crowding: float  # 0.0 -> 1.0
    air_quality: float       # 0.0 -> 100.0

    bus_freq: float = BUS_BASE_FREQ
    mrt_freq: float = MRT_BASE_FREQ

    def clamp(self) -> None:
        self.road_traffic = min(max(self.road_traffic, 0.0), 1.0)
        self.bus_load = min(max(self.bus_load, 0.0), 1.0)
        self.mrt_load = min(max(self.mrt_load, 0.0), 1.0)
        self.station_crowding = min(max(self.station_crowding, 0.0), 1.0)
        self.air_quality = min(max(self.air_quality, 0.0), 100.0)
        self.bus_freq = max(0.0, self.bus_freq)
        self.mrt_freq = max(0.0, self.mrt_freq)


@dataclass
class CityState:
    districts: Dict[str, DistrictState]
    t: int = 0
    history: List[Dict[str, float]] = field(default_factory=list)

    def snapshot_metrics(self) -> Dict[str, float]:
        n = len(self.districts)
        return {
            "t": self.t,
            "avg_traffic": sum(d.road_traffic for d in self.districts.values()) / n,
            "avg_bus_load": sum(d.bus_load for d in self.districts.values()) / n,
            "avg_mrt_load": sum(d.mrt_load for d in self.districts.values()) / n,
            "avg_station": sum(d.station_crowding for d in self.districts.values()) / n,
            "avg_air": sum(d.air_quality for d in self.districts.values()) / n,
            "avg_bus_freq": sum(d.bus_freq for d in self.districts.values()) / n,
            "avg_mrt_freq": sum(d.mrt_freq for d in self.districts.values()) / n,
        }


# -----------------------------
# Environment (mobility dynamics)
# -----------------------------

class MobilityEnvironment:
    """
    Simple mobility dynamics:
    - Demand waves change loads
    - Higher bus_freq reduces bus_load
    - Higher mrt_freq reduces mrt_load
    - Station crowding depends on bus+mrt loads
    """
    def step(self, city: CityState) -> None:
        for d in city.districts.values():
            demand_wave = random.uniform(-0.03, 0.07)

            # Road traffic
            d.road_traffic += demand_wave + random.uniform(-0.02, 0.05)

            # Bus load dynamics (more frequency helps; high traffic hurts buses)
            d.bus_load += (
                0.06 * d.road_traffic
                - 0.03 * (d.bus_freq - BUS_BASE_FREQ)
                + demand_wave
                + random.uniform(-0.02, 0.02)
            )

            # MRT load dynamics (more frequency helps; bus overload can spill into MRT)
            d.mrt_load += (
                0.04 * d.bus_load
                - 0.02 * (d.mrt_freq - MRT_BASE_FREQ)
                + demand_wave
                + random.uniform(-0.02, 0.02)
            )

            # Station crowding depends on both bus and MRT loads
            avg_pt = (d.bus_load + d.mrt_load) / 2
            d.station_crowding += 0.35 * avg_pt - 0.15 + random.uniform(-0.03, 0.03)

            # Air quality proxy worsens with idling traffic
            d.air_quality += -20 * d.road_traffic + random.uniform(-1.5, 1.5)

            d.clamp()

        city.t += 1
        city.history.append(city.snapshot_metrics())


# -----------------------------
# Agents
# -----------------------------

class MonitoringAgent:
    def observe(self, city: CityState) -> Dict[str, DistrictState]:
        return city.districts


class CapacityPlannerAgent:
    """
    Computes how many extra buses/hour and trains/hour to deploy using capacity logic.
    """

    def decide_bus(self, d: DistrictState) -> Tuple[str, int]:
        baseline_capacity = BUS_BASE_FREQ * BUS_CAPACITY
        arrival_per_hour = d.bus_load * baseline_capacity

        required_freq = arrival_per_hour / (BUS_CAPACITY * BUS_TARGET_LF)
        extra = math.ceil(required_freq - d.bus_freq)

        if extra <= 0:
            return ("NO_CHANGE", 0)

        # If roads are too congested, adding buses can worsen road flow -> use bus priority instead
        if d.road_traffic > TRAFFIC_BUS_ADD_LIMIT:
            return ("USE_BUS_PRIORITY", 0)

        extra = min(extra, BUS_MAX_EXTRA)
        return ("ADD_BUSES", extra)

    def decide_mrt(self, d: DistrictState) -> Tuple[str, int]:
        baseline_capacity = MRT_BASE_FREQ * TRAIN_CAPACITY
        arrival_per_hour = d.mrt_load * baseline_capacity

        required_freq = arrival_per_hour / (TRAIN_CAPACITY * MRT_TARGET_LF)
        extra = math.ceil(required_freq - d.mrt_freq)

        if extra <= 0:
            return ("NO_CHANGE", 0)

        extra = min(extra, MRT_MAX_EXTRA)
        return ("ADD_TRAINS", extra)

    def decide_crowd(self, d: DistrictState) -> bool:
        return d.station_crowding > CROWDING_CRITICAL


class ExecutionAgent:
    def apply(self, d: DistrictState, bus_decision: str, bus_extra: int, mrt_decision: str, mrt_extra: int, do_crowd: bool) -> None:
        # Crowd management first (safety/comfort)
        if do_crowd:
            d.station_crowding = max(0.0, d.station_crowding - 0.15)
            print(f"[ACTION] {d.name}: Crowd management (reduce station crowding)")

        # MRT actions
        if mrt_decision == "ADD_TRAINS":
            d.mrt_freq += mrt_extra
            # immediate effect: relieve MRT and stations a bit (fast response)
            d.mrt_load = max(0.0, d.mrt_load - 0.06 * (mrt_extra / max(1, MRT_MAX_EXTRA)))
            d.station_crowding = max(0.0, d.station_crowding - 0.03 * (mrt_extra / max(1, MRT_MAX_EXTRA)))
            print(f"[ACTION] {d.name}: +{mrt_extra} trains/hour (mrt_freq={d.mrt_freq:.1f})")
        else:
            print(f"[ACTION] {d.name}: MRT no change")

        # Bus actions
        if bus_decision == "ADD_BUSES":
            d.bus_freq += bus_extra
            d.bus_load = max(0.0, d.bus_load - 0.06 * (bus_extra / max(1, BUS_MAX_EXTRA)))
            print(f"[ACTION] {d.name}: +{bus_extra} buses/hour (bus_freq={d.bus_freq:.1f})")

        elif bus_decision == "USE_BUS_PRIORITY":
            d.road_traffic = max(0.0, d.road_traffic - 0.07)
            d.bus_load = max(0.0, d.bus_load - 0.05)
            print(f"[ACTION] {d.name}: Bus priority signals (no extra buses due to high traffic)")

        else:
            print(f"[ACTION] {d.name}: Bus no change")


# -----------------------------
# Runner
# -----------------------------

def make_city() -> CityState:
    # Districts are just clusters/areas for prototype, not exact SG geography
    return CityState(
        districts={
            "Central": DistrictState("Central", road_traffic=0.78, bus_load=0.82, mrt_load=0.78, station_crowding=0.85, air_quality=58),
            "North":   DistrictState("North",   road_traffic=0.62, bus_load=0.60, mrt_load=0.55, station_crowding=0.60, air_quality=65),
            "East":    DistrictState("East",    road_traffic=0.58, bus_load=0.75, mrt_load=0.70, station_crowding=0.66, air_quality=70),
            "West":    DistrictState("West",    road_traffic=0.66, bus_load=0.68, mrt_load=0.64, station_crowding=0.65, air_quality=62),
        }
    )


def main(steps: int = 10, seed: int = 42) -> None:
    random.seed(seed)

    city = make_city()
    env = MobilityEnvironment()
    monitor = MonitoringAgent()
    planner = CapacityPlannerAgent()
    executor = ExecutionAgent()

    city.history.append(city.snapshot_metrics())

    for _ in range(steps):
        print(f"\n=== Time {city.t} ===")
        districts = monitor.observe(city)

        for d in districts.values():
            bus_decision, bus_extra = planner.decide_bus(d)
            mrt_decision, mrt_extra = planner.decide_mrt(d)
            do_crowd = planner.decide_crowd(d)

            executor.apply(d, bus_decision, bus_extra, mrt_decision, mrt_extra, do_crowd)

        env.step(city)

        snap = city.history[-1]
        print(
            f"[METRICS] traffic={snap['avg_traffic']:.2f} bus_load={snap['avg_bus_load']:.2f} "
            f"mrt_load={snap['avg_mrt_load']:.2f} station={snap['avg_station']:.2f} air={snap['avg_air']:.1f} "
            f"| bus_freq={snap['avg_bus_freq']:.1f} mrt_freq={snap['avg_mrt_freq']:.1f}"
        )

    print("\nDone.")


if __name__ == "__main__":
    main()
