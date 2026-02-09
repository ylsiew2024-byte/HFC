"""
PolicyAgent v2 — Validates proposals against operational constraints.
- No bus lane policy (removed: not implementable by operator)
- Travel advisories only off-peak
- Escalation path for severe disruptions
- Cost-aware: penalises over-deployment when unnecessary
"""
from typing import Dict, Any, List
from ..models import (
    BUS_MAX_EXTRA, MRT_MAX_EXTRA, TRAFFIC_BUS_ADD_LIMIT, CROWDING_CRITICAL,
    PEAK_HOURS,
)


class PolicyAgent:
    """Enforces operational policy rules and constraints on proposals."""

    def sanitize(self, proposals: Dict[str, Any], observations: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and sanitize both district and train proposals."""
        sanitized_districts = []
        adjustments = []
        blocked = []

        hour = observations.get("hour", 12)
        is_peak = hour in PEAK_HOURS

        for proposal in proposals["district_proposals"]:
            district_name = proposal["district"]
            obs = observations["districts"][district_name]
            clean = proposal.copy()

            # Rule 1: Cap bus deployments
            orig_extra = clean["bus_extra"]
            clean["bus_extra"] = max(0, min(BUS_MAX_EXTRA, clean["bus_extra"]))
            if clean["bus_extra"] != orig_extra:
                adjustments.append(
                    f"Clamped {district_name} bus_extra from {orig_extra} to {clean['bus_extra']}"
                )

            # Rule 2: Block reserve deployment on gridlocked roads (use SHORT_TURN instead)
            if obs["road_traffic"] > TRAFFIC_BUS_ADD_LIMIT:
                if clean["bus_action"] == "DEPLOY_RESERVE" and not clean.get("do_reroute"):
                    blocked.append(
                        f"Blocked DEPLOY_RESERVE for {district_name}: traffic "
                        f"{obs['road_traffic']*100:.0f}% > {TRAFFIC_BUS_ADD_LIMIT*100:.0f}% — "
                        f"converting to SHORT_TURN"
                    )
                    clean["bus_action"] = "SHORT_TURN"
                    clean["bus_extra"] = 0
                    clean["do_short_turn"] = True

            # Rule 3: Crowd management only when crowding > critical threshold
            if obs["station_crowding"] <= CROWDING_CRITICAL:
                if clean["do_crowd_mgmt"]:
                    adjustments.append(
                        f"Removed crowd_mgmt for {district_name}: crowding "
                        f"{obs['station_crowding']*100:.0f}% <= {CROWDING_CRITICAL*100:.0f}%"
                    )
                clean["do_crowd_mgmt"] = False

            # Rule 4: NO travel advisories during peak hours
            if is_peak and clean.get("do_advisory"):
                blocked.append(
                    f"Blocked travel advisory for {district_name}: peak hour "
                    f"({hour:02d}:00) — commuters cannot shift timing"
                )
                clean["do_advisory"] = False

            # Rule 5: Advisory only when conditions warrant AND alternatives exist
            if clean.get("do_advisory"):
                if obs["station_crowding"] <= 0.7 and obs["road_traffic"] <= 0.75:
                    adjustments.append(
                        f"Removed advisory for {district_name}: conditions not met"
                    )
                    clean["do_advisory"] = False

            sanitized_districts.append(clean)

        # Train proposals
        sanitized_trains = []
        for proposal in proposals["train_proposals"]:
            clean = proposal.copy()
            orig_extra = clean["mrt_extra"]
            clean["mrt_extra"] = max(0, min(MRT_MAX_EXTRA, clean["mrt_extra"]))
            if clean["mrt_extra"] != orig_extra:
                adjustments.append(
                    f"Clamped {clean['line_id']} mrt_extra from {orig_extra} to {clean['mrt_extra']}"
                )
            sanitized_trains.append(clean)

        return {
            "district_proposals": sanitized_districts,
            "train_proposals": sanitized_trains,
            "_trace": {
                "adjustments": adjustments,
                "blocked": blocked,
            },
        }
