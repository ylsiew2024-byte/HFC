"""
Demand forecasting module for MetroMind v2.
Uses lightweight exponential smoothing + hour-of-day patterns
to predict demand 1-3 hours ahead for proactive planning.
No ML libraries required — hackathon-feasible.
"""
import math
import random
from typing import Dict, Any, List
from .models import CityState


# Smoothing parameter for exponential moving average
ALPHA = 0.3

# Hours with no bus/train service — forecast should be zero
NO_SERVICE_HOURS = {1, 2, 3, 4, 5}

# Base demand profile (same shape as env.py demand wave)
def _base_demand(hour: int) -> float:
    if 1 <= hour < 5:
        return 0.02
    if hour == 0:
        return 0.08
    if hour == 5:
        return 0.15
    morning = math.exp(-((hour - 8) ** 2) / 4)
    evening = math.exp(-((hour - 18) ** 2) / 4)
    midday = 0.4 if 10 <= hour <= 16 else 0.0
    late = max(0, 0.3 - 0.1 * (hour - 21)) if hour >= 21 else 0.0
    return min(1.0, max(morning, evening, midday, late))


class DemandForecaster:
    """Predicts district-level bus/MRT demand and line-level train demand
    for the next 1-3 hours using exponential smoothing on observed loads
    combined with known hourly demand patterns."""

    def __init__(self):
        # Tracked smoothed values per district
        self._district_ema: Dict[str, float] = {}
        # Tracked smoothed values per train line
        self._line_ema: Dict[str, float] = {}

    def forecast(self, city: CityState) -> Dict[str, Any]:
        """Generate demand forecast for the next 3 hours.

        Returns:
            {
                "current_hour": int,
                "districts": {
                    "Central": {"forecast": [h+1, h+2, h+3], "confidence": [lo, hi]},
                    ...
                },
                "train_lines": {
                    "NSL": {"forecast": [h+1, h+2, h+3], "confidence": [lo, hi]},
                    ...
                },
                "alerts": ["Central predicted overload at +1h", ...],
            }
        """
        hour = city.hour_of_day
        result = {
            "current_hour": hour,
            "districts": {},
            "train_lines": {},
            "alerts": [],
        }

        # Weather modifier on forecast
        weather_boost = 0.0
        w = city.weather
        if w.condition == "Heavy Rain":
            weather_boost = 0.08
        elif w.condition == "Thunderstorm":
            weather_boost = 0.12
        elif w.condition == "Light Rain":
            weather_boost = 0.03

        # Event modifier: if active events, they persist for forecast window
        event_districts = {}
        for event in city.active_events:
            for d in event.districts:
                event_districts[d] = event_districts.get(d, 1.0) * event.demand_mult

        # District forecasts
        for district in city.districts:
            name = district.name
            # Current observed load (matches map: bus + mrt + station crowding)
            observed = (district.bus_load_factor + district.mrt_load_factor + district.station_crowding) / 3

            # Update EMA
            prev = self._district_ema.get(name, observed)
            ema = ALPHA * observed + (1 - ALPHA) * prev
            self._district_ema[name] = ema

            # Forecast next 3 hours
            forecasts = []
            for offset in range(1, 4):
                future_hour = (hour + offset) % 24
                # No service hours → zero demand
                if future_hour in NO_SERVICE_HOURS:
                    forecasts.append(0.0)
                    continue
                base = _base_demand(future_hour)
                # Blend EMA trend with base pattern
                predicted = 0.6 * base + 0.4 * ema + weather_boost
                # Apply event multiplier if events likely persist
                event_mult = event_districts.get(name, 1.0)
                if offset <= 2:  # events likely still active for +1h, +2h
                    predicted *= event_mult
                predicted = max(0.0, min(1.2, predicted))
                forecasts.append(round(predicted, 3))

            # Confidence bounds (wider for further out)
            peak = max(forecasts)
            lo = round(max(0, peak - 0.12), 3)
            hi = round(min(1.2, peak + 0.12), 3)

            result["districts"][name] = {
                "forecast": forecasts,
                "confidence": [lo, hi],
                "current_load": round(observed, 3),
            }

            # Alert if any forecast hour shows overload
            for i, f in enumerate(forecasts):
                if f > 0.85:
                    result["alerts"].append(
                        f"Forecast: {name} demand {f:.0%} at +{i+1}h — proactive deployment recommended"
                    )
                    break  # one alert per district

        # Train line forecasts
        for line_id, line in city.train_lines.items():
            observed = line.line_load
            prev = self._line_ema.get(line_id, observed)
            ema = ALPHA * observed + (1 - ALPHA) * prev
            self._line_ema[line_id] = ema

            forecasts = []
            for offset in range(1, 4):
                future_hour = (hour + offset) % 24
                # No service hours → zero demand
                if future_hour in NO_SERVICE_HOURS:
                    forecasts.append(0.0)
                    continue
                base = _base_demand(future_hour) * 0.85 + 0.05
                predicted = 0.6 * base + 0.4 * ema + weather_boost * 0.5
                # Disruption boost
                if line.disruption_level > 0.1:
                    predicted *= (1 + line.disruption_level * 0.2)
                predicted = max(0.0, min(1.2, predicted))
                forecasts.append(round(predicted, 3))

            peak = max(forecasts)
            lo = round(max(0, peak - 0.10), 3)
            hi = round(min(1.2, peak + 0.10), 3)

            result["train_lines"][line_id] = {
                "forecast": forecasts,
                "confidence": [lo, hi],
                "current_load": round(observed, 3),
            }

            for i, f in enumerate(forecasts):
                if f > 0.80:
                    result["alerts"].append(
                        f"Forecast: {line.line_name} load {f:.0%} at +{i+1}h — consider adding trains"
                    )
                    break

        return result
