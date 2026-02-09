"""
CapacityPlannerAgent v2 — Forecast-driven, cost-aware capacity planning.
Generates action proposals using feasible operational controls:
  Bus: DEPLOY_RESERVE, SHORT_TURN, HOLD_AT_TERMINAL, REROUTE_AROUND_INCIDENT
  Train: ADD_TRAINS, HOLD_HEADWAY
  Advisory: TRAVEL_ADVISORY (off-peak only)
  Escalation: ESCALATE_TO_OPERATOR
"""
from typing import Dict, Any, List
from ..models import (
    CityState, BUS_TARGET_LF, MRT_TARGET_LF, CROWDING_CRITICAL, PEAK_HOURS,
)


class CapacityPlannerAgent:
    """Plans capacity adjustments using forecast + observations.
    Cost-aware: avoids over-deploying when forecast shows demand easing."""

    def propose(self, city: CityState, observations: Dict[str, Any],
                forecast: Dict[str, Any] = None) -> Dict[str, Any]:
        """Generate proposals for districts (bus) and train lines."""
        district_proposals = []
        reasoning = []
        escalations = []

        hour = city.hour_of_day
        is_peak = hour in PEAK_HOURS
        forecast_districts = forecast.get("districts", {}) if forecast else {}
        forecast_lines = forecast.get("train_lines", {}) if forecast else {}
        forecast_alerts = forecast.get("alerts", []) if forecast else []

        # Check for active road incidents
        road_incident_districts = set()
        for event in city.active_events:
            if event.road_incident:
                road_incident_districts.update(event.districts)

        for district in city.districts:
            obs = observations["districts"][district.name]
            urgency = self._district_urgency(obs)
            fc = forecast_districts.get(district.name, {})
            fc_values = fc.get("forecast", [0, 0, 0])
            fc_peak = max(fc_values) if fc_values else 0

            bus_action = "NO_CHANGE"
            bus_extra = 0
            do_crowd_mgmt = False
            do_advisory = False
            do_short_turn = False
            do_hold_terminal = False
            do_reroute = False
            do_escalate = False

            # --- Proactive: forecast-driven pre-positioning ---
            if fc_peak > 0.85 and obs["bus_load_factor"] <= BUS_TARGET_LF:
                # Demand not yet high but forecast shows overload coming
                bus_action = "DEPLOY_RESERVE"
                bus_extra = min(5, max(1, int((fc_peak - 0.85) * 15)))
                reasoning.append(
                    f"{district.name}: Forecast predicts {fc_peak:.0%} demand at +1-3h — "
                    f"proactively deploying +{bus_extra} reserve units"
                )

            # --- Reactive: current overload ---
            elif obs["bus_load_factor"] > BUS_TARGET_LF:
                if district.name in road_incident_districts:
                    do_reroute = True
                    bus_action = "DEPLOY_RESERVE"
                    bus_extra = min(8, max(1, int((obs["bus_load_factor"] - BUS_TARGET_LF) * 20)))
                    reasoning.append(
                        f"{district.name}: Road incident active — rerouting buses "
                        f"and deploying +{bus_extra} reserve units"
                    )
                elif obs["road_traffic"] > 0.8:
                    do_short_turn = True
                    bus_action = "SHORT_TURN"
                    reasoning.append(
                        f"{district.name}: High traffic ({obs['road_traffic']:.0%}) — "
                        f"short-turning routes to increase frequency on congested segment"
                    )
                else:
                    bus_action = "DEPLOY_RESERVE"
                    overload = obs["bus_load_factor"] - BUS_TARGET_LF
                    bus_extra = min(10, max(1, int(overload * 20)))
                    reasoning.append(
                        f"{district.name}: Bus load {obs['bus_load_factor']:.0%} exceeds target — "
                        f"deploying +{bus_extra} reserve bus units"
                    )

            # Cost-aware: if forecast shows demand easing, hold reserves
            elif fc_values and fc_values[0] < 0.4 and obs["bus_load_factor"] < 0.4:
                reasoning.append(
                    f"{district.name}: Low demand ({obs['bus_load_factor']:.0%}), "
                    f"forecast confirms easing — holding reserve to reduce cost"
                )

            # Headway hold to reduce bunching
            if obs["bus_load_factor"] > 0.7 and obs["bus_load_factor"] <= BUS_TARGET_LF:
                do_hold_terminal = True
                reasoning.append(
                    f"{district.name}: Moderate load ({obs['bus_load_factor']:.0%}) — "
                    f"holding headway at terminal to prevent bunching"
                )

            # Station crowd management
            if obs["station_crowding"] > CROWDING_CRITICAL:
                do_crowd_mgmt = True
                reasoning.append(
                    f"{district.name}: Station crowding critical ({obs['station_crowding']:.0%}) — "
                    f"crowd management activated"
                )

            # Escalation for severe situations
            if obs["station_crowding"] > 0.95 and obs["bus_load_factor"] > 0.95:
                do_escalate = True
                escalations.append({
                    "district": district.name,
                    "reason": f"Severe overload: crowding {obs['station_crowding']:.0%}, "
                              f"bus load {obs['bus_load_factor']:.0%}",
                    "hour": hour,
                })
                reasoning.append(
                    f"{district.name}: ESCALATING TO OPERATOR — severe overload beyond agent capacity"
                )

            # Travel advisory (only off-peak, only if forecast shows overload)
            if not is_peak and not obs.get("nudges_active", False):
                if (obs["station_crowding"] > 0.7 or obs["road_traffic"] > 0.75) and fc_peak > 0.75:
                    do_advisory = True
                    reasoning.append(
                        f"{district.name}: Off-peak travel advisory — "
                        f"alternative routes recommended (forecast: {fc_peak:.0%})"
                    )

            district_proposals.append({
                "district": district.name,
                "bus_action": bus_action,
                "bus_extra": bus_extra,
                "do_crowd_mgmt": do_crowd_mgmt,
                "do_advisory": do_advisory,
                "do_short_turn": do_short_turn,
                "do_hold_terminal": do_hold_terminal,
                "do_reroute": do_reroute,
                "do_escalate": do_escalate,
                "urgency": urgency,
            })

        # Train line proposals
        train_proposals = []
        for line_id, line_obs in observations.get("train_lines", {}).items():
            urgency = self._train_urgency(line_obs)
            fc = forecast_lines.get(line_id, {})
            fc_values = fc.get("forecast", [0, 0, 0])
            fc_peak = max(fc_values) if fc_values else 0

            mrt_action = "NO_CHANGE"
            mrt_extra = 0
            do_hold_headway = False
            do_escalate_line = False

            # Proactive: forecast shows overload in 1-3h
            if fc_peak > 0.80 and line_obs["line_load"] <= MRT_TARGET_LF:
                mrt_action = "ADD_TRAINS"
                mrt_extra = min(2, max(1, int((fc_peak - 0.80) * 8)))
                reasoning.append(
                    f"{line_id}: Forecast predicts {fc_peak:.0%} load at +1-3h — "
                    f"proactively adding +{mrt_extra} trains"
                )

            # Reactive: current overload
            elif line_obs["line_load"] > MRT_TARGET_LF:
                mrt_action = "ADD_TRAINS"
                overload = line_obs["line_load"] - MRT_TARGET_LF
                mrt_extra = min(3, max(1, int(overload * 10)))
                reasoning.append(
                    f"{line_id}: Load {line_obs['line_load']:.0%} exceeds threshold — "
                    f"requesting +{mrt_extra} train service units"
                )

            elif line_obs["line_load"] < 0.3:
                reasoning.append(
                    f"{line_id}: Low demand ({line_obs['line_load']:.0%}) — "
                    f"scale-down appropriate, saving cost"
                )

            # Headway hold for moderate load
            if line_obs["line_load"] > 0.6 and line_obs["line_load"] <= MRT_TARGET_LF:
                do_hold_headway = True
                reasoning.append(
                    f"{line_id}: Moderate load — holding headway to maintain spacing"
                )

            # Severe disruption: escalate
            if line_obs["disruption_level"] > 0.5:
                do_escalate_line = True
                escalations.append({
                    "line_id": line_id,
                    "reason": f"Severe disruption: {line_obs['disruption_level']:.0%}",
                    "hour": hour,
                })
                reasoning.append(
                    f"{line_id}: ESCALATING TO OPERATOR — disruption level "
                    f"{line_obs['disruption_level']:.0%} exceeds threshold"
                )

            train_proposals.append({
                "line_id": line_id,
                "mrt_action": mrt_action,
                "mrt_extra": mrt_extra,
                "do_hold_headway": do_hold_headway,
                "do_escalate": do_escalate_line,
                "urgency": urgency,
            })

        # Include forecast alerts in reasoning
        for alert in forecast_alerts:
            reasoning.append(f"[Forecast] {alert}")

        return {
            "district_proposals": district_proposals,
            "train_proposals": train_proposals,
            "reasoning": reasoning,
            "escalations": escalations,
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
