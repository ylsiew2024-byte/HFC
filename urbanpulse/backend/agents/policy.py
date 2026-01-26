"""
PolicyAgent - Validates and sanitizes proposals against constraints.
"""
from typing import Dict, Any, List
from ..models import (
    BUS_MAX_EXTRA,
    MRT_MAX_EXTRA,
    TRAFFIC_BUS_ADD_LIMIT,
    CROWDING_CRITICAL,
)


class PolicyAgent:
    """Enforces policy rules and constraints on proposals."""

    def sanitize(
        self,
        proposals: List[Dict[str, Any]],
        observations: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Validate and sanitize proposals against policy rules.
        Returns list of sanitized proposals.
        """
        sanitized = []

        for proposal in proposals:
            district_name = proposal["district"]
            obs = observations["districts"][district_name]

            # Create a copy to modify
            clean = proposal.copy()

            # Rule 1: If road traffic > limit, cannot add buses, only bus priority
            if obs["road_traffic"] > TRAFFIC_BUS_ADD_LIMIT:
                if clean["bus_action"] == "ADD_BUSES":
                    clean["bus_action"] = "USE_BUS_PRIORITY"
                    clean["bus_extra"] = 0

            # Rule 2: Clamp bus_extra to [0, BUS_MAX_EXTRA]
            clean["bus_extra"] = max(0, min(BUS_MAX_EXTRA, clean["bus_extra"]))

            # Rule 3: Clamp mrt_extra to [0, MRT_MAX_EXTRA]
            clean["mrt_extra"] = max(0, min(MRT_MAX_EXTRA, clean["mrt_extra"]))

            # Rule 4: Crowd management only if station_crowding > critical
            if obs["station_crowding"] <= CROWDING_CRITICAL:
                clean["do_crowd_mgmt"] = False

            # Rule 5: Nudges only when crowding OR traffic is high
            if obs["station_crowding"] <= 0.7 and obs["road_traffic"] <= 0.75:
                clean["do_nudge"] = False

            sanitized.append(clean)

        return sanitized
