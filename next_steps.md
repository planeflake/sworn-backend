# 🌎 Sworn: Living World Simulation Features

This document outlines proposed and active systems that make the world of **Sworn** feel alive even before players are introduced. Each system is modular, theme-aware, and built to evolve autonomously.

---

## ☁️ Weather System

**Goal:** Dynamically generate and apply seasonal weather that affects the environment and future character actions.

### Requirements:
- `weather_types` table (theme-aware, weighted, by season)
- `world_weather` table (active events, tied to world)
- `WeatherService` (daily weather updates, event generation)

### Features:
- Seasonal weather pulled from DB based on `theme_id`
- Daily weather rolls, chance-based intensity and duration
- Affects resource yields, trade, movement
- Future: Tied to mood, crops, or faction morale

### Integration:
- Called from `advance_world_day()`
- Can trigger side effects in settlement services

---

## 🌕 Celestial Event System

**Goal:** Introduce lunar cycles and cosmic patterns that influence the world’s behavior.

### Requirements:
- `celestial_cycles` table (name, period, offset, phase, theme-aware)
- `celestial_events` table (triggered results by world/day)
- `CelestialService` (evaluates which cycles trigger each day)

### Features:
- Lunar and eclipse cycles, including custom ones like “Warp Crescent”
- Each world triggers unique celestial events
- Phases like "full", "crescent", "warp-aligned"
- WorldProphecies can react to celestial phases

### Integration:
- Called from `advance_world_day()`
- Data exposed via `/worlds/{id}/celestial-events`

---

## 🌋 Geological Event System

**Goal:** Add tectonic, volcanic, and resource-generating events that shape terrain and influence exploration.

### Requirements:
- `geological_events` table (intensity, resource discovery)
- `GeologicalService` with random daily checks
- `Resource` table with theme-aware entries
- `resource_nodes` table with visibility and accessibility flags

### Features:
- Rare, powerful events: quakes, eruptions, fault shifts
- Can cause new resource nodes to become accessible
- Resources pulled dynamically per world/theme
- Nodes may be hidden and require discovery via skill checks or NPC actions

### Integration:
- Geological events mark or create resource nodes
- Characters/NPCs with appropriate skill levels may detect nodes post-event
- Future: integrate with settlement upgrade options

---

## 🔮 Settlement & Resource Node System

**Goal:** Allow dynamic creation of settlements and hidden resources tied to terrain, discovery, and skills.

### Requirements:
- `settlements` table with location, population, stats
- `resource_nodes` table (location, resource_id, hidden, accessibility_score, discovered_by_id, discovered_at)

### Features:
- Settlements can build near areas with latent (hidden) resources
- Resource nodes start hidden unless revealed by:
  - Geological events (expose surface indicators)
  - Specialist NPCs or characters with mining/geology skills
- Discovery chance = accessibility + skill bonuses
- Nodes can fuel settlement upgrades (e.g. mines, quarries)

### Integration:
- Called from geological service and `settlement_tick`
- Detected nodes flagged and linked to discoverer entity
- Triggers quest chain or auto-structures in the future

---

## 🔮 World Prophecies

**Goal:** Introduce long-arc narrative triggers that fire under specific conditions to deepen world lore.

### Requirements:
- `world_prophecies` table (text, condition_trigger, fulfilled)
- `ProphecyService` to evaluate them during world tick

### Features:
- Encoded triggers: `event_phase:full`, `quake:intensity>7`
- Fulfilled prophecies log world lore
- Optional effects: unlock regions, spawn threats, shift diplomacy

### Integration:
- Runs in parallel with celestial/geological systems
- Can generate system logs or lore entries

---

## Other Modular Systems

### 🔯 Faith & Pantheon System
- `pantheon`, `deities`, `worship_activity`
- Settlements may change dominant religion over time
- Certain deities favor specific celestial events

### 🌱 Soil Fertility
- Each area has a `fertility_score`
- Decreases over time; improves with weather or events

### 🦠 Plague Simulation
- Outbreaks spread from region to region via roads/trade
- Climate and moon phases can influence infection rate

### 🗡️ Bandit Factions
- Splinter factions form if morale or prosperity drops
- May raid settlements or disrupt trade

### 🛃 Rediscovered Infrastructure
- Ancient roads, portals, aqueducts hidden in terrain
- Become active via quakes, prophecy, or celestial alignments

---

## Next Steps
- [ ] Seed `weather_types` with generic and Warhammer examples
- [ ] Add theme-aware `Resource` entries for discovery
- [ ] Wire `CelestialService`, `GeologicalService`, and `ProphecyService` into world tick
- [ ] Add `resource_nodes` table with discovery mechanics
- [ ] Add logic for NPC or character-based discovery of nodes
- [ ] Unit tests for each subsystem
- [ ] Create API routes to expose current weather, celestial state, geological history, fulfilled prophecies

