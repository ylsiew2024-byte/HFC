"""
CoordinatorAgent - Allocates global budgets across districts.
"""
from typing import Dict, Any, List
from ..models import CityState


class CoordinatorAgent:
    """Coordinates resource allocation across districts with limited budgets."""

    def allocate(
        self,
        city: CityState,
        proposals: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Allocate limited budgets across districts based on urgency.
        Returns list of approved proposals with allocated resources.
        """
        # Sort by urgency descending
        sorted_proposals = sorted(proposals, key=lambda p: p["urgency"], reverse=True)

        bus_left = city.bus_budget
        mrt_left = city.mrt_budget

        approved = []

        for proposal in sorted_proposals:
            approved_proposal = proposal.copy()

            # Allocate buses
            if proposal["bus_action"] == "ADD_BUSES" and proposal["bus_extra"] > 0:
                allocated_buses = min(proposal["bus_extra"], bus_left)
                approved_proposal["bus_extra"] = allocated_buses
                bus_left -= allocated_buses

                # If we couldn't allocate any buses, change action
                if allocated_buses == 0:
                    approved_proposal["bus_action"] = "NO_CHANGE"

            # Allocate MRT
            if proposal["mrt_action"] == "ADD_TRAINS" and proposal["mrt_extra"] > 0:
                allocated_mrt = min(proposal["mrt_extra"], mrt_left)
                approved_proposal["mrt_extra"] = allocated_mrt
                mrt_left -= allocated_mrt

                # If we couldn't allocate any trains, change action
                if allocated_mrt == 0:
                    approved_proposal["mrt_action"] = "NO_CHANGE"

            approved.append(approved_proposal)

        # Update remaining budgets in city state
        city.bus_budget = bus_left
        city.mrt_budget = mrt_left

        return approved
