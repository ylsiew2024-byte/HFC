from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Tuple
import random
import time


# -----------------------------
# Data models
# -----------------------------

@dataclass
class DistrictState:
    name: str
    traffic: float          # 0.0 (free) -> 1.0 (gridlock)
    air_quality: float      # 0.0 (bad) -> 100.0 (good)
    energy_load: float      # 0.0 -> 1.0 (peak)
    crowding: float         # 0.0 -> 1.0 (packed)

    def clamp(self) -> None:
        self.traffic = max(0.0, min(1.0, self.traffic))
        self.energy_load = max(0.0, min(1.0, self.energy_load))
        self.crowding = max(0.0, min(1.0, self.crowding))
        self.air_quality = max(0.0, min(100.0, self.air_quality))


@dataclass
class CityState:
    districts: Dict[str, DistrictState]
    t: int = 0
    history: List[Dict[str, float]] = field(default_factory=list)

    def snapshot_metrics(self) -> Dict[str, float]:
        # Simple overall metrics (you can explain these in your proposal)
        avg_traffic = sum(d.traffic for d in self.districts.values()) / len(self.districts)
        avg_air = sum(d.air_quality for d in self.districts.values()) / len(self.districts)
        avg_energy = sum(d.energy_load for d in self.districts.values()) / len(self.districts)
        avg_crowd = sum(d.crowding for d in self.districts.values()) / len(self.districts)

        liveability_score = (1 - avg_traffic) * 40 + (avg_air / 100) * 40 + (1 - avg_crowd) * 20
        environment_score = (avg_air / 100) * 60 + (1 - avg_energy) * 40

        return {
            "t": float(self.t),
            "avg_traffic": avg_traffic,
            "avg_air": avg_air,
            "avg_energy": avg_energy,
            "avg_crowding": avg_crowd,
            "liveability_score": liveability_score,     # higher is better
            "environment_score": environment_score,     # higher is better
        }


# -----------------------------
# Simulated environment
# -----------------------------

class CityEnvironment:
    """
    Simulates city dynamics + applies actions.
    This lets you demo "Agentic AI" without needing real gov data.
    """

    def __init__(self, seed: int = 42):
        random.seed(seed)

    def step(self, city: CityState, actions: List[Tuple[str, str]]) -> None:
        """
        Advance one time step:
        - apply actions
        - add natural fluctuations
        - update air quality based on traffic & energy
        """
        # 1) Apply actions
        for district_name, action in actions:
            d = city.districts[district_name]
            self._apply_action(d, action)

        # 2) Natural fluctuations & coupling effects
        for d in city.districts.values():
            # Random daily variation
            d.traffic += random.uniform(-0.03, 0.06)
            d.crowding += random.uniform(-0.03, 0.05)
            d.energy_load += random.uniform(-0.02, 0.05)

            # Coupling: more traffic -> worse air, more energy -> slightly worse air
            d.air_quality += (-25.0 * d.traffic) + (-8.0 * d.energy_load) + random.uniform(-1.5, 1.5)

            d.clamp()

        # 3) Time + log metrics
        city.t += 1
        city.history.append(city.snapshot_metrics())

    def _apply_action(self, d: DistrictState, action: str) -> None:
        """
        These "actions" are your agent tools.
        """
        if action == "OPTIMIZE_TRAFFIC_SIGNALS":
            d.traffic -= 0.10
            d.air_quality += 2.0

        elif action == "BOOST_PUBLIC_TRANSIT":
            d.traffic -= 0.07
            d.energy_load += 0.03  # more transit running
            d.air_quality += 1.0

        elif action == "CONGESTION_PRICING":
            d.traffic -= 0.12
            d.air_quality += 3.0

        elif action == "LIMIT_VEHICLE_ENTRY":
            d.traffic -= 0.15
            d.air_quality += 4.0

        elif action == "SHIFT_EVENT_TIMES":
            d.crowding -= 0.12
            d.traffic -= 0.05

        elif action == "SMART_COOLING_POLICY":
            d.energy_load -= 0.12
            d.air_quality += 0.5

        elif action == "NO_ACTION":
            pass

        else:
            # Unknown action: do nothing
            pass

        d.clamp()


# -----------------------------
# Agents
# -----------------------------

