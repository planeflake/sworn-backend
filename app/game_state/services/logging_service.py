# app/game_state/services/logging_service.py
import logging
import uuid
from datetime import datetime
from typing import Dict, Any, Optional

from sqlalchemy.orm import Session
from app.models.logging import EntityActionLog
from app.models.core import Worlds

logger = logging.getLogger(__name__)

class LoggingService:
    """
    Service for logging entity actions including trader movements.
    Provides methods to create, retrieve, and analyze action logs.
    """
    
    def __init__(self, db: Session):
        """
        Initialize with a database session.
        
        Args:
            db (Session): SQLAlchemy database session
        """
        self.db = db
    
    def log_action(self,
                  entity_id: str,
                  entity_type: str,
                  action_type: str,
                  world_id: str,
                  entity_name: Optional[str] = None,
                  action_subtype: Optional[str] = None,
                  from_location_id: Optional[str] = None,
                  from_location_type: Optional[str] = None,
                  from_location_name: Optional[str] = None,
                  to_location_id: Optional[str] = None,
                  to_location_type: Optional[str] = None,
                  to_location_name: Optional[str] = None,
                  related_entity_id: Optional[str] = None,
                  related_entity_type: Optional[str] = None,
                  related_entity_name: Optional[str] = None,
                  details: Optional[Dict[str, Any]] = None,
                  game_day: Optional[int] = None,
                  game_time: Optional[str] = None) -> str:
        """
        Log an entity action to the database.
        
        Args:
            entity_id: ID of the entity performing the action
            entity_type: Type of entity ('trader', 'player', etc.)
            action_type: Type of action ('movement', 'trade', etc.)
            world_id: ID of the world where the action occurred
            entity_name: Optional name of the entity
            action_subtype: Optional subtype of the action
            from_location_id: Optional source location ID
            from_location_type: Optional source location type
            from_location_name: Optional source location name
            to_location_id: Optional destination location ID
            to_location_type: Optional destination location type
            to_location_name: Optional destination location name
            related_entity_id: Optional ID of a related entity
            related_entity_type: Optional type of the related entity
            related_entity_name: Optional name of the related entity
            details: Optional additional details as a dictionary
            game_day: Optional game day when the action occurred
            game_time: Optional game time when the action occurred
            
        Returns:
            str: ID of the created log entry
        """
        try:
            # If game_day is not provided, try to get it from the world
            if game_day is None:
                world = self.db.query(Worlds).filter(Worlds.world_id == world_id).first()
                if world:
                    game_day = world.current_game_day
            print("Logging action")
            # Create the log entry
            log_entry = EntityActionLog(
                entity_id=entity_id,
                entity_type=entity_type,
                entity_name=entity_name,
                action_type=action_type,
                action_subtype=action_subtype,
                from_location_id=from_location_id,
                from_location_type=from_location_type,
                from_location_name=from_location_name,
                to_location_id=to_location_id,
                to_location_type=to_location_type,
                to_location_name=to_location_name,
                related_entity_id=related_entity_id,
                related_entity_type=related_entity_type,
                related_entity_name=related_entity_name,
                details=details or {},
                world_id=world_id,
                game_day=game_day,
                game_time=game_time,
                timestamp=datetime.utcnow()
            )
            
            self.db.add(log_entry)
            self.db.commit()
            
            logger.info(f"Logged {action_type} action for {entity_type} {entity_id}")
            return str(log_entry.log_id)
            
        except Exception as e:
            logger.exception(f"Error logging action: {e}")
            self.db.rollback()
            return None
    
    def log_trader_movement(self,
                           trader_id: str,
                           trader_name: str,
                           world_id: str,
                           from_location_id: Optional[str] = None,
                           from_location_type: Optional[str] = None,
                           from_location_name: Optional[str] = None,
                           to_location_id: Optional[str] = None,
                           to_location_type: Optional[str] = None,
                           to_location_name: Optional[str] = None,
                           details: Optional[Dict[str, Any]] = None) -> str:
        """
        Log a trader movement action.
        
        Args:
            trader_id: ID of the trader
            trader_name: Name of the trader
            world_id: ID of the world
            from_location_id: Optional source location ID
            from_location_type: Optional source location type ('settlement', 'area')
            from_location_name: Optional source location name
            to_location_id: Optional destination location ID
            to_location_type: Optional destination location type
            to_location_name: Optional destination location name
            details: Optional additional details
            
        Returns:
            str: ID of the created log entry
        """
        # Determine action subtype based on locations
        action_subtype = None
        if from_location_id and to_location_id:
            action_subtype = "travel"
        elif from_location_id and not to_location_id:
            action_subtype = "depart"
        elif not from_location_id and to_location_id:
            action_subtype = "arrive"
            
        return self.log_action(
            entity_id=trader_id,
            entity_type="trader",
            entity_name=trader_name,
            action_type="movement",
            action_subtype=action_subtype,
            world_id=world_id,
            from_location_id=from_location_id,
            from_location_type=from_location_type,
            from_location_name=from_location_name,
            to_location_id=to_location_id,
            to_location_type=to_location_type,
            to_location_name=to_location_name,
            details=details
        )
    
    def log_trader_trade(self,
                        trader_id: str,
                        trader_name: str,
                        world_id: str,
                        location_id: str,
                        location_type: str,
                        location_name: str,
                        related_entity_id: Optional[str] = None,
                        related_entity_type: Optional[str] = None,
                        related_entity_name: Optional[str] = None,
                        items_sold: Optional[Dict[str, Any]] = None,
                        items_bought: Optional[Dict[str, Any]] = None,
                        gold_received: Optional[int] = None,
                        gold_spent: Optional[int] = None) -> str:
        """
        Log a trader trade action.
        
        Args:
            trader_id: ID of the trader
            trader_name: Name of the trader
            world_id: ID of the world
            location_id: ID of the location where trade occurred
            location_type: Type of location ('settlement', 'area')
            location_name: Name of the location
            related_entity_id: Optional ID of the trading partner
            related_entity_type: Optional type of the trading partner
            related_entity_name: Optional name of the trading partner
            items_sold: Optional dictionary of items sold by the trader
            items_bought: Optional dictionary of items bought by the trader
            gold_received: Optional amount of gold received
            gold_spent: Optional amount of gold spent
            
        Returns:
            str: ID of the created log entry
        """
        details = {
            "items_sold": items_sold or {},
            "items_bought": items_bought or {},
            "gold_received": gold_received,
            "gold_spent": gold_spent,
            "profit": (gold_received or 0) - (gold_spent or 0)
        }
        
        return self.log_action(
            entity_id=trader_id,
            entity_type="trader",
            entity_name=trader_name,
            action_type="trade",
            world_id=world_id,
            from_location_id=location_id,
            from_location_type=location_type,
            from_location_name=location_name,
            related_entity_id=related_entity_id,
            related_entity_type=related_entity_type,
            related_entity_name=related_entity_name,
            details=details
        )
    
    def get_trader_action_history(self, trader_id: str, limit: int = 100) -> list:
        """
        Get action history for a specific trader.
        
        Args:
            trader_id: ID of the trader
            limit: Maximum number of records to return
            
        Returns:
            list: List of action log entries
        """
        try:
            query = self.db.query(EntityActionLog).filter(
                EntityActionLog.entity_id == trader_id,
                EntityActionLog.entity_type == 'trader'
            ).order_by(EntityActionLog.timestamp.desc()).limit(limit)
            
            return query.all()
            
        except Exception as e:
            logger.exception(f"Error retrieving trader action history: {e}")
            return []
    
    def get_trader_movement_history(self, trader_id: str, limit: int = 100) -> list:
        """
        Get movement history for a specific trader.
        
        Args:
            trader_id: ID of the trader
            limit: Maximum number of records to return
            
        Returns:
            list: List of movement log entries
        """
        try:
            query = self.db.query(EntityActionLog).filter(
                EntityActionLog.entity_id == trader_id,
                EntityActionLog.entity_type == 'trader',
                EntityActionLog.action_type == 'movement'
            ).order_by(EntityActionLog.timestamp.desc()).limit(limit)
            
            return query.all()
            
        except Exception as e:
            logger.exception(f"Error retrieving trader movement history: {e}")
            return []