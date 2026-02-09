"""
Environment dynamics for MetroMind v2 city simulation.
Includes demand patterns, weather effects, train line dynamics, emissions,
and operating cost calculations.
"""
import math
import random
from .models import (
    CityState, DistrictState, TrainLineState,
    CAPACITY_DECAY_RATE, BUS_EMISSIONS, MRT_EMISSIONS,
    TRAFFIC_EMISSIONS_FACTOR,
    COST_BUS_ACTIVE, COST_TRAIN_ACTIVE, COST_RESERVE_IDLE,
    COST_CROWDING_PENALTY, COST_DELAY_PENALTY, CROWDING_CRITICAL,
)


class MobilityEnvironment:
    """Simulates urban mobility dynamics with weather, train lines, costs."""

    def step(self, city: CityState) -> dict:
        """Advance the simulation by one time step."""
        step_summary = {
            "events_triggered": [],
            "events_ended": [],
            "emissions": 0,
            "cost_this_hour": 0,
        }

        # Reset hourly tracking
        city.hourly_emissions = 0
        city.cost_this_hour = 0

        # 1. Update weather
        city.update_weather()

        # 2. Potentially trigger random events
        new_event = city.trigger_random_event()
        if new_event:
            step_summary["events_triggered"].append(new_event.to_dict())

        # 3. Update active events and district demand multipliers
        city.update_events()

        # 4. Compute base demand wave
        demand_wave = self._compute_demand_wave(city.hour_of_day)

        # 5. Weather modifiers
        weather_traffic_mod = 0.0
        weather_crowding_mod = 0.0
        weather_bus_penalty = 0.0
        weather_air_penalty = 0.0
        weather_disruption_boost = 0.0

        w = city.weather
        if w.condition == "Light Rain":
            weather_traffic_mod = 0.05 * w.intensity
            weather_crowding_mod = 0.03 * w.intensity
            weather_bus_penalty = 0.02 * w.intensity
        elif w.condition == "Heavy Rain":
            weather_traffic_mod = 0.12 * w.intensity
            weather_crowding_mod = 0.08 * w.intensity
            weather_bus_penalty = 0.06 * w.intensity
        elif w.condition == "Thunderstorm":
            weather_traffic_mod = 0.15 * w.intensity
            weather_crowding_mod = 0.10 * w.intensity
            weather_bus_penalty = 0.08 * w.intensity
            weather_disruption_boost = 0.15 * w.intensity
        elif w.condition == "Haze":
            weather_air_penalty = 15 * w.intensity

        # Check for road incidents affecting specific districts
        road_incident_districts = set()
        for event in city.active_events:
            if event.road_incident:
                road_incident_districts.update(event.districts)

        # 6. Process each district
        for district in city.districts:
            road_incident = district.name in road_incident_districts
            self._process_district(district, demand_wave,
                                   weather_traffic_mod, weather_crowding_mod,
                                   weather_bus_penalty, weather_air_penalty,
                                   road_incident)

        # 7. Process train lines
        self._process_train_lines(city, demand_wave, weather_disruption_boost,
                                  weather_crowding_mod)

        # 8. Calculate emissions
        self._calculate_emissions(city)
        step_summary["emissions"] = city.hourly_emissions

        # 9. Calculate operating cost
        self._calculate_cost(city)
        step_summary["cost_this_hour"] = city.cost_this_hour

        # 10. Decay capacity back toward baseline
        self._decay_capacity(city)

        # 11. Update sustainability score
        self._update_sustainability(city)

        # 12. Advance time
        city.t += 1
        city.hour_of_day = city.t % 24
        city.day_index = city.t // 24 + 1

        # Reset daily cost at midnight (new day starts fresh)
        if city.hour_of_day == 0:
            city.cost_today = 0

        return step_summary

    def _process_district(self, district: DistrictState, demand_wave: float,
                          weather_traffic_mod: float, weather_crowding_mod: float,
                          weather_bus_penalty: float, weather_air_penalty: float,
                          road_incident: bool = False):
        """Process one district's dynamics for one step."""
        # Handle nudge decay (now called advisory)
        if district.nudges_active:
            district.nudge_timer -= 1
            if district.nudge_timer <= 0:
                district.nudges_active = False
                district.nudge_timer = 0

        nudge_reduction = 0.03 if district.nudges_active else 0.0
        effective_demand = demand_wave * district.event_demand_mult

        # Road incident increases traffic significantly
        road_incident_traffic = 0.15 if road_incident else 0.0

        # Bus load
        base_bus_demand = effective_demand * 0.85 + 0.05 - nudge_reduction + weather_bus_penalty
        target_bus_load = base_bus_demand * (90 / max(district.bus_capacity, 1))
        district.bus_load_factor = self._smooth(district.bus_load_factor, target_bus_load, 0.4)
        district.bus_load_factor = max(0.02, min(1.2, district.bus_load_factor))

        # MRT load
        base_mrt_demand = effective_demand * 0.80 + 0.05 - nudge_reduction
        target_mrt_load = base_mrt_demand * (40 / max(district.mrt_capacity, 1))
        district.mrt_load_factor = self._smooth(district.mrt_load_factor, target_mrt_load, 0.4)
        district.mrt_load_factor = max(0.02, min(1.2, district.mrt_load_factor))

        # Station crowding (weather drives more people to PT)
        target_crowding = (0.5 * district.mrt_load_factor +
                           0.4 * effective_demand + weather_crowding_mod)
        district.station_crowding = self._smooth(district.station_crowding, target_crowding, 0.35)
        district.station_crowding = max(0.0, min(1.0, district.station_crowding))

        # Road traffic
        transit_spillover = max(0, district.bus_load_factor - 0.9) * 0.5
        base_traffic = (0.08 + 0.5 * effective_demand + transit_spillover +
                        weather_traffic_mod + road_incident_traffic)
        district.road_traffic = self._smooth(district.road_traffic, base_traffic, 0.3)
        district.road_traffic = max(0.05, min(1.0, district.road_traffic))

        # Air quality
        target_air = 90 - 40 * district.road_traffic - weather_air_penalty
        district.air_quality = self._smooth(district.air_quality, target_air, 0.15)
        district.air_quality = max(20, min(100, district.air_quality))

    def _process_train_lines(self, city: CityState, demand_wave: float,
                             disruption_boost: float, crowding_mod: float):
        """Process each train line's dynamics."""
        for line_id, line in city.train_lines.items():
            # Base load from demand wave
            target_load = demand_wave * 0.85 + 0.05

            # Event disruptions on specific lines
            for event in city.active_events:
                if line_id in event.affected_lines:
                    if event.reduces_mrt:
                        target_load *= 1.2  # more crowded if service reduced
                        line.disruption_level = min(1.0, line.disruption_level + 0.3)

            # Weather disruption
            if disruption_boost > 0:
                if random.random() < disruption_boost * 0.3:
                    line.disruption_level = min(1.0, line.disruption_level + 0.1)

            # Disruption increases load (fewer trains running)
            target_load *= (1 + line.disruption_level * 0.3)

            # Frequency effect: more trains = lower load per train
            freq_ratio = line.base_frequency / max(line.frequency, 1)
            target_load *= freq_ratio

            # Weather pushes more people to trains
            target_load += crowding_mod * 0.5

            # Smooth update
            line.line_load = self._smooth(line.line_load, target_load, 0.4)
            line.line_load = max(0.02, min(1.2, line.line_load))

            # Disruption decays slowly
            line.disruption_level = max(0, line.disruption_level - 0.05)

            # Frequency decay toward baseline
            if line.frequency > line.base_frequency:
                line.frequency = max(line.base_frequency,
                                     line.frequency - max(1, int((line.frequency - line.base_frequency) * CAPACITY_DECAY_RATE)))

    def _calculate_emissions(self, city: CityState):
        """Calculate hourly carbon emissions."""
        total = 0
        for district in city.districts:
            active_buses = district.bus_capacity * district.bus_load_factor
            bus_e = active_buses * BUS_EMISSIONS * 0.01
            traffic_e = district.road_traffic * TRAFFIC_EMISSIONS_FACTOR * 0.1
            total += bus_e + traffic_e

        for line in city.train_lines.values():
            train_e = line.frequency * line.line_load * MRT_EMISSIONS * 0.05
            total += train_e

        city.add_emissions(total)

    def _calculate_cost(self, city: CityState):
        """Calculate hourly operating cost in cost units."""
        cost = 0.0

        # Active bus service cost
        cost += city.bus_service_units_active * COST_BUS_ACTIVE

        # Active train service cost
        cost += city.train_service_units_active * COST_TRAIN_ACTIVE

        # Idle reserve cost (units available but not deployed)
        idle_bus = max(0, city.bus_service_units_max - city.bus_service_units_active)
        idle_train = max(0, city.train_service_units_max - city.train_service_units_active)
        # Only count idle units during operating hours (drivers on standby)
        if city.bus_service_units_active > 0:  # operating hours
            cost += (idle_bus + idle_train) * COST_RESERVE_IDLE

        # Crowding penalty (incidents have safety/brand cost)
        for d in city.districts:
            if d.station_crowding > CROWDING_CRITICAL:
                cost += COST_CROWDING_PENALTY

        # Delay penalty
        for line in city.train_lines.values():
            if line.disruption_level > 0.3:
                cost += COST_DELAY_PENALTY

        city.cost_this_hour = round(cost, 1)
        city.cost_today += city.cost_this_hour
        city.cost_history.append(city.cost_this_hour)
        # Keep only last 50 entries
        if len(city.cost_history) > 50:
            city.cost_history = city.cost_history[-50:]

    def _decay_capacity(self, city: CityState):
        """Decay added capacity back toward baseline."""
        for district in city.districts:
            if district.bus_capacity > district.base_bus_capacity:
                decay = (district.bus_capacity - district.base_bus_capacity) * CAPACITY_DECAY_RATE
                district.bus_capacity = max(
                    district.base_bus_capacity,
                    int(district.bus_capacity - max(1, decay))
                )
            if district.mrt_capacity > district.base_mrt_capacity:
                decay = (district.mrt_capacity - district.base_mrt_capacity) * CAPACITY_DECAY_RATE
                district.mrt_capacity = max(
                    district.base_mrt_capacity,
                    int(district.mrt_capacity - max(1, decay))
                )

    def _update_sustainability(self, city: CityState):
        """Update long-term sustainability score."""
        if city.hourly_emissions < 50:
            city.sustainability_score = min(100, city.sustainability_score + 0.1)
        elif city.hourly_emissions > 150:
            city.sustainability_score = max(0, city.sustainability_score - 0.2)

    def _compute_demand_wave(self, hour: int) -> float:
        """Compute demand multiplier based on hour of day (0-23)."""
        if hour >= 1 and hour < 5:
            return 0.02
        elif hour == 0:
            return 0.08
        elif hour == 5:
            return 0.15

        morning_rush = math.exp(-((hour - 8) ** 2) / 4)
        evening_rush = math.exp(-((hour - 18) ** 2) / 4)
        midday = 0.4 if 10 <= hour <= 16 else 0.0
        late_decline = max(0, 0.3 - 0.1 * (hour - 21)) if hour >= 21 else 0.0

        base = max(morning_rush, evening_rush, midday, late_decline)
        return min(1.0, base)

    def _smooth(self, current: float, target: float, rate: float) -> float:
        """Smoothly move current value toward target."""
        return current + rate * (target - current)
