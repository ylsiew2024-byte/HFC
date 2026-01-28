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
        """Validate and sanitize both district and train proposals.
        Returns sanitized proposals and a trace of adjustments/blocks."""
        sanitized_districts = []
        adjustments = []
        blocked = []

        for proposal in proposals["district_proposals"]:
            district_name = proposal["district"]
            obs = observations["districts"][district_name]
            clean = proposal.copy()

            if obs["road_traffic"] > TRAFFIC_BUS_ADD_LIMIT:
                if clean["bus_action"] == "ADD_BUSES":
                    blocked.append(f"Blocked ADD_BUSES for {district_name}: road traffic {obs['road_traffic']*100:.0f}% > {TRAFFIC_BUS_ADD_LIMIT*100:.0f}% limit")
                    clean["bus_action"] = "USE_BUS_PRIORITY"
                    clean["bus_extra"] = 0

            orig_extra = clean["bus_extra"]
            clean["bus_extra"] = max(0, min(BUS_MAX_EXTRA, clean["bus_extra"]))
            if clean["bus_extra"] != orig_extra:
                adjustments.append(f"Clamped {district_name} bus_extra from {orig_extra} to {clean['bus_extra']}")

            if obs["station_crowding"] <= CROWDING_CRITICAL:
                if clean["do_crowd_mgmt"]:
                    adjustments.append(f"Removed crowd_mgmt for {district_name}: crowding {obs['station_crowding']*100:.0f}% <= {CROWDING_CRITICAL*100:.0f}%")
                clean["do_crowd_mgmt"] = False

            if obs["station_crowding"] <= 0.7 and obs["road_traffic"] <= 0.75:
                if clean["do_nudge"]:
                    adjustments.append(f"Removed nudge for {district_name}: conditions not met")
                clean["do_nudge"] = False

            sanitized_districts.append(clean)

        sanitized_trains = []
        for proposal in proposals["train_proposals"]:
            clean = proposal.copy()
            orig_extra = clean["mrt_extra"]
            clean["mrt_extra"] = max(0, min(MRT_MAX_EXTRA, clean["mrt_extra"]))
            if clean["mrt_extra"] != orig_extra:
                adjustments.append(f"Clamped {clean['line_id']} mrt_extra from {orig_extra} to {clean['mrt_extra']}")
            sanitized_trains.append(clean)

        return {
            "district_proposals": sanitized_districts,
            "train_proposals": sanitized_trains,
            "_trace": {
                "adjustments": adjustments,
                "blocked": blocked,
            },
        }