class MonitoringAgent:
    def observe(self, city: CityState) -> Dict[str, Dict[str, float]]:
        observations = {}
        for name, d in city.districts.items():
            observations[name] = {
                "traffic": d.traffic,
                "air_quality": d.air_quality,
                "energy_load": d.energy_load,
                "crowding": d.crowding,
            }
        return observations


class PlannerAgent:
    """
    Plans per-district actions based on goals + state over time.
    Includes "learning" via simple thresholds that adapt.
    """

    def __init__(self):
        # Adaptive thresholds (stateful!)
        self.traffic_threshold = 0.70
        self.air_threshold = 55.0
        self.energy_threshold = 0.75
        self.crowd_threshold = 0.70

        self.last_outcomes: List[Dict[str, float]] = []

    def decide(self, observations: Dict[str, Dict[str, float]]) -> Dict[str, str]:
        plan: Dict[str, str] = {}

        for district, o in observations.items():
            traffic = o["traffic"]
            air = o["air_quality"]
            energy = o["energy_load"]
            crowd = o["crowding"]

            # Priority: safety/health -> air quality
            if air < self.air_threshold and traffic > 0.45:
                plan[district] = "LIMIT_VEHICLE_ENTRY"
            elif traffic > self.traffic_threshold:
                plan[district] = "OPTIMIZE_TRAFFIC_SIGNALS"
            elif crowd > self.crowd_threshold:
                plan[district] = "SHIFT_EVENT_TIMES"
            elif energy > self.energy_threshold:
                plan[district] = "SMART_COOLING_POLICY"
            else:
                # mild improvement nudge
                if traffic > 0.55:
                    plan[district] = "BOOST_PUBLIC_TRANSIT"
                else:
                    plan[district] = "NO_ACTION"

        return plan

    def learn(self, metrics: Dict[str, float]) -> None:
        """
        Simple feedback adaptation:
        - If liveability drops, become more aggressive on traffic/crowding.
        - If environment drops, become more aggressive on energy/air.
        """
        self.last_outcomes.append(metrics)
        if len(self.last_outcomes) < 3:
            return

        # Compare last 3 steps trend
        m1, m2, m3 = self.last_outcomes[-3], self.last_outcomes[-2], self.last_outcomes[-1]
        live_trend = m3["liveability_score"] - m1["liveability_score"]
        env_trend = m3["environment_score"] - m1["environment_score"]

        # Adjust thresholds (bounded)
        if live_trend < -1.0:
            self.traffic_threshold = max(0.55, self.traffic_threshold - 0.03)
            self.crowd_threshold = max(0.55, self.crowd_threshold - 0.03)

        if env_trend < -1.0:
            self.air_threshold = min(70.0, self.air_threshold + 1.0)  # require better air
            self.energy_threshold = max(0.60, self.energy_threshold - 0.03)

        # If things improve, relax slightly (stability)
        if live_trend > 1.0:
            self.traffic_threshold = min(0.80, self.traffic_threshold + 0.01)
            self.crowd_threshold = min(0.80, self.crowd_threshold + 0.01)

        if env_trend > 1.0:
            self.energy_threshold = min(0.85, self.energy_threshold + 0.01)


class CoordinationAgent:
    """
    Ensures district plans don't create unfair trade-offs.
    Simple equity rule: don't overload one district with strict actions every step.
    """

    def __init__(self):
        self.strict_action_counts: Dict[str, int] = {}

    def coordinate(self, plan: Dict[str, str]) -> Dict[str, str]:
        coordinated = dict(plan)

        for district, action in plan.items():
            if district not in self.strict_action_counts:
                self.strict_action_counts[district] = 0

            is_strict = action in {"LIMIT_VEHICLE_ENTRY", "CONGESTION_PRICING"}
            if is_strict:
                self.strict_action_counts[district] += 1

            # Equity guard: if a district gets strict actions too often, downgrade once
            if self.strict_action_counts[district] >= 3 and is_strict:
                coordinated[district] = "OPTIMIZE_TRAFFIC_SIGNALS"
                self.strict_action_counts[district] = 0

        return coordinated


