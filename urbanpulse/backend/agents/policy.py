"""
PolicyAgent - Validates and sanitizes proposals against constraints.
"""
from typing import Dict, Any, List
from ..models import (
    BUS_MAX_EXTRA, MRT_MAX_EXTRA, TRAFFIC_BUS_ADD_LIMIT, CROWDING_CRITICAL,
)


class PolicyAgent:
    """Enforces policy rules and constraints on proposals."""

    def sanitize(self, proposals: Dict[str, Any], observations: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and sanitize both district and train proposals."""
        sanitized_districts = []
        for proposal in proposals["district_proposals"]:
            district_name = proposal["district"]
            obs = observations["districts"][district_name]
            clean = proposal.copy()

            if obs["road_traffic"] > TRAFFIC_BUS_ADD_LIMIT:
                if clean["bus_action"] == "ADD_BUSES":
                    clean["bus_action"] = "USE_BUS_PRIORITY"
                    clean["bus_extra"] = 0

            clean["bus_extra"] = max(0, min(BUS_MAX_EXTRA, clean["bus_extra"]))

            if obs["station_crowding"] <= CROWDING_CRITICAL:
                clean["do_crowd_mgmt"] = False

            if obs["station_crowding"] <= 0.7 and obs["road_traffic"] <= 0.75:
                clean["do_nudge"] = False

            sanitized_districts.append(clean)

        sanitized_trains = []
        for proposal in proposals["train_proposals"]:
            clean = proposal.copy()
            clean["mrt_extra"] = max(0, min(MRT_MAX_EXTRA, clean["mrt_extra"]))
            sanitized_trains.append(clean)

        return {
            "district_proposals": sanitized_districts,
            "train_proposals": sanitized_trains,
        }
