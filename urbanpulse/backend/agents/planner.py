"""
CapacityPlannerAgent - Generates action proposals for districts (bus) and train lines.
"""
from typing import Dict, Any, List
from ..models import (
    CityState, BUS_TARGET_LF, MRT_TARGET_LF, CROWDING_CRITICAL,
)


class CapacityPlannerAgent:
    """Plans capacity adjustments and generates proposals."""

    def propose(self, city: CityState, observations: Dict[str, Any]) -> Dict[str, Any]:
        """Generate proposals for districts (bus) and train lines separately."""
        district_proposals = []
        for district in city.districts:
            obs = observations["districts"][district.name]
            urgency = self._district_urgency(obs)

            bus_action = "NO_CHANGE"
            bus_extra = 0
            do_crowd_mgmt = False
            do_nudge = False

            if obs["bus_load_factor"] > BUS_TARGET_LF:
                if obs["road_traffic"] > 0.8:
                    bus_action = "USE_BUS_PRIORITY"
                else:
                    bus_action = "ADD_BUSES"
                    overload = obs["bus_load_factor"] - BUS_TARGET_LF
                    bus_extra = min(10, max(1, int(overload * 20)))

            if obs["station_crowding"] > CROWDING_CRITICAL:
                do_crowd_mgmt = True

            if obs["station_crowding"] > 0.7 or obs["road_traffic"] > 0.75:
                if not obs["nudges_active"]:
                    do_nudge = True

            district_proposals.append({
                "district": district.name,
                "bus_action": bus_action,
                "bus_extra": bus_extra,
                "do_crowd_mgmt": do_crowd_mgmt,
                "do_nudge": do_nudge,
                "urgency": urgency,
            })

        # Train line proposals
        train_proposals = []
        for line_id, line_obs in observations.get("train_lines", {}).items():
            urgency = self._train_urgency(line_obs)
            mrt_action = "NO_CHANGE"
            mrt_extra = 0

            if line_obs["line_load"] > MRT_TARGET_LF:
                mrt_action = "ADD_TRAINS"
                overload = line_obs["line_load"] - MRT_TARGET_LF
                mrt_extra = min(3, max(1, int(overload * 10)))

            train_proposals.append({
                "line_id": line_id,
                "mrt_action": mrt_action,
                "mrt_extra": mrt_extra,
                "urgency": urgency,
            })

        return {
            "district_proposals": district_proposals,
            "train_proposals": train_proposals,
        }

    def _district_urgency(self, obs: Dict[str, Any]) -> float:
        urgency = 0.0
        if obs["station_crowding"] > CROWDING_CRITICAL:
            urgency += 2.0
        if obs["bus_load_factor"] > BUS_TARGET_LF:
            urgency += 1.0
        if obs["mrt_load_factor"] > MRT_TARGET_LF:
            urgency += 1.0
        if obs["road_traffic"] > 0.75:
            urgency += 0.5
        if obs["air_quality"] < 60:
            urgency += 0.5
        return urgency

    def _train_urgency(self, obs: Dict[str, Any]) -> float:
        urgency = 0.0
        if obs["line_load"] > MRT_TARGET_LF:
            urgency += 2.0
        if obs["disruption_level"] > 0.3:
            urgency += 1.5
        if obs["line_load"] > 0.6:
            urgency += 0.5
        return urgency
