"""
ExecutionAgent v2 — Applies approved actions to the city state.
Implements feasible operational controls:
  DEPLOY_RESERVE, SHORT_TURN, HOLD_AT_TERMINAL, REROUTE_AROUND_INCIDENT
  HOLD_HEADWAY, TRAVEL_ADVISORY, ESCALATE_TO_OPERATOR
"""
from typing import Dict, Any, List
from ..models import CityState, COST_ESCALATION_PENALTY


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

            # 1. Crowd management (safety first)
            if proposal.get("do_crowd_mgmt"):
                district.station_crowding *= 0.85
                actions_taken.append("CROWD_MGMT")

            # 2. Bus reserve deployment
            if proposal["bus_action"] == "DEPLOY_RESERVE" and proposal["bus_extra"] > 0:
                district.bus_capacity += proposal["bus_extra"]
                district.bus_load_factor *= 0.95
                actions_taken.append(f"DEPLOY_RESERVE +{proposal['bus_extra']}")

            # 3. Short-turn (cut route early to boost frequency in hot segment)
            if proposal.get("do_short_turn") or proposal["bus_action"] == "SHORT_TURN":
                district.bus_load_factor *= 0.94
                district.road_traffic *= 0.97
                actions_taken.append("SHORT_TURN")

            # 4. Hold at terminal (headway regulation to reduce bunching)
            if proposal.get("do_hold_terminal"):
                district.bus_load_factor *= 0.98
                actions_taken.append("HOLD_AT_TERMINAL")

            # 5. Reroute around incident
            if proposal.get("do_reroute"):
                district.road_traffic *= 0.95
                actions_taken.append("REROUTE_AROUND_INCIDENT")

            # 6. Travel advisory (replaces nudge — off-peak only)
            if proposal.get("do_advisory"):
                district.nudges_active = True
                district.nudge_timer = 3
                actions_taken.append("TRAVEL_ADVISORY")

            # 7. Escalation to human operator
            if proposal.get("do_escalate"):
                city.operator_escalations.append({
                    "t": city.t,
                    "hour": city.hour_of_day,
                    "type": "district",
                    "target": district_name,
                    "reason": f"Severe overload in {district_name}",
                })
                city.cost_this_hour += COST_ESCALATION_PENALTY
                actions_taken.append("ESCALATE_TO_OPERATOR")

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

            # Add trains
            if proposal["mrt_action"] == "ADD_TRAINS" and proposal["mrt_extra"] > 0:
                line.frequency += proposal["mrt_extra"]
                line.line_load *= 0.95
                action_str = f"ADD_TRAINS +{proposal['mrt_extra']}"
                actions_taken.append(action_str)
                line.actions_this_hour.append(action_str)

            # Hold headway (spacing control)
            if proposal.get("do_hold_headway"):
                line.line_load *= 0.98
                actions_taken.append("HOLD_HEADWAY")
                line.actions_this_hour.append("HOLD_HEADWAY")

            # Escalation
            if proposal.get("do_escalate"):
                city.operator_escalations.append({
                    "t": city.t,
                    "hour": city.hour_of_day,
                    "type": "train_line",
                    "target": line_id,
                    "reason": f"Severe disruption on {line.line_name}",
                })
                city.cost_this_hour += COST_ESCALATION_PENALTY
                actions_taken.append("ESCALATE_TO_OPERATOR")
                line.actions_this_hour.append("ESCALATE_TO_OPERATOR")

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
