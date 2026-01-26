"""
ExecutionAgent - Applies approved actions to the city state.
"""
from typing import Dict, Any, List
from ..models import CityState


class ExecutionAgent:
    """Executes approved actions and logs them."""

    def execute(
        self,
        city: CityState,
        approved_proposals: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Apply approved actions to the city state.
        Returns list of action events for logging.
        """
        action_events = []

        for proposal in approved_proposals:
            district_name = proposal["district"]
            district = next(
                (d for d in city.districts if d.name == district_name),
                None
            )

            if district is None:
                continue

            actions_taken = []

            # Apply crowd management first (safety)
            if proposal["do_crowd_mgmt"]:
                # Crowd management reduces crowding immediately
                district.station_crowding *= 0.85
                actions_taken.append("CROWD_MGMT")

            # Apply MRT changes
            if proposal["mrt_action"] == "ADD_TRAINS" and proposal["mrt_extra"] > 0:
                district.mrt_capacity += proposal["mrt_extra"]
                # Adding capacity reduces load factor
                district.mrt_load_factor *= 0.95
                actions_taken.append(f"ADD_TRAINS +{proposal['mrt_extra']}")

            # Apply bus changes
            if proposal["bus_action"] == "ADD_BUSES" and proposal["bus_extra"] > 0:
                district.bus_capacity += proposal["bus_extra"]
                # Adding capacity reduces load factor
                district.bus_load_factor *= 0.95
                actions_taken.append(f"ADD_BUSES +{proposal['bus_extra']}")
            elif proposal["bus_action"] == "USE_BUS_PRIORITY":
                # Bus priority improves efficiency without adding buses
                district.bus_load_factor *= 0.97
                district.road_traffic *= 0.98
                actions_taken.append("BUS_PRIORITY")

            # Apply nudges
            if proposal["do_nudge"]:
                district.nudges_active = True
                district.nudge_timer = 3  # Nudges last 3 steps
                actions_taken.append("NUDGE_ACTIVATED")

            # Only log if actions were taken
            if actions_taken:
                event = {
                    "t": city.t,
                    "district": district_name,
                    "actions": actions_taken,
                    "urgency": round(proposal["urgency"], 2),
                }
                action_events.append(event)
                city.action_log.append(event)

        return action_events
