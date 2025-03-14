# app/game_state/manager.py
from sqlalchemy.orm import Session
from models.core import Worlds, Settlements, Characters
import logging

logger = logging.getLogger(__name__)

class GameStateManager:
    def __init__(self, db: Session):
        self.db = db
    
    def get_world_state(self, world_id):
        """Get the complete state of a world"""
        world = self.db.query(Worlds).filter(Worlds.world_id == world_id).first()
        if not world:
            return None
        
        return {
            "world": world,
            "current_day": world.current_game_day,
            "settlement_count": self.db.query(Settlements).filter(Settlements.world_id == world_id).count(),
            "player_count": self.db.query(Characters).filter(Characters.world_id == world_id).count()
        }
    
    def advance_game_day(self, world_id):
        """Increment the game day counter and trigger daily processes"""
        world = self.db.query(Worlds).filter(Worlds.world_id == world_id).first()
        if not world:
            return False
        
        world.current_game_day += 1
        self.db.commit()
        
        logger.info(f"Advanced world {world_id} to day {world.current_game_day}")
        return world.current_game_day