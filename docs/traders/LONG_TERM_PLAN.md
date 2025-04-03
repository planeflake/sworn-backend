# Long-Term NPC/Trader Consolidation Plan

This document outlines the comprehensive approach for fully consolidating the NPCs and Traders tables into a unified, role-based NPC system.

## Vision

A single, coherent NPC system where all character types (traders, rulers, villagers, etc.) are stored in the NPCs table, with specialized behavior and attributes defined through the CharacterRole system. This creates a more maintainable, extensible architecture that simplifies code while enabling more complex NPC behaviors.

## Strategic Goals

1. Complete elimination of the Traders table
2. Full migration to role-based attributes for specialized NPC types
3. Simplified, consistent API for all NPC interactions
4. Enhanced flexibility for NPCs to take on multiple roles
5. Improved performance and reduced data duplication
6. Cleaner code architecture and reduced maintenance burden

## Implementation Plan

### Phase 1: Schema Enhancement (Month 1)

1. **Extend NPCs Table**
   - Add essential fields that must be directly on NPCs
   ```sql
   ALTER TABLE npcs 
   ADD COLUMN inventory JSONB DEFAULT '{}',
   ADD COLUMN gold INTEGER DEFAULT 0,
   ADD COLUMN journey_data JSONB DEFAULT '{}',
   ADD COLUMN active_task_id UUID DEFAULT NULL;
   ```

2. **Create Comprehensive Role Definitions**
   - Define all specialized NPC types as roles
   - Create detailed attribute schemas for each role
   - Build validation system for role attributes

3. **Develop Migration Scripts**
   - Create tools to move data from Traders to NPCs + Roles
   - Ensure data integrity throughout migration
   - Add validation to confirm successful migration

### Phase 2: Core Services Refactoring (Month 2-3)

1. **Build Unified NPC Service Layer**
   - Complete replacement for TraderService
   - Role-aware service that handles specialized behavior
   - Optimized queries for the new data structure

2. **Refactor Worker Processes**
   - Rewrite trader_worker.py to use NPC + Roles
   - Update Celery task definitions
   - Modify movement and journey tracking code

3. **Refactor Decision-Making Systems**
   - Update MCTS to work with the new NPC structure
   - Modify state representations and action handling
   - Ensure AI decision quality remains consistent

### Phase 3: API and Frontend Updates (Month 4)

1. **Update API Endpoints**
   - Replace trader-specific endpoints with role-based NPC endpoints
   - Create migrations for client applications
   - Document API changes and provide transition examples

2. **Update Admin Tools**
   - Modify tools for NPC and Trader management
   - Update visualization and monitoring tools
   - Create new tools leveraging the unified architecture

3. **Data Analysis Tools**
   - Create new analytics for NPC role performance
   - Build tools for analyzing NPC behavior across roles

### Phase 4: Complete Transition (Month 5-6)

1. **Full Codebase Audit**
   - Scan entire codebase for remaining trader references
   - Update all hard-coded trader assumptions
   - Replace direct SQL queries

2. **Deprecate Traders Table**
   - Mark Traders table as deprecated
   - Add database triggers to maintain compatibility
   - Log usage of deprecated access patterns

3. **Database Migration**
   - Create migration script to completely consolidate data
   - Run in testing environments
   - Schedule production migration

4. **Schema Simplification**
   - After successful migration, plan for table removal
   - Create backup archival of Traders data
   - Remove Traders table in a future release

## Technical Architecture Changes

### Data Access Pattern Before:
```
Code → TraderService → TraderModel → Traders Table
Code → NPCService → NPCs Table
```

### Data Access Pattern After:
```
Code → NPCService (role-aware) → NPCs Table + CharacterRoles Table
```

### Key Components:

1. **Role-Based NPC Service**
   ```python
   class NPCService:
       def get_npc_with_role(self, npc_id, role_code):
           # Fetch NPC and associated role data
           
       def get_trader_data(self, npc_id):
           # Specialized method returns trader-relevant data
           
       def update_journey(self, npc_id, journey_updates):
           # Update journey data on NPC record
   ```

2. **NPC Entity with Role Extensions**
   ```python
   class NPC:
       def __init__(self, base_data, roles=None):
           self.base_data = base_data
           self.roles = roles or {}
           
       def as_trader(self):
           # Return trader view of this NPC
           
       def get_role_attribute(self, role_code, attribute):
           # Get attribute from specific role
   ```

3. **Worker Process Adaptation**
   ```python
   def process_trader_movement(npc_id):
       npc_service = NPCService(db)
       npc = npc_service.get_npc_with_role(npc_id, "trader")
       
       # Process movement using role attributes
       trader_data = npc.roles.get("trader", {})
       journey = npc.journey_data
       # ...
   ```

## Testing Strategy

1. **Comprehensive Test Suite**
   - Develop extensive tests covering all NPC behaviors
   - Create comparative tests between old and new systems
   - Measure performance differences

2. **Data Migration Validation**
   - Validate data integrity after each migration step
   - Create tools to compare NPCs to their former Trader records
   - Test querying patterns to ensure performance

3. **Staged Rollout**
   - Roll out changes to testing environments first
   - Run parallel systems where possible
   - Monitor for unexpected behavior

## Success Metrics

- Zero Traders table dependencies in codebase
- 100% of trader functionality working through NPC + Roles
- Performance equal to or better than the old system
- Reduced code complexity (measured by cyclomatic complexity)
- Ability to assign multiple roles to NPCs
- Development velocity improvement for new NPC features

## Potential Challenges and Mitigations

| Challenge | Mitigation Strategy |
|-----------|---------------------|
| Complex data migration | Incremental approach with validation at each step |
| Performance concerns with role lookup | Optimize queries and consider materialized views |
| Business logic spread across codebase | Comprehensive code scanning and automated tests |
| Backward compatibility | Maintain compatibility layer during transition |
| Timeline slippage | Modular approach allows partial benefits even if full migration delayed |

## Future Opportunities

Once the consolidation is complete, several new possibilities emerge:

1. **Multi-Role NPCs**
   - NPCs that function as both traders and crafters
   - Dynamic role acquisition and evolution

2. **Enhanced NPC Progression**
   - Career paths for NPCs across different roles
   - Skill and attribute development over time

3. **Unified AI System**
   - Single decision-making framework for all NPC types
   - More complex interaction between different NPC roles

4. **Simplified Development**
   - Faster implementation of new NPC types
   - Reduced bugs from inconsistent data structures