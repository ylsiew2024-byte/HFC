"""
CapacityPlannerAgent - Generates action proposals for each district.
"""
from typing import Dict, Any, List
from ..models import (
    CityState,
    BUS_TARGET_LF,
    MRT_TARGET_LF,
    CROWDING_CRITICAL,
)


class CapacityPlannerAgent:
    """Plans capacity adjustments and generates proposals."""

    def propose(self, city: CityState, observations: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generate action proposals for each district.
        Returns list of proposal dicts.
        """
        proposals = []

        for district in city.districts:
            obs = observations["districts"][district.name]

            # Calculate urgency score
            urgency = self._calculate_urgency(obs)

            # Determine actions
            bus_action = "NO_CHANGE"
            bus_extra = 0
            mrt_action = "NO_CHANGE"
            mrt_extra = 0
            do_crowd_mgmt = False
            do_nudge = False

            # Bus decisions
            if obs["bus_load_factor"] > BUS_TARGET_LF:
                if obs["road_traffic"] > 0.8:
                    bus_action = "USE_BUS_PRIORITY"
                else:
                    bus_action = "ADD_BUSES"
                    # Request more buses based on how overloaded
                    overload = obs["bus_load_factor"] - BUS_TARGET_LF
                    bus_extra = min(10, max(1, int(overload * 20)))

            # MRT decisions
            if obs["mrt_load_factor"] > MRT_TARGET_LF:
                mrt_action = "ADD_TRAINS"
                overload = obs["mrt_load_factor"] - MRT_TARGET_LF
                mrt_extra = min(3, max(1, int(overload * 10)))

            # Crowd management if critical crowding
            if obs["station_crowding"] > CROWDING_CRITICAL:
                do_crowd_mgmt = True

            # Nudges if crowding or traffic is high
            if obs["station_crowding"] > 0.7 or obs["road_traffic"] > 0.75:
                if not obs["nudges_active"]:
                    do_nudge = True

            proposals.append({
                "district": district.name,
                "bus_action": bus_action,
                "bus_extra": bus_extra,
                "mrt_action": mrt_action,
                "mrt_extra": mrt_extra,
                "do_crowd_mgmt": do_crowd_mgmt,
                "do_nudge": do_nudge,
                "urgency": urgency,
            })

        return proposals

    def _calculate_urgency(self, obs: Dict[str, Any]) -> float:
        """Calculate urgency score for a district."""
        urgency = 0.0

        # +2.0 if station crowding > critical
        if obs["station_crowding"] > CROWDING_CRITICAL:
            urgency += 2.0

        # +1.0 if bus_load > target
        if obs["bus_load_factor"] > BUS_TARGET_LF:
            urgency += 1.0

        # +1.0 if mrt_load > target
        if obs["mrt_load_factor"] > MRT_TARGET_LF:
            urgency += 1.0

        # +0.5 if road traffic high (> 0.75)
        if obs["road_traffic"] > 0.75:
            urgency += 0.5

        # +0.5 if air quality low (< 60)
        if obs["air_quality"] < 60:
            urgency += 0.5

        return urgency
