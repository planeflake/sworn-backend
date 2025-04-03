# NPCs and Traders Consolidation Strategy

This directory contains the strategic plans for consolidating the NPCs and Traders tables to create a more unified, maintainable character system.

## Current Architecture

The current system uses two separate tables to represent trader characters:

1. **NPCs Table**
   - Contains basic NPC information (name, stats, skills)
   - General-purpose for all NPC types
   - Used for location tracking
   - Currently has ~14 records

2. **Traders Table**
   - Contains trader-specific attributes and behavior
   - Handles trading functionality, inventory, etc.
   - Tracks journey information
   - Currently has ~6 records (all linked to NPCs)

This dual-table approach creates several challenges:
- Data duplication and potential inconsistency
- Complex code to work with both tables
- Difficulty extending functionality to other NPC types
- Maintenance overhead

## Consolidation Strategy

Rather than attempting an immediate, high-risk consolidation, we've developed a two-phase approach:

### [Short-Term Plan](SHORT_TERM_PLAN.md)

A 6-week plan to begin the transition while maintaining compatibility:

- Leverage the existing CharacterRole system
- Move trader-specific attributes to role attributes
- Begin using NPCs as the primary record
- Create compatibility services and utilities
- No schema removal, only enhancement

This approach provides incremental improvements while minimizing risk.

### [Long-Term Plan](LONG_TERM_PLAN.md)

A 6-month comprehensive consolidation plan:

- Complete elimination of the Traders table
- Full migration to role-based NPC architecture
- Entire codebase refactoring
- Enhanced flexibility for multi-role NPCs
- Schema simplification and optimization

## Key Benefits

Unifying NPCs and Traders tables through a role-based approach will:

1. **Reduce Complexity**
   - Single source of truth for character data
   - Consistent patterns for accessing character attributes
   - Simplified location and state tracking

2. **Improve Extensibility**
   - Easy addition of new NPC types
   - NPCs can take on multiple roles
   - Reusable behavior across NPC types

3. **Enhance Gameplay**
   - More dynamic NPCs with evolving roles
   - Better integration between different character systems
   - Faster development of new NPC behaviors

## Implementation Considerations

Several factors influence the proposed timeline and approach:

- **Code Dependencies**: ~363 references to trader_id in the codebase
- **API Stability**: Need to maintain compatibility for frontend
- **Data Integrity**: Ensuring no information is lost during transition
- **Performance**: Maintaining efficient queries and processing

## Getting Started

To begin implementing this strategy:

1. Review both the short-term and long-term plans
2. Start with the tasks in Phase 1 of the short-term plan
3. Create a tracking system for migration progress
4. Implement comprehensive testing between each step

## Diagrams

### Current Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  API Layer  │────►│TraderService│────►│   Traders   │
└─────────────┘     └─────────────┘     └─────────────┘
                         │                     │
                         │                     │ npc_id
                         ▼                     ▼
                    ┌─────────────┐     ┌─────────────┐
                    │ NPC Service │────►│    NPCs     │
                    └─────────────┘     └─────────────┘
```

### Target Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  API Layer  │────►│ NPC Service │────►│    NPCs     │
└─────────────┘     └─────────────┘     └─────────────┘
                         │                     │
                         │                     │
                         ▼                     ▼
                    ┌─────────────┐     ┌─────────────┐
                    │ Role Service│────►│    Roles    │
                    └─────────────┘     └─────────────┘
```

This unified approach will create a more maintainable and extensible system for all character types in the game.