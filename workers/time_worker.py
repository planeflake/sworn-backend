# workers/time_worker.py
from workers.celery_app import app
from database.connection import SessionLocal
from models.core import Worlds
from workers.settlement_worker import process_all_settlements
import logging

logger = logging.getLogger(__name__)

@app.task
def advance_game_day(world_id=None):
    """Advance the game day for one or all worlds"""
    db = SessionLocal()
    try:
        query = db.query(Worlds)
        if world_id:
            query = query.filter(Worlds.world_id == world_id)
        
        worlds = query.all()
        
        for world in worlds:
            # Advance day counter
            world.current_game_day += 1
            logger.info(f"Advanced world {world.world_name} to day {world.current_game_day}")
            
            # Trigger daily processes for this world
            process_all_settlements.delay(str(world.world_id))
        
        db.commit()
        return len(worlds)
    finally:
        db.close()