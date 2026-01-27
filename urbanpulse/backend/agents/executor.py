"""
ExecutionAgent - Applies approved actions to the city state.
"""
from typing import Dict, Any, List
from ..models import (
    CityState,
    BUS_COST_PER_UNIT, MRT_COST_PER_UNIT,
    CROWD_MGMT_COST, NUDGE_COST
)


class ExecutionAgent:
    """Executes approved actions and logs them."""

    def execute(
        self,
        city: CityState,
        approved_proposals: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Apply approved actions to the city state.
        Deducts costs for each action taken.
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
            step_cost = 0

            # Apply crowd management first (safety)
            if proposal["do_crowd_mgmt"]:
                cost = CROWD_MGMT_COST
                if city.deduct_funds(cost, "crowd_mgmt"):
                    # Crowd management reduces crowding immediately
                    district.station_crowding *= 0.85
                    actions_taken.append("CROWD_MGMT")
                    step_cost += cost

            # Apply MRT changes
            if proposal["mrt_action"] == "ADD_TRAINS" and proposal["mrt_extra"] > 0:
                cost = MRT_COST_PER_UNIT * proposal["mrt_extra"]
                if city.deduct_funds(cost, "mrt_deployment"):
                    district.mrt_capacity += proposal["mrt_extra"]
                    # Adding capacity reduces load factor
                    district.mrt_load_factor *= 0.95
                    actions_taken.append(f"ADD_TRAINS +{proposal['mrt_extra']}")
                    step_cost += cost

            # Apply bus changes
            if proposal["bus_action"] == "ADD_BUSES" and proposal["bus_extra"] > 0:
                cost = BUS_COST_PER_UNIT * proposal["bus_extra"]
                if city.deduct_funds(cost, "bus_deployment"):
                    district.bus_capacity += proposal["bus_extra"]
                    # Adding capacity reduces load factor
                    district.bus_load_factor *= 0.95
                    actions_taken.append(f"ADD_BUSES +{proposal['bus_extra']}")
                    step_cost += cost
            elif proposal["bus_action"] == "USE_BUS_PRIORITY":
                # Bus priority is cheaper - just traffic management
                cost = BUS_COST_PER_UNIT * 0.5
                if city.deduct_funds(cost, "bus_priority"):
                    # Bus priority improves efficiency without adding buses
                    district.bus_load_factor *= 0.97
                    district.road_traffic *= 0.98
                    actions_taken.append("BUS_PRIORITY")
                    step_cost += cost

            # Apply nudges
            if proposal["do_nudge"]:
                cost = NUDGE_COST
                if city.deduct_funds(cost, "nudge_campaign"):
                    district.nudges_active = True
                    district.nudge_timer = 3  # Nudges last 3 steps
                    actions_taken.append("NUDGE_ACTIVATED")
                    step_cost += cost

            # Only log if actions were taken
            if actions_taken:
                event = {
                    "t": city.t,
                    "district": district_name,
                    "actions": actions_taken,
                    "urgency": round(proposal["urgency"], 2),
                    "cost": round(step_cost, 1),
                }
                action_events.append(event)
                city.action_log.append(event)

        return action_events
