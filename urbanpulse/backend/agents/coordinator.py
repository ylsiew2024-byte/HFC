"""
CoordinatorAgent - Allocates global resource capacities across districts and train lines.
"""
from typing import Dict, Any, List
from ..models import CityState


class CoordinatorAgent:
    """Coordinates resource allocation with limited capacities."""

    def allocate(self, city: CityState, proposals: Dict[str, Any]) -> Dict[str, Any]:
        """Allocate bus_fleet_capacity across districts and train_slot_capacity across lines."""
        allocations = []

        # Reserve ~20-30% buffer
        bus_available = max(0, city.bus_service_units_active - round(city.bus_service_units_max * 0.2))
        train_available = max(0, city.train_service_units_active - round(city.train_service_units_max * 0.2))

        # District bus allocation
        sorted_districts = sorted(proposals["district_proposals"],
                                  key=lambda p: p["urgency"], reverse=True)
        bus_left = bus_available
        approved_districts = []

        for proposal in sorted_districts:
            approved = proposal.copy()
            if proposal["bus_action"] == "ADD_BUSES" and proposal["bus_extra"] > 0:
                allocated = min(proposal["bus_extra"], bus_left)
                approved["bus_extra"] = allocated
                bus_left -= allocated
                if allocated == 0:
                    approved["bus_action"] = "NO_CHANGE"
                    allocations.append(f"{proposal['district']}: requested +{proposal['bus_extra']} units, denied (reserve limit)")
                elif allocated < proposal["bus_extra"]:
                    allocations.append(f"{proposal['district']}: requested +{proposal['bus_extra']} units, allocated +{allocated} (partial)")
                else:
                    allocations.append(f"{proposal['district']}: allocated +{allocated} bus service units")
            approved_districts.append(approved)

        # Train line allocation
        sorted_trains = sorted(proposals["train_proposals"],
                               key=lambda p: p["urgency"], reverse=True)
        train_left = train_available
        approved_trains = []

        for proposal in sorted_trains:
            approved = proposal.copy()
            if proposal["mrt_action"] == "ADD_TRAINS" and proposal["mrt_extra"] > 0:
                allocated = min(proposal["mrt_extra"], train_left)
                approved["mrt_extra"] = allocated
                train_left -= allocated
                if allocated == 0:
                    approved["mrt_action"] = "NO_CHANGE"
                    allocations.append(f"{proposal['line_id']}: requested +{proposal['mrt_extra']} units, denied (reserve limit)")
                elif allocated < proposal["mrt_extra"]:
                    allocations.append(f"{proposal['line_id']}: requested +{proposal['mrt_extra']} units, allocated +{allocated} (partial)")
                else:
                    allocations.append(f"{proposal['line_id']}: allocated +{allocated} train service units")
            approved_trains.append(approved)

        return {
            "district_proposals": approved_districts,
            "train_proposals": approved_trains,
            "_trace": {
                "allocations": allocations,
                "remaining_capacity": {
                    "bus_service_units": bus_left,
                    "train_service_units": train_left,
                },
            },
        }
