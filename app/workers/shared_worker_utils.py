from app.workers.celery_app import app
from database.connection import SessionLocal
from app.models.core import Settlements, Worlds
from app.models.seasons import Seasons
from sqlalchemy import text

@app.task
def get_seasonal_modifiers(world_id):
    """Get the resource production modifiers for the current season in a world"""
    db = SessionLocal()
    try:
        world = db.query(Worlds).filter(Worlds.world_id == world_id).first()
        if not world:
            return {"error": "World not found"}
        
        current_season = world.current_season or "spring"
        
        # Check if seasons table exists
        if not db.execute(text("SELECT to_regclass('public.seasons')")).scalar():
            # Return default modifiers if seasons table doesn't exist
            return {
                "season": current_season,
                "modifiers": {
                    "wood": 1.0,
                    "food": 1.0,
                    "stone": 1.0,
                    "ore": 1.0,
                    "herbs": 1.0
                },
                "travel_modifier": 1.0
            }
        
        # Get season from database
        season = db.query(Seasons).filter(Seasons.name == current_season).first()
        if not season:
            return {
                "season": current_season,
                "modifiers": {
                    "wood": 1.0,
                    "food": 1.0,
                    "stone": 1.0,
                    "ore": 1.0,
                    "herbs": 1.0
                },
                "travel_modifier": 1.0
            }
        
        return {
            "season": current_season,
            "display_name": season.display_name,
            "modifiers": season.resource_modifiers,
            "travel_modifier": season.travel_modifier,
            "description": season.description,
            "color": season.color_hex
        }
        
    finally:
        db.close()
     
@app.task
def process_all_settlements(world_id=None):
    db = SessionLocal()
    try:
        query = db.query(Settlements)
        
        # Filter by world if provided
        if world_id:
            query = query.filter(Settlements.world_id == world_id)
            
        settlements = query.all()
        
        # Import here to avoid circular import
        from app.workers.settlement_worker import process_settlement_production
        
        for settlement in settlements:
            process_settlement_production.delay(str(settlement.settlement_id))
        
        return {"status": "success", "count": len(settlements)}
    finally:
        db.close()
