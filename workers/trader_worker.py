# workers/trader_worker.py
from workers.celery_app import app
from database.connection import SessionLocal
from models.core import Traders, Settlements #, NPCs
from app.ai.simple_decision import SimpleDecisionEngine
import logging
import uuid

logger = logging.getLogger(__name__)
decision_engine = SimpleDecisionEngine()

@app.task
def process_trader_movement(trader_id):
    """Process trader movement decision and execution"""
    db = SessionLocal()
    try:
        trader = db.query(Traders).filter(Traders.trader_id == trader_id).first()
        if not trader:
            logger.error(f"Trader {trader_id} not found")
            return False
        
        # Get current and connected settlements
        current_settlement = db.query(Settlements).filter(
            Settlements.settlement_id == trader.current_settlement_id
        ).first()
        
        if not current_settlement or not current_settlement.connections:
            logger.warning(f"Trader {trader_id} has no valid connections from current location")
            return False
        
        # Build trader data for AI
        trader_data = {
            'trader_id': str(trader.trader_id),
            'current_settlement_id': str(trader.current_settlement_id),
            'home_settlement_id': str(trader.home_settlement_id),
            'schedule': trader.schedule,
            'biome_preferences': trader.biome_preferences,
            'world_day': db.query(trader.world_id).first().current_game_day,
            'available_connections': []
        }
        
        # Process connections
        for conn in current_settlement.connections:
            dest_settlement = db.query(Settlements).filter(
                Settlements.settlement_name == conn.get('destination')
            ).first()
            
            if dest_settlement:
                trader_data['available_connections'].append({
                    'destination_id': str(dest_settlement.settlement_id),
                    'destination_name': dest_settlement.settlement_name,
                    'distance': conn.get('distance', 0),
                    'danger_level': conn.get('danger_level', 0),
                    'biome_composition': conn.get('biome_composition', {})
                })
        
        # Use AI to decide next movement
        next_settlement_id = decision_engine.decide_trader_movement(trader_data)
        
        # Execute movement if different from current
        if str(next_settlement_id) != str(trader.current_settlement_id):
            trader.current_settlement_id = uuid.UUID(next_settlement_id)
            db.commit()
            logger.info(f"Trader {trader.npc_id} moved to settlement {next_settlement_id}")
            return True
        
        return False
    
    except Exception as e:
        logger.exception(f"Error processing trader movement: {str(e)}")
        db.rollback()
        return False
    finally:
        db.close()

@app.task
def process_all_traders(world_id=None):
    """Process movement for all traders in a world (or all worlds if none specified)"""
    db = SessionLocal()
    try:
        query = db.query(Traders)
        if world_id:
            query = query.filter(Traders.world_id == world_id)
        
        traders = query.all()
        
        for trader in traders:
            process_trader_movement.delay(str(trader.trader_id))
        
        return len(traders)
    finally:
        db.close()