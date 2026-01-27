## Context
You are helping to redesign and improve a Singapore public transport dashboard / map-based application prototype.

The goal is to refine the UI, interaction flow, and data presentation to better reflect real-world Singapore transport usage and events.

---

## Required Changes & Enhancements

### 1. Remove Monetary Elements
- Remove all references to **money, fares, savings, or financial incentives**
- Focus purely on **time, congestion, disruptions, and user awareness**

---

### 2. Replace Buttons with Time Dropdown
- Replace existing buttons with a **dropdown selector**
- Dropdown allows users to **select a specific hour**
- Time should be displayed in proper **time format** (e.g. `07:00`, `08:30`, `18:00`)
- Ensure consistency across:
  - Maps
  - Active events
  - Any time-based indicators

---

### 3. Separate Maps by Transport Type

#### Bus Map
- Create a **dedicated bus map**
- Split bus visualisation by **districts / regions** (e.g. Central, East, West, North, North-East)
- Clearly show:
  - Bus congestion
  - Bus disruptions
  - District-level intensity

#### Train Map
- Create a **separate train map**
- Organise train data by **MRT lines**, such as:
  - Circle Line
  - North East Line
  - East West Line
  - Downtown Line
  - North South Line
- Each line should be visually distinct and recognisable

---

### 4. Train Breakdowns in Active Events
- Add **train breakdowns / service disruptions** into the **Active Events** section
- Each event should include:
  - Affected MRT line
  - Nature of disruption (e.g. delay, breakdown, partial closure)
  - Time window
  - Severity indicator (low / medium / high)

---

### 5. Map Design – Singapore Style
- Redesign maps to resemble **Singapore’s official transport maps**
- Clean, schematic, and minimal
- Use:
  - Clear line colours
  - Simple nodes/stations
  - District boundaries for buses
- Avoid clutter and overly realistic map visuals

---

### 6. Time Display Formatting
- Replace generic hour labels (e.g. `7`, `8`, `9`) with **formatted time**
- Example:
  - ❌ `7`
  - ✅ `07:00`
- Apply consistently across:
  - Dropdown
  - Map legend
  - Event timestamps

---

### 7. Weather Integration into Active Events
- Add **weather conditions** (e.g. raining, heavy rain, thunderstorms) into **Active Events**
- Weather events should:
  - Be time-specific
  - Indicate affected areas
  - Show potential impact on transport (e.g. slower bus speeds, higher congestion)

---

## Output Expectations
Please generate:
- Updated **UI structure**
- Suggested **interaction flow**
- Clear **section breakdowns**
- Any assumptions you make should be explicitly stated

Keep the design practical, Singapore-specific, and easy for commuters to understand at a glance.
