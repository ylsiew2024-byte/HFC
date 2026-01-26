"""
Environment dynamics for the city simulation.
"""
import math
from typing import List
from .models import CityState, DistrictState


class MobilityEnvironment:
    """Simulates urban mobility dynamics."""

    def step(self, city: CityState) -> None:
        """
        Advance the simulation by one time step.
        Updates demand, traffic, air quality based on current state.
        """
        # Simulate demand waves (time-of-day pattern)
        demand_wave = self._compute_demand_wave(city.t)

        for district in city.districts:
            # Handle nudge decay
            if district.nudges_active:
                district.nudge_timer -= 1
                if district.nudge_timer <= 0:
                    district.nudges_active = False
                    district.nudge_timer = 0

            # Nudge effect reduces demand
            nudge_reduction = 0.03 if district.nudges_active else 0.0

            # Update load factors based on demand wave
            # At night (demand_wave ~0), loads should be very low
            # At peak (demand_wave ~1), loads can reach capacity
            base_bus_demand = demand_wave * 0.85 + 0.05 - nudge_reduction
            base_mrt_demand = demand_wave * 0.80 + 0.05 - nudge_reduction

            # Load factors move toward demand, adjusted by capacity utilization
            target_bus_load = base_bus_demand * (90 / max(district.bus_capacity, 1))
            target_mrt_load = base_mrt_demand * (40 / max(district.mrt_capacity, 1))

            district.bus_load_factor = self._smooth_update(
                district.bus_load_factor,
                target_bus_load,
                0.4  # Faster response
            )
            district.mrt_load_factor = self._smooth_update(
                district.mrt_load_factor,
                target_mrt_load,
                0.4
            )

            # Clamp load factors (can go to near-zero at night)
            district.bus_load_factor = max(0.02, min(1.2, district.bus_load_factor))
            district.mrt_load_factor = max(0.02, min(1.2, district.mrt_load_factor))

            # Station crowding correlates with MRT load and demand
            # Very low at night when stations are empty/closed
            target_crowding = 0.5 * district.mrt_load_factor + 0.4 * demand_wave
            district.station_crowding = self._smooth_update(
                district.station_crowding,
                target_crowding,
                0.35
            )
            district.station_crowding = max(0.0, min(1.0, district.station_crowding))

            # Road traffic - still some cars at night, but much less
            transit_spillover = max(0, district.bus_load_factor - 0.9) * 0.5
            base_traffic = 0.08 + 0.5 * demand_wave + transit_spillover  # Minimum 8% even at night
            district.road_traffic = self._smooth_update(
                district.road_traffic,
                base_traffic,
                0.3
            )
            district.road_traffic = max(0.05, min(1.0, district.road_traffic))

            # Air quality inversely related to traffic
            target_air = 90 - 40 * district.road_traffic
            district.air_quality = self._smooth_update(
                district.air_quality,
                target_air,
                0.15
            )
            district.air_quality = max(20, min(100, district.air_quality))

        # Increment time step
        city.t += 1

    def _compute_demand_wave(self, t: int) -> float:
        """
        Compute demand multiplier based on time of day.
        Based on Singapore MRT/bus operating hours (~5:30 AM to ~midnight).
        """
        hour = t % 24

        # Singapore transit: closed roughly 1 AM - 5 AM
        # Night service ends ~midnight, starts ~5:30 AM
        if hour >= 1 and hour < 5:
            # Transit closed - minimal activity (only night owls, taxis)
            return 0.02
        elif hour == 0 or hour == 24:
            # Just after midnight - winding down
            return 0.08
        elif hour == 5:
            # Early morning - services starting
            return 0.15

        # Morning rush: peak at hour 8 (7-9 AM intense)
        morning_rush = math.exp(-((hour - 8) ** 2) / 4)
        # Evening rush: peak at hour 18 (5-7 PM intense)
        evening_rush = math.exp(-((hour - 18) ** 2) / 4)
        # Midday baseline activity
        midday = 0.4 if 10 <= hour <= 16 else 0.0
        # Late evening decline (after 9 PM)
        late_decline = max(0, 0.3 - 0.1 * (hour - 21)) if hour >= 21 else 0.0

        base = max(morning_rush, evening_rush, midday, late_decline)

        # Scale to realistic range [0, 1]
        return min(1.0, base)

    def _smooth_update(self, current: float, target: float, rate: float) -> float:
        """Smoothly move current value toward target."""
        return current + rate * (target - current)
