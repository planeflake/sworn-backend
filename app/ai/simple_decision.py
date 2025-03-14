# ai/simple_decision.py
from typing import Dict, Any, List
import random
import logging

logger = logging.getLogger(__name__)

class SimpleDecisionEngine:
    """A simple rule-based decision engine for NPCs"""
    
    def decide_trader_movement(self, trader_data: Dict[str, Any]) -> str:
        """Decide where a trader should travel next based on simple rules"""
        current_location = trader_data['current_settlement_id']
        home_location = trader_data['home_settlement_id']
        schedule = trader_data.get('schedule', {})
        connections = trader_data.get('available_connections', [])
        
        if not connections:
            logger.warning(f"Trader {trader_data.get('trader_id')} has no available connections to travel")
            return current_location
        
        # Simple cases first
        if len(connections) == 1:
            # Only one option
            return connections[0]['destination_id']
        
        # Check if we're following a schedule
        if schedule:
            # Get today's scheduled destination, if any
            current_day = trader_data.get('world_day', 1)
            for settlement, schedule_info in schedule.items():
                if (current_day - schedule_info.get('arrival_day', 1)) % schedule_info.get('frequency_days', 7) == 0:
                    # Find this settlement in connections
                    for conn in connections:
                        if conn['destination_name'] == settlement:
                            return conn['destination_id']
        
        # If we're away from home for too long, go home
        days_away = trader_data.get('days_away', 0)
        if days_away > 5 and home_location != current_location:
            # Find home in connections
            for conn in connections:
                if conn['destination_id'] == home_location:
                    return home_location
        
        # Default: pick a random connection weighted by trader preferences
        weighted_connections = []
        for conn in connections:
            # Calculate a weight based on:
            # 1. Trader's biome preferences
            # 2. Danger level (inverse)
            # 3. Distance (inverse)
            biome_weight = 0
            for biome, composition in conn.get('biome_composition', {}).items():
                preference = trader_data.get('biome_preferences', {}).get(biome, 0.5)
                biome_weight += preference * composition
            
            danger_weight = 1.0 / (1 + conn.get('danger_level', 1))
            distance_weight = 1.0 / (1 + conn.get('distance', 1) / 20)
            
            total_weight = biome_weight * danger_weight * distance_weight
            weighted_connections.append((conn['destination_id'], total_weight))
        
        # Normalize weights
        total = sum(w for _, w in weighted_connections)
        if total > 0:
            normalized = [(id, w/total) for id, w in weighted_connections]
            
            # Choose based on weights
            choice = random.random()
            cumulative = 0
            for dest_id, weight in normalized:
                cumulative += weight
                if cumulative >= choice:
                    return dest_id
        
        # Fallback: completely random
        return random.choice([conn['destination_id'] for conn in connections])