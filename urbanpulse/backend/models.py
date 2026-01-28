"""
Data models for MetroMind city simulation.
No monetary system - uses resource capacity constraints only.
Includes weather, train lines, and district state.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import random


# === Constants ===
BUS_TARGET_LF = 0.85
MRT_TARGET_LF = 0.80
CROWDING_CRITICAL = 0.9
TRAFFIC_BUS_ADD_LIMIT = 0.8
BUS_MAX_EXTRA = 10
MRT_MAX_EXTRA = 3

# Capacity decay rate (% per hour back to baseline)
CAPACITY_DECAY_RATE = 0.05

# Emissions (kg CO2 per unit per hour)
BUS_EMISSIONS = 50
MRT_EMISSIONS = 10
TRAFFIC_EMISSIONS_FACTOR = 100

# Weather types
WEATHER_TYPES = ["Clear", "Light Rain", "Heavy Rain", "Thunderstorm", "Haze"]

# Train line definitions
TRAIN_LINE_DEFS = {
    "CCL": {"name": "Circle Line", "color": "#ed8936", "base_freq": 12, "base_load": 0.3},
    "NEL": {"name": "North East Line", "color": "#9f7aea", "base_freq": 10, "base_load": 0.3},
    "EWL": {"name": "East West Line", "color": "#48bb78", "base_freq": 14, "base_load": 0.3},
    "NSL": {"name": "North South Line", "color": "#e53e3e", "base_freq": 14, "base_load": 0.3},
}

# === Event Types ===
EVENTS = [
    {"id": "rush_hour_surge", "name": "Rush Hour Surge", "icon": "\U0001f6a6",
     "districts": ["Central"], "demand_mult": 1.3, "duration": 2},
    {"id": "concert_marina", "name": "Concert at Marina Bay", "icon": "\U0001f3b5",
     "districts": ["Central", "South"], "demand_mult": 1.4, "duration": 3},
    {"id": "airport_rush", "name": "Changi Airport Rush", "icon": "\u2708\ufe0f",
     "districts": ["East"], "demand_mult": 1.5, "duration": 2},
    {"id": "jurong_event", "name": "Jurong Industrial Event", "icon": "\U0001f3ed",
     "districts": ["West"], "demand_mult": 1.35, "duration": 2},
    {"id": "weekend_sentosa", "name": "Sentosa Weekend Crowd", "icon": "\U0001f3dd\ufe0f",
     "districts": ["South"], "demand_mult": 1.4, "duration": 3},
    {"id": "mrt_maintenance", "name": "MRT Line Maintenance", "icon": "\U0001f527",
     "districts": ["North", "Central"], "demand_mult": 1.2, "duration": 2,
     "reduces_mrt": True, "affected_lines": ["NSL"]},
]


@dataclass
class ActiveEvent:
    """An active event affecting the city."""
    event_id: str
    name: str
    icon: str
    districts: List[str]
    demand_mult: float
    remaining_hours: int
    reduces_mrt: bool = False
    affected_lines: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "name": self.name,
            "icon": self.icon,
            "districts": self.districts,
            "demand_mult": self.demand_mult,
            "remaining_hours": self.remaining_hours,
            "affected_lines": self.affected_lines,
        }


@dataclass
class WeatherState:
    """Current weather condition."""
    condition: str = "Clear"
    intensity: float = 0.0        # 0..1
    affected_regions: List[str] = field(default_factory=lambda: ["Islandwide"])
    persistence_hours: int = 0    # hours remaining for this weather

    def to_dict(self) -> Dict[str, Any]:
        return {
            "condition": self.condition,
            "intensity": round(self.intensity, 2),
            "affected_regions": self.affected_regions,
            "persistence_hours": self.persistence_hours,
        }


@dataclass
class TrainLineState:
    """State of a single MRT line."""
    line_id: str
    line_name: str
    color: str
    line_load: float = 0.3       # 0..1
    frequency: int = 12          # trains per hour
    base_frequency: int = 12
    disruption_level: float = 0.0  # 0..1
    actions_this_hour: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "line_id": self.line_id,
            "line_name": self.line_name,
            "color": self.color,
            "line_load": round(self.line_load, 3),
            "frequency": self.frequency,
            "base_frequency": self.base_frequency,
            "disruption_level": round(self.disruption_level, 3),
            "actions_this_hour": self.actions_this_hour,
        }


@dataclass
class DistrictState:
    """State of a single district (bus-focused)."""
    name: str
    population: int
    bus_capacity: int
    mrt_capacity: int
    base_bus_capacity: int
    base_mrt_capacity: int
    bus_load_factor: float
    mrt_load_factor: float
    station_crowding: float
    road_traffic: float
    air_quality: float
    nudges_active: bool = False
    nudge_timer: int = 0
    event_demand_mult: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "population": self.population,
            "bus_capacity": self.bus_capacity,
            "mrt_capacity": self.mrt_capacity,
            "base_bus_capacity": self.base_bus_capacity,
            "base_mrt_capacity": self.base_mrt_capacity,
            "bus_load_factor": round(self.bus_load_factor, 3),
            "mrt_load_factor": round(self.mrt_load_factor, 3),
            "station_crowding": round(self.station_crowding, 3),
            "road_traffic": round(self.road_traffic, 3),
            "air_quality": round(self.air_quality, 1),
            "nudges_active": self.nudges_active,
            "event_demand_mult": round(self.event_demand_mult, 2),
        }


@dataclass
class CityState:
    """State of the entire city. No monetary tracking."""
    districts: List[DistrictState]
    train_lines: Dict[str, TrainLineState] = field(default_factory=dict)
    t: int = 0                              # absolute time step (hours elapsed)
    hour_of_day: int = 0                    # 0-23
    day_index: int = 1                      # day number

    # Service unit capacity constraints
    bus_service_units_max: int = 50         # max bus service units available
    bus_service_units_active: int = 0       # currently deployed bus service units
    train_service_units_max: int = 20       # max train service units available
    train_service_units_active: int = 0     # currently deployed train service units

    # Environmental tracking
    carbon_emissions: float = 0.0
    hourly_emissions: float = 0.0
    sustainability_score: float = 100.0

    # Weather
    weather: WeatherState = field(default_factory=WeatherState)

    # Events
    active_events: List[ActiveEvent] = field(default_factory=list)
    event_log: List[Dict[str, Any]] = field(default_factory=list)

    # Action logs and history
    action_log: List[Dict[str, Any]] = field(default_factory=list)
    history: List[Dict[str, Any]] = field(default_factory=list)

    def reset_capacities(self):
        """Clear per-hour train line actions at the start of each step."""
        for line in self.train_lines.values():
            line.actions_this_hour = []

    def add_emissions(self, amount: float):
        """Add carbon emissions."""
        self.carbon_emissions += amount
        self.hourly_emissions += amount
        self.sustainability_score = max(0, self.sustainability_score - amount * 0.001)

    def trigger_random_event(self) -> Optional[ActiveEvent]:
        """Potentially trigger a random event."""
        hour = self.hour_of_day

        base_chance = 0.05
        if 7 <= hour <= 9 or 17 <= hour <= 19:
            base_chance = 0.15
        elif 10 <= hour <= 16:
            base_chance = 0.08

        if len(self.active_events) >= 2:
            base_chance *= 0.3

        if random.random() < base_chance:
            event_data = random.choice(EVENTS)
            event = ActiveEvent(
                event_id=event_data["id"],
                name=event_data["name"],
                icon=event_data["icon"],
                districts=event_data["districts"],
                demand_mult=event_data["demand_mult"],
                remaining_hours=event_data["duration"],
                reduces_mrt=event_data.get("reduces_mrt", False),
                affected_lines=event_data.get("affected_lines", []),
            )
            self.active_events.append(event)
            self.event_log.append({
                "t": self.t,
                "hour": self.hour_of_day,
                "type": "event_start",
                "event": event.to_dict(),
            })
            return event
        return None

    def update_events(self):
        """Tick down event timers and remove expired events."""
        expired = []
        for event in self.active_events:
            event.remaining_hours -= 1
            if event.remaining_hours <= 0:
                expired.append(event)
                self.event_log.append({
                    "t": self.t,
                    "type": "event_end",
                    "event_id": event.event_id,
                })
        for event in expired:
            self.active_events.remove(event)

        # Update district demand multipliers
        for district in self.districts:
            district.event_demand_mult = 1.0
            for event in self.active_events:
                if "all" in event.districts or district.name in event.districts:
                    district.event_demand_mult *= event.demand_mult

    def update_weather(self):
        """Evolve weather with persistence and hour-based transitions."""
        w = self.weather
        if w.persistence_hours > 0:
            w.persistence_hours -= 1
            return

        # Decide new weather based on hour and randomness
        hour = self.hour_of_day
        roll = random.random()

        # Afternoon more likely rain (tropical Singapore pattern)
        if 14 <= hour <= 18:
            if roll < 0.15:
                w.condition = "Heavy Rain"
                w.intensity = round(random.uniform(0.6, 0.9), 2)
                w.persistence_hours = random.randint(1, 3)
                w.affected_regions = random.choice([["Islandwide"], ["East"], ["West", "Central"]])
            elif roll < 0.35:
                w.condition = "Light Rain"
                w.intensity = round(random.uniform(0.2, 0.5), 2)
                w.persistence_hours = random.randint(1, 2)
                w.affected_regions = ["Islandwide"]
            elif roll < 0.40:
                w.condition = "Thunderstorm"
                w.intensity = round(random.uniform(0.7, 1.0), 2)
                w.persistence_hours = random.randint(1, 2)
                w.affected_regions = ["Islandwide"]
            else:
                w.condition = "Clear"
                w.intensity = 0.0
                w.persistence_hours = random.randint(1, 4)
                w.affected_regions = ["Islandwide"]
        elif 8 <= hour <= 11:
            # Morning haze possibility
            if roll < 0.08:
                w.condition = "Haze"
                w.intensity = round(random.uniform(0.3, 0.7), 2)
                w.persistence_hours = random.randint(2, 5)
                w.affected_regions = ["Islandwide"]
            elif roll < 0.18:
                w.condition = "Light Rain"
                w.intensity = round(random.uniform(0.2, 0.4), 2)
                w.persistence_hours = random.randint(1, 2)
                w.affected_regions = ["Islandwide"]
            else:
                w.condition = "Clear"
                w.intensity = 0.0
                w.persistence_hours = random.randint(2, 4)
                w.affected_regions = ["Islandwide"]
        else:
            if roll < 0.10:
                w.condition = "Light Rain"
                w.intensity = round(random.uniform(0.1, 0.3), 2)
                w.persistence_hours = random.randint(1, 2)
                w.affected_regions = ["Islandwide"]
            else:
                w.condition = "Clear"
                w.intensity = 0.0
                w.persistence_hours = random.randint(2, 5)
                w.affected_regions = ["Islandwide"]
