"""
ExecutionAgent - Applies approved actions to the city state. No cost/money involved.
"""
from typing import Dict, Any, List
from ..models import CityState


class ExecutionAgent:
    """Executes approved actions and logs them."""

    def execute(self, city: CityState, approved: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Apply approved district and train actions. Returns action events."""
        action_events = []

        # District (bus) actions
        for proposal in approved["district_proposals"]:
            district_name = proposal["district"]
            district = next((d for d in city.districts if d.name == district_name), None)
            if district is None:
                continue

            actions_taken = []

            if proposal["do_crowd_mgmt"]:
                district.station_crowding *= 0.85
                actions_taken.append("CROWD_MGMT")

            if proposal["bus_action"] == "ADD_BUSES" and proposal["bus_extra"] > 0:
                district.bus_capacity += proposal["bus_extra"]
                district.bus_load_factor *= 0.95
                actions_taken.append(f"ADD_BUSES +{proposal['bus_extra']}")
            elif proposal["bus_action"] == "USE_BUS_PRIORITY":
                district.bus_load_factor *= 0.97
                district.road_traffic *= 0.98
                actions_taken.append("BUS_PRIORITY")

            if proposal["do_nudge"]:
                district.nudges_active = True
                district.nudge_timer = 3
                actions_taken.append("NUDGE_ACTIVATED")

            if actions_taken:
                event = {
                    "t": city.t,
                    "hour": city.hour_of_day,
                    "type": "district",
                    "district": district_name,
                    "actions": actions_taken,
                    "urgency": round(proposal["urgency"], 2),
                }
                action_events.append(event)
                city.action_log.append(event)

        # Train line actions
        for proposal in approved["train_proposals"]:
            line_id = proposal["line_id"]
            line = city.train_lines.get(line_id)
            if line is None:
                continue

            actions_taken = []

            if proposal["mrt_action"] == "ADD_TRAINS" and proposal["mrt_extra"] > 0:
                line.frequency += proposal["mrt_extra"]
                line.line_load *= 0.95
                action_str = f"ADD_TRAINS +{proposal['mrt_extra']}"
                actions_taken.append(action_str)
                line.actions_this_hour.append(action_str)

            if actions_taken:
                event = {
                    "t": city.t,
                    "hour": city.hour_of_day,
                    "type": "train_line",
                    "line_id": line_id,
                    "line_name": line.line_name,
                    "actions": actions_taken,
                    "urgency": round(proposal["urgency"], 2),
                }
                action_events.append(event)
                city.action_log.append(event)

        return action_events