class GovernanceAgent:
    """
    Ethics & safety constraints:
    - Blocks high-impact actions unless conditions justify them.
    - Simulates "human approval thresholds" by requiring severe triggers.
    """

    def __init__(self):
        self.audit_log: List[str] = []

    def approve(self, observations: Dict[str, Dict[str, float]], plan: Dict[str, str]) -> Dict[str, str]:
        approved = dict(plan)

        for district, action in plan.items():
            o = observations[district]

            if action == "LIMIT_VEHICLE_ENTRY":
                # Only allow if air is genuinely poor or traffic is extreme
                if not (o["air_quality"] < 50.0 or o["traffic"] > 0.80):
                    approved[district] = "BOOST_PUBLIC_TRANSIT"
                    self.audit_log.append(
                        f"[GOV] Blocked LIMIT_VEHICLE_ENTRY in {district}: not severe enough; replaced with BOOST_PUBLIC_TRANSIT."
                    )

            if action == "CONGESTION_PRICING":
                # Only allow if traffic is very high
                if o["traffic"] < 0.85:
                    approved[district] = "OPTIMIZE_TRAFFIC_SIGNALS"
                    self.audit_log.append(
                        f"[GOV] Blocked CONGESTION_PRICING in {district}: traffic not high enough; replaced with OPTIMIZE_TRAFFIC_SIGNALS."
                    )

        return approved


class ExecutionAgent:
    def execute(self, plan: Dict[str, str]) -> List[Tuple[str, str]]:
        # Convert plan into executable action list
        actions = [(district, action) for district, action in plan.items()]
        return actions


# -----------------------------
# Runner / Demo
# -----------------------------

def make_initial_city() -> CityState:
    districts = {
        "Central": DistrictState("Central", traffic=0.78, air_quality=55.0, energy_load=0.72, crowding=0.75),
        "North":   DistrictState("North",   traffic=0.62, air_quality=62.0, energy_load=0.68, crowding=0.60),
        "East":    DistrictState("East",    traffic=0.58, air_quality=70.0, energy_load=0.80, crowding=0.55),
        "West":    DistrictState("West",    traffic=0.66, air_quality=60.0, energy_load=0.74, crowding=0.62),
    }
    return CityState(districts=districts)


def print_step(city: CityState, plan: Dict[str, str]) -> None:
    m = city.snapshot_metrics()
    print(f"\n=== t={int(m['t'])} ===")
    print(f"City metrics: traffic={m['avg_traffic']:.2f} | air={m['avg_air']:.1f} | energy={m['avg_energy']:.2f} | crowd={m['avg_crowding']:.2f}")
    print(f"Scores: liveability={m['liveability_score']:.1f} | environment={m['environment_score']:.1f}")
    for dname, action in plan.items():
        d = city.districts[dname]
        print(f"- {dname:7} | action={action:22} | traffic={d.traffic:.2f} air={d.air_quality:.1f} energy={d.energy_load:.2f} crowd={d.crowding:.2f}")


def main(steps: int = 12, seed: int = 42, sleep_s: float = 0.0) -> None:
    env = CityEnvironment(seed=seed)
    city = make_initial_city()

    monitor = MonitoringAgent()
    planner = PlannerAgent()
    coordinator = CoordinationAgent()
    governance = GovernanceAgent()
    executor = ExecutionAgent()

    # Initial log
    city.history.append(city.snapshot_metrics())

    for _ in range(steps):
        observations = monitor.observe(city)
        raw_plan = planner.decide(observations)
        coordinated_plan = coordinator.coordinate(raw_plan)
        approved_plan = governance.approve(observations, coordinated_plan)

        print_step(city, approved_plan)

        actions = executor.execute(approved_plan)
        env.step(city, actions)

        # Learning from outcomes
        planner.learn(city.history[-1])

        if sleep_s > 0:
            time.sleep(sleep_s)

    if governance.audit_log:
        print("\n=== Governance Audit Log ===")
        for line in governance.audit_log[-10:]:
            print(line)

    # Final summary
    start = city.history[0]
    end = city.history[-1]
    print("\n=== Summary (Start -> End) ===")
    print(f"Liveability:  {start['liveability_score']:.1f} -> {end['liveability_score']:.1f}")
    print(f"Environment:  {start['environment_score']:.1f} -> {end['environment_score']:.1f}")


if __name__ == "__main__":
    main()
