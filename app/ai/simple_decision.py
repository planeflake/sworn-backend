# ai/simple_decision.py
from typing import Dict, Any, List
import random
import logging
import json

logger = logging.getLogger(__name__)

class SimpleDecisionEngine:
    """A simple rule-based decision engine for NPCs"""
    
    def decide_trader_movement(self, trader_data: Dict[str, Any]) -> Dict[str, Any]:
        """Decide the next move for a trader"""
        connections = trader_data.get('available_connections', [])
        
        # Validate connections
        valid_connections = []
        for conn in connections:
            if not isinstance(conn, dict):
                logger.warning(f"Skipping invalid connection (not a dict): {conn}")
                continue
                
            # Check required fields
            if 'destination_id' not in conn or 'destination_name' not in conn:
                logger.warning(f"Skipping connection missing required fields: {conn}")
                continue
                
            # Skip invalid destination IDs
            dest_id = conn['destination_id']
            if (isinstance(dest_id, str) and 
                (dest_id.startswith('11111') or dest_id == '00000000-0000-0000-0000-000000000000')):
                logger.warning(f"Skipping connection with placeholder destination ID: {dest_id}")
                continue
                
            valid_connections.append(conn)
            
        if not valid_connections:
            # If no valid connections, try to return home
            home_id = trader_data.get('home_settlement_id')
            if home_id and home_id != trader_data.get('current_settlement_id'):
                logger.info(f"No valid connections, returning to home settlement {home_id}")
                return {
                    'next_settlement_id': home_id,
                    'next_settlement_name': 'Home Settlement'
                }
            raise ValueError("No valid connections for trader movement")
            
        # Use validated connections for decision making
        connections = valid_connections
        
        home_settlement_id = trader_data.get('home_settlement_id')
        current_settlement_id = trader_data.get('current_settlement_id')
        world_day = trader_data.get('world_day', 1)
        biome_preferences = trader_data.get('biome_preferences', {})
        schedule = trader_data.get('schedule', {})
        
        # Check if trader should return home (every 7 days)
        going_home = False
        if world_day % 7 == 0 and current_settlement_id != home_settlement_id:
            # Find connection to home settlement if available
            home_connection = next(
                (conn for conn in connections if conn['destination_id'] == home_settlement_id), 
                None
            )
            if home_connection:
                logger.info(f"Trader returning home on day {world_day}")
                next_move = {
                    'next_settlement_id': home_connection['destination_id'],
                    'next_settlement_name': home_connection['destination_name']
                }
                return next_move
            going_home = True
        
        # Parse biome preferences if available
        biome_weights = {}
        if biome_preferences and isinstance(biome_preferences, str):
            try:
                biome_weights = json.loads(biome_preferences)
            except json.JSONDecodeError:
                logger.warning(f"Invalid biome preferences format: {biome_preferences}")
        
        # Weighted selection of next settlement
        total_weight = 0
        weighted_connections = []
        
        for conn in connections:
            # Skip current settlement in connections (self-connection)
            if conn['destination_id'] == current_settlement_id:
                continue
                
            # Base weight
            weight = 1.0
            
            # Increase weight for home settlement if trying to go home
            if going_home and conn['destination_id'] == home_settlement_id:
                weight *= 5.0
                
            # Use schedule preferences if available (not implemented yet)
            
            # Add to weighted list
            weighted_connections.append((conn, weight))
            total_weight += weight
        
        # If no valid connections after filtering, pick a random one
        if not weighted_connections:
            logger.warning("No weighted connections available, selecting randomly")
            # Make sure connections isn't empty
            if not connections:
                # Default to home settlement if we have no connections
                if home_settlement_id:
                    return {
                        'next_settlement_id': home_settlement_id,
                        'next_settlement_name': 'Home Settlement'
                    }
                # Really nothing to do here
                raise ValueError("No connections at all and no home settlement")
                
            random_conn = random.choice(connections)
            return {
                'next_settlement_id': random_conn['destination_id'],
                'next_settlement_name': random_conn.get('destination_name', 'Unknown')
            }
        
        # Select based on weights
        selection = random.random() * total_weight
        current_weight = 0
        
        for conn, weight in weighted_connections:
            current_weight += weight
            if selection <= current_weight:
                return {
                    'next_settlement_id': conn['destination_id'],
                    'next_settlement_name': conn['destination_name']
                }
        
        # Fallback
        fallback = weighted_connections[0][0]
        logger.info(f"Using fallback connection: {fallback}")
        return {
            'next_settlement_id': fallback['destination_id'],
            'next_settlement_name': fallback['destination_name']
        }