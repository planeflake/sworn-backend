# workers/settlement_worker.py
from workers.celery_app import app
from database.connection import SessionLocal

from models.core import Settlements

@app.task
def process_settlement_production(settlement_id):
    db = SessionLocal()
    try:
        # Simple test task
        print(f"Processing production for settlement {settlement_id}")
        # Later you'll add resource generation, building progress, etc.
        return {"status": "success", "settlement_id": settlement_id}
    finally:
        db.close()

    # workers/settlement_worker.py (additional function)

@app.task
def process_all_settlements():
    db = SessionLocal()
    try:
        settlements = db.query(Settlements).all()
        for settlement in settlements:
            process_settlement_production.delay(str(settlement.settlement_id))
        return {"status": "success", "count": len(settlements)}
    finally:
        db.close()

