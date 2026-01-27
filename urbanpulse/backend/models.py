"""
Data models for MetroMind city simulation.
Enhanced with budget, emissions, and event systems.
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

# Cost constants (in thousands $)
BUS_COST_PER_UNIT = 0.5      # $500 per bus deployment
MRT_COST_PER_UNIT = 2.0      # $2000 per train deployment
CROWD_MGMT_COST = 1.0        # $1000 per crowd management action
NUDGE_COST = 0.2             # $200 per nudge campaign
HOURLY_REVENUE = 5.0         # $5000 base tax revenue per hour

# Penalty costs per hour
LIVEABILITY_PENALTY_RATE = 1.0   # $1000 per point below 70
ENVIRONMENT_PENALTY_RATE = 0.5   # $500 per point below 70
PENALTY_THRESHOLD = 70

# Emissions (kg CO2 per unit per hour)
BUS_EMISSIONS = 50           # Diesel bus emissions
MRT_EMISSIONS = 10           # Electric train (indirect)
TRAFFIC_EMISSIONS_FACTOR = 100  # Per 10% traffic

# Capacity decay rate (% per hour back to baseline)
CAPACITY_DECAY_RATE = 0.05


# === Event Types ===
EVENTS = [
    {"id": "rush_hour_surge", "name": "Rush Hour Surge", "icon": "🚦",
     "districts": ["Central"], "demand_mult": 1.3, "duration": 2},
    {"id": "concert_marina", "name": "Concert at Marina Bay", "icon": "🎵",
     "districts": ["Central", "South"], "demand_mult": 1.4, "duration": 3},
    {"id": "airport_rush", "name": "Changi Airport Rush", "icon": "✈️",
     "districts": ["East"], "demand_mult": 1.5, "duration": 2},
    {"id": "rain_forecast", "name": "Heavy Rain Expected", "icon": "🌧️",
     "districts": ["all"], "demand_mult": 1.25, "duration": 4, "type": "weather",
     "areas": ["Islandwide"], "impact": "Slower bus speeds, higher congestion"},
    {"id": "jurong_event", "name": "Jurong Industrial Event", "icon": "🏭",
     "districts": ["West"], "demand_mult": 1.35, "duration": 2},
    {"id": "weekend_sentosa", "name": "Sentosa Weekend Crowd", "icon": "🏝️",
     "districts": ["South"], "demand_mult": 1.4, "duration": 3},
    {"id": "mrt_maintenance", "name": "MRT Line Maintenance", "icon": "🔧",
     "districts": ["North", "Central"], "demand_mult": 1.2, "duration": 2,
     "reduces_mrt": True},

    # Additional Weather Events
    {"id": "thunderstorm", "name": "Thunderstorm Warning", "icon": "⛈️", "type": "weather",
     "districts": ["all"], "areas": ["Islandwide"], "demand_mult": 1.3, "duration": 1,
     "impact": "Service delays, seek shelter"},
    {"id": "light_rain", "name": "Light Rain", "icon": "🌦️", "type": "weather",
     "districts": ["North", "South"], "areas": ["Northern/Southern regions"], "demand_mult": 1.1, "duration": 3,
     "impact": "Minor delays expected"},

    # Train Disruptions
    {"id": "ns_line_delay", "name": "NS Line: Service Delay", "icon": "🚨", "type": "train_disruption",
     "line": "North-South Line", "districts": ["North", "Central"], "demand_mult": 1.4, "duration": 2,
     "severity": "medium", "description": "Signaling fault causing delays"},
    {"id": "ew_line_breakdown", "name": "EW Line: Train Breakdown", "icon": "⚠️", "type": "train_disruption",
     "line": "East-West Line", "districts": ["East", "Central"], "demand_mult": 1.6, "duration": 3,
     "severity": "high", "description": "Train fault, service disrupted"},
    {"id": "cc_line_delay", "name": "CC Line: Minor Delay", "icon": "⏰", "type": "train_disruption",
     "line": "Circle Line", "districts": ["Central"], "demand_mult": 1.2, "duration": 1,
     "severity": "low", "description": "Platform door issue"},
    {"id": "dt_line_partial", "name": "DT Line: Partial Closure", "icon": "🚧", "type": "train_disruption",
     "line": "Downtown Line", "districts": ["Central", "North"], "demand_mult": 1.5, "duration": 4,
     "severity": "high", "description": "Track maintenance, partial service"},
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
    event_type: str = "regular"  # regular, weather, train_disruption
    severity: str = None  # low, medium, high (for disruptions)
    line: str = None  # MRT line name (for train disruptions)
    description: str = None  # description of disruption
    areas: List[str] = None  # affected areas (for weather)
    impact: str = None  # impact description (for weather)

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "event_id": self.event_id,
            "name": self.name,
            "icon": self.icon,
            "districts": self.districts,
            "demand_mult": self.demand_mult,
            "remaining_hours": self.remaining_hours,
            "type": self.event_type,
        }
        if self.severity:
            result["severity"] = self.severity
        if self.line:
            result["line"] = self.line
        if self.description:
            result["description"] = self.description
        if self.areas:
            result["areas"] = self.areas
        if self.impact:
            result["impact"] = self.impact
        return result


@dataclass
class DistrictState:
    """State of a single district."""
    name: str
    population: int
    bus_capacity: int           # current buses per hour
    mrt_capacity: int           # current trains per hour
    base_bus_capacity: int      # baseline capacity (for decay)
    base_mrt_capacity: int      # baseline capacity (for decay)
    bus_load_factor: float      # 0-1, ratio of demand to capacity
    mrt_load_factor: float      # 0-1
    station_crowding: float     # 0-1, crowding level at stations
    road_traffic: float         # 0-1, traffic congestion level
    air_quality: float          # 0-100, higher is better
    nudges_active: bool = False
    nudge_timer: int = 0
    event_demand_mult: float = 1.0  # Multiplier from active events

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
    """State of the entire city with economic and environmental tracking."""
    districts: List[DistrictState]
    t: int = 0                              # current time step (hour)
    bus_budget: int = 40                    # buses available this hour
    mrt_budget: int = 12                    # trains available this hour

    # Economic tracking
    funds: float = 1000.0                   # City funds in thousands ($1M start)
    total_revenue: float = 0.0             # Cumulative revenue
    total_costs: float = 0.0               # Cumulative costs
    hourly_cost: float = 0.0               # Cost this hour
    hourly_revenue: float = 0.0            # Revenue this hour

    # Environmental tracking
    carbon_emissions: float = 0.0          # Cumulative CO2 in kg
    hourly_emissions: float = 0.0          # Emissions this hour
    sustainability_score: float = 100.0    # Long-term environmental health

    # Events
    active_events: List[ActiveEvent] = field(default_factory=list)
    event_log: List[Dict[str, Any]] = field(default_factory=list)

    # Action logs and history
    action_log: List[Dict[str, Any]] = field(default_factory=list)
    history: List[Dict[str, Any]] = field(default_factory=list)

    # Initial values for reset
    _initial_bus_budget: int = 40
    _initial_mrt_budget: int = 12

    def to_dict(self) -> Dict[str, Any]:
        return {
            "t": self.t,
            "bus_budget": self.bus_budget,
            "mrt_budget": self.mrt_budget,
            "funds": round(self.funds, 1),
            "carbon_emissions": round(self.carbon_emissions, 1),
            "sustainability_score": round(self.sustainability_score, 1),
            "districts": [d.to_dict() for d in self.districts],
        }

    def reset_budgets(self):
        """Reset budgets at the start of each step."""
        self.bus_budget = self._initial_bus_budget
        self.mrt_budget = self._initial_mrt_budget

    def add_funds(self, amount: float, reason: str = ""):
        """Add funds (revenue)."""
        self.funds += amount
        self.total_revenue += amount
        self.hourly_revenue += amount

    def deduct_funds(self, amount: float, reason: str = "") -> bool:
        """Deduct funds if available. Returns True if successful."""
        if self.funds >= amount:
            self.funds -= amount
            self.total_costs += amount
            self.hourly_cost += amount
            return True
        return False

    def add_emissions(self, amount: float):
        """Add carbon emissions."""
        self.carbon_emissions += amount
        self.hourly_emissions += amount
        # Degrade sustainability based on emissions
        self.sustainability_score = max(0, self.sustainability_score - amount * 0.001)

    def trigger_random_event(self) -> Optional[ActiveEvent]:
        """Potentially trigger a random event. Returns event if triggered."""
        hour = self.t % 24

        # Events more likely during peak hours
        base_chance = 0.05
        if 7 <= hour <= 9 or 17 <= hour <= 19:
            base_chance = 0.15
        elif 10 <= hour <= 16:
            base_chance = 0.08

        # Don't stack too many events
        if len(self.active_events) >= 2:
            base_chance *= 0.3

        if random.random() < base_chance:
            # Pick a random event
            event_data = random.choice(EVENTS)
            event = ActiveEvent(
                event_id=event_data["id"],
                name=event_data["name"],
                icon=event_data["icon"],
                districts=event_data["districts"],
                demand_mult=event_data["demand_mult"],
                remaining_hours=event_data["duration"],
                reduces_mrt=event_data.get("reduces_mrt", False),
                event_type=event_data.get("type", "regular"),
                severity=event_data.get("severity"),
                line=event_data.get("line"),
                description=event_data.get("description"),
                areas=event_data.get("areas"),
                impact=event_data.get("impact"),
            )
            self.active_events.append(event)
            self.event_log.append({
                "t": self.t,
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

        # Update district demand multipliers based on active events
        for district in self.districts:
            district.event_demand_mult = 1.0
            for event in self.active_events:
                if "all" in event.districts or district.name in event.districts:
                    district.event_demand_mult *= event.demand_mult
