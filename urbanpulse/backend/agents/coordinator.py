"""
CoordinatorAgent - Allocates global resource capacities across districts and train lines.
"""
from typing import Dict, Any, List
from ..models import CityState


class CoordinatorAgent:
    """Coordinates resource allocation with limited capacities."""

    def allocate(self, city: CityState, proposals: Dict[str, Any]) -> Dict[str, Any]:
        """Allocate bus_fleet_capacity across districts and train_slot_capacity across lines."""

        # District bus allocation
        sorted_districts = sorted(proposals["district_proposals"],
                                  key=lambda p: p["urgency"], reverse=True)
        bus_left = city.bus_fleet_capacity
        approved_districts = []

        for proposal in sorted_districts:
            approved = proposal.copy()
            if proposal["bus_action"] == "ADD_BUSES" and proposal["bus_extra"] > 0:
                allocated = min(proposal["bus_extra"], bus_left)
                approved["bus_extra"] = allocated
                bus_left -= allocated
                if allocated == 0:
                    approved["bus_action"] = "NO_CHANGE"
            approved_districts.append(approved)

        city.bus_fleet_capacity = bus_left

        # Train line allocation
        sorted_trains = sorted(proposals["train_proposals"],
                               key=lambda p: p["urgency"], reverse=True)
        train_left = city.train_slot_capacity
        approved_trains = []

        for proposal in sorted_trains:
            approved = proposal.copy()
            if proposal["mrt_action"] == "ADD_TRAINS" and proposal["mrt_extra"] > 0:
                allocated = min(proposal["mrt_extra"], train_left)
                approved["mrt_extra"] = allocated
                train_left -= allocated
                if allocated == 0:
                    approved["mrt_action"] = "NO_CHANGE"
            approved_trains.append(approved)

        city.train_slot_capacity = train_left

        return {
            "district_proposals": approved_districts,
            "train_proposals": approved_trains,
        }
