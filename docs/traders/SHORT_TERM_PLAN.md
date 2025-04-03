# Short-Term NPC/Trader Consolidation Plan

This document outlines the short-term approach to gradually transition from using separate Traders and NPCs tables toward a more unified NPC-based system using the role architecture.

## Overview

Rather than immediately merging the Traders and NPCs tables (which would require extensive code changes), this short-term plan focuses on leveraging the existing CharacterRole system to reduce duplication while maintaining compatibility with current code.

## Goals

1. Reduce data duplication between NPCs and Traders tables
2. Begin using CharacterRole for trader-specific attributes
3. Create patterns for accessing trader data through NPCs
4. Maintain backward compatibility with existing code
5. Set the foundation for future complete consolidation

## Implementation Plan

### Phase 1: Role Enhancement (Week 1-2)

1. **Create/Update Trader Role**
   - Ensure a robust "trader" role exists in the Role table
   - Define a comprehensive attribute schema that covers trader-specific needs
   ```json
   {
     "type": "object",
     "properties": {
       "inventory_capacity": { "type": "number" },
       "cart_health": { "type": "number" },
       "cart_upgrades": { "type": "array" },
       "preferred_biomes": { "type": "object" },
       "trade_routes": { "type": "array" },
       "trade_priorities": { "type": "object" },
       "buy_prices": { "type": "object" },
       "sell_prices": { "type": "object" }
     }
   }
   ```

2. **Ensure All Traders Have NPC Links**
   - Verify all traders have valid NPC records
   - Create missing NPCs for any traders without them
   - Add CharacterRole entries linking NPCs to the trader role

3. **Extend NPCs Schema (If Needed)**
   - Add key fields that don't fit well in the role attributes
   - Consider adding journey_state JSON field to NPCs table

### Phase 2: Service Layer Updates (Week 3-4)

1. **Create TraderNpcService**
   - New service that works with both NPCs and Traders tables
   - Interface compatible with existing TraderService
   - Internal implementation uses both tables as needed
   ```python
   class TraderNpcService:
       def __init__(self, db):
           self.db = db
           self.npc_service = NpcService(db)
           self.role_service = RoleService(db)
           self.trader_service = TraderService(db)  # Legacy service
           
       def get_trader_by_id(self, trader_id):
           # Get from traders table but also load NPC data
           # Return composite object
   ```

2. **Update Worker Functions**
   - Create new versions of key worker functions
   - Gradually transition Celery tasks to use new functions
   - Keep old functions working for backward compatibility

3. **Update Entity Classes**
   - Enhance Trader entity to load data from both sources
   - Add helper methods that work with the new data structure

### Phase 3: Client Code Updates (Week 5-6)

1. **Update API Endpoints**
   - Create new endpoints that use the TraderNpcService
   - Maintain existing endpoints for backward compatibility
   - Document the transition path for API users

2. **Update MCTS Integration**
   - Ensure MCTS decision-making works with the new data structure
   - Update state representation to handle role-based attributes

3. **Create Migration Utilities**
   - Helper functions to sync data between tables
   - Tools to diagnose and fix data inconsistencies

## Testing Strategy

1. **Dual Data Path Testing**
   - Test that data can be accessed through both old and new paths
   - Validate that changes to one path propagate correctly

2. **Movement Simulation**
   - Test trader movement works correctly with role-based attributes
   - Validate journey tracking in the new structure

3. **Trading Tests**
   - Verify that inventory management works with the new structure
   - Test buying/selling functionality

## Metrics for Success

- All traders have corresponding NPCs and CharacterRoles
- No data duplication between NPCs and Traders tables
- All existing functionality works with the new approach
- Code readability and maintainability improvements
- Reduction in specialized code for handling trader entities

## Next Steps After Completion

Upon successful implementation of this short-term plan:

1. Begin monitoring usage of the old vs. new approach
2. Identify remaining barriers to complete consolidation
3. Transition to the long-term plan for full table consolidation

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Functionality regression | Comprehensive test suite covering all trader actions |
| Performance degradation | Benchmark before and after, optimize query patterns |
| Data inconsistency | Create validation tools and syncing mechanisms |
| Development confusion | Clear documentation of the transition patterns |