"""
Environment dynamics for the MetroMind city simulation.
Includes demand patterns, capacity decay, emissions, and economics.
"""
import math
from .models import (
    CityState, DistrictState,
    CAPACITY_DECAY_RATE, BUS_EMISSIONS, MRT_EMISSIONS,
    TRAFFIC_EMISSIONS_FACTOR, HOURLY_REVENUE,
    LIVEABILITY_PENALTY_RATE, ENVIRONMENT_PENALTY_RATE, PENALTY_THRESHOLD
)


class MobilityEnvironment:
    """Simulates urban mobility dynamics with economic and environmental factors."""

    def step(self, city: CityState) -> dict:
        """
        Advance the simulation by one time step.
        Returns a summary of what happened this step.
        """
        step_summary = {
            "events_triggered": [],
            "events_ended": [],
            "emissions": 0,
            "costs": 0,
            "revenue": 0,
        }

        # Reset hourly tracking
        city.hourly_cost = 0
        city.hourly_revenue = 0
        city.hourly_emissions = 0

        # 1. Potentially trigger random events
        new_event = city.trigger_random_event()
        if new_event:
            step_summary["events_triggered"].append(new_event.to_dict())

        # 2. Update active events and district demand multipliers
        city.update_events()

        # 3. Compute base demand wave
        demand_wave = self._compute_demand_wave(city.t)

        # 4. Process each district
        for district in self.districts_step(city, demand_wave):
            pass  # Generator processes districts

        # 5. Calculate emissions from current operations
        self._calculate_emissions(city)
        step_summary["emissions"] = city.hourly_emissions

        # 6. Calculate economics (revenue and penalties)
        self._calculate_economics(city)
        step_summary["costs"] = city.hourly_cost
        step_summary["revenue"] = city.hourly_revenue

        # 7. Decay capacity back toward baseline
        self._decay_capacity(city)

        # 8. Update sustainability score
        self._update_sustainability(city)

        # Increment time step
        city.t += 1

        return step_summary

    def districts_step(self, city: CityState, demand_wave: float):
        """Process each district's dynamics."""
        for district in city.districts:
            # Handle nudge decay
            if district.nudges_active:
                district.nudge_timer -= 1
                if district.nudge_timer <= 0:
                    district.nudges_active = False
                    district.nudge_timer = 0

            # Nudge effect reduces demand
            nudge_reduction = 0.03 if district.nudges_active else 0.0

            # Apply event demand multiplier
            effective_demand = demand_wave * district.event_demand_mult

            # Update load factors based on demand
            base_bus_demand = effective_demand * 0.85 + 0.05 - nudge_reduction
            base_mrt_demand = effective_demand * 0.80 + 0.05 - nudge_reduction

            # Load factors adjusted by capacity
            target_bus_load = base_bus_demand * (90 / max(district.bus_capacity, 1))
            target_mrt_load = base_mrt_demand * (40 / max(district.mrt_capacity, 1))

            district.bus_load_factor = self._smooth_update(
                district.bus_load_factor, target_bus_load, 0.4
            )
            district.mrt_load_factor = self._smooth_update(
                district.mrt_load_factor, target_mrt_load, 0.4
            )

            # Clamp load factors
            district.bus_load_factor = max(0.02, min(1.2, district.bus_load_factor))
            district.mrt_load_factor = max(0.02, min(1.2, district.mrt_load_factor))

            # Station crowding
            target_crowding = (0.5 * district.mrt_load_factor +
                             0.4 * effective_demand)
            district.station_crowding = self._smooth_update(
                district.station_crowding, target_crowding, 0.35
            )
            district.station_crowding = max(0.0, min(1.0, district.station_crowding))

            # Road traffic
            transit_spillover = max(0, district.bus_load_factor - 0.9) * 0.5
            base_traffic = 0.08 + 0.5 * effective_demand + transit_spillover
            district.road_traffic = self._smooth_update(
                district.road_traffic, base_traffic, 0.3
            )
            district.road_traffic = max(0.05, min(1.0, district.road_traffic))

            # Air quality (inversely related to traffic and emissions)
            target_air = 90 - 40 * district.road_traffic
            district.air_quality = self._smooth_update(
                district.air_quality, target_air, 0.15
            )
            district.air_quality = max(20, min(100, district.air_quality))

            yield district

    def _calculate_emissions(self, city: CityState):
        """Calculate hourly carbon emissions from transit operations."""
        total_emissions = 0

        for district in city.districts:
            # Bus emissions (based on number of active buses)
            active_buses = district.bus_capacity * district.bus_load_factor
            bus_emissions = active_buses * BUS_EMISSIONS * 0.01  # Scale down

            # MRT emissions (cleaner but still some)
            active_trains = district.mrt_capacity * district.mrt_load_factor
            mrt_emissions = active_trains * MRT_EMISSIONS * 0.01

            # Traffic emissions (cars on the road)
            traffic_emissions = district.road_traffic * TRAFFIC_EMISSIONS_FACTOR * 0.1

            total_emissions += bus_emissions + mrt_emissions + traffic_emissions

        city.add_emissions(total_emissions)

    def _calculate_economics(self, city: CityState):
        """Calculate hourly revenue and penalty costs."""
        from .kpi import score

        # Base hourly revenue (scales with time of day)
        hour = city.t % 24
        revenue_mult = 1.0
        if 7 <= hour <= 9 or 17 <= hour <= 19:
            revenue_mult = 1.5  # More fare revenue during rush
        elif 1 <= hour <= 5:
            revenue_mult = 0.2  # Almost no revenue at night

        city.add_funds(HOURLY_REVENUE * revenue_mult, "hourly_revenue")

        # Calculate penalties for poor scores
        scores = score(city)
        liveability = scores["liveability_score"]
        environment = scores["environment_score"]

        if liveability < PENALTY_THRESHOLD:
            penalty = (PENALTY_THRESHOLD - liveability) * LIVEABILITY_PENALTY_RATE
            city.deduct_funds(penalty, "liveability_penalty")

        if environment < PENALTY_THRESHOLD:
            penalty = (PENALTY_THRESHOLD - environment) * ENVIRONMENT_PENALTY_RATE
            city.deduct_funds(penalty, "environment_penalty")

    def _decay_capacity(self, city: CityState):
        """Decay added capacity back toward baseline over time."""
        for district in city.districts:
            # Bus capacity decay
            if district.bus_capacity > district.base_bus_capacity:
                decay = (district.bus_capacity - district.base_bus_capacity) * CAPACITY_DECAY_RATE
                district.bus_capacity = max(
                    district.base_bus_capacity,
                    int(district.bus_capacity - max(1, decay))
                )

            # MRT capacity decay
            if district.mrt_capacity > district.base_mrt_capacity:
                decay = (district.mrt_capacity - district.base_mrt_capacity) * CAPACITY_DECAY_RATE
                district.mrt_capacity = max(
                    district.base_mrt_capacity,
                    int(district.mrt_capacity - max(1, decay))
                )

    def _update_sustainability(self, city: CityState):
        """Update long-term sustainability score."""
        # Sustainability slowly recovers if emissions are low
        if city.hourly_emissions < 50:
            city.sustainability_score = min(100, city.sustainability_score + 0.1)
        elif city.hourly_emissions > 150:
            city.sustainability_score = max(0, city.sustainability_score - 0.2)

    def _compute_demand_wave(self, t: int) -> float:
        """
        Compute demand multiplier based on time of day.
        Based on Singapore MRT/bus operating hours (~5:30 AM to ~midnight).
        """
        hour = t % 24

        # Singapore transit: closed roughly 1 AM - 5 AM
        if hour >= 1 and hour < 5:
            return 0.02
        elif hour == 0:
            return 0.08
        elif hour == 5:
            return 0.15

        # Morning rush: peak at hour 8
        morning_rush = math.exp(-((hour - 8) ** 2) / 4)
        # Evening rush: peak at hour 18
        evening_rush = math.exp(-((hour - 18) ** 2) / 4)
        # Midday baseline
        midday = 0.4 if 10 <= hour <= 16 else 0.0
        # Late evening decline
        late_decline = max(0, 0.3 - 0.1 * (hour - 21)) if hour >= 21 else 0.0

        base = max(morning_rush, evening_rush, midday, late_decline)
        return min(1.0, base)

    def _smooth_update(self, current: float, target: float, rate: float) -> float:
        """Smoothly move current value toward target."""
        return current + rate * (target - current)
