import json
import uuid
import logging
from typing import List, Optional, Dict, Any
from sqlalchemy import select, insert, update, delete
from sqlalchemy.orm import Session
from database.connection import SessionLocal

from app.models.settlement import SettlementModel
from app.game_state.entities.settlement import Settlement

logger = logging.getLogger(__name__)

class SettlementManager:
    """
    Manages persistence and lifecycle for Settlement entities.
    
    Responsibilities:
      1. Loading settlements from the database.
      2. Saving settlements to the database.
      3. Creating new settlements.
      4. Maintaining a cache of loaded settlements.
      5. Providing query methods.
    """
    
    def __init__(self):
        self.settlements = {}  # Cache: settlement_id -> Settlement (domain entity)
        logger.info(f"{self.__class__.__name__} initialized")
    
    def create_settlement(self, name: str, description: Optional[str] = None) -> Settlement:
        """
        Create a new settlement with a unique ID.
        """
        settlement_id = str(uuid.uuid4())
        settlement = Settlement(settlement_id=settlement_id, name=name, description=description)
        settlement.set_basic_info(name, description or f"A settlement named {name}")
        self.settlements[settlement_id] = settlement
        self.save_settlement(settlement)
        logger.info(f"Created new settlement: {name} (ID: {settlement_id})")
        return settlement

    def load_settlement(self, settlement_id: str) -> Optional[Settlement]:
        """
        Load a settlement from cache or database.
        """
        if settlement_id in self.settlements:
            return self.settlements[settlement_id]
        
        session: Session = SessionLocal()
        try:
            stmt = select(SettlementModel).where(SettlementModel.settlement_id == settlement_id)
            result = session.execute(stmt).scalars().first()
            if not result:
                logger.warning(f"Settlement not found: {settlement_id}")
                return None
            # Convert the ORM model to a dictionary, then to a domain Settlement.
            settlement_data = result.to_dict()
            settlement = Settlement.from_dict(settlement_data)
            self.settlements[settlement_id] = settlement
            logger.info(f"Loaded settlement: {settlement.settlement_name} (ID: {settlement_id})")
            return settlement
        except Exception as e:
            logger.error(f"Error loading settlement {settlement_id}: {e}")
            return None
        finally:
            session.close()

    def save_settlement(self, settlement: Settlement) -> bool:
        """
        Save (insert or update) a settlement to the database.
        """
        if not settlement.is_dirty:
            return True

        try:
            settlement_dict = settlement.to_dict()
            
            # Use a custom JSON encoder that handles UUID objects
            class UUIDEncoder(json.JSONEncoder):
                def default(self, obj):
                    import uuid
                    if isinstance(obj, uuid.UUID):
                        return str(obj)
                    return json.JSONEncoder.default(self, obj)
            
            settlement_data = json.dumps(settlement_dict, cls=UUIDEncoder)
        except Exception as e:
            logger.error(f"Error serializing settlement {settlement.settlement_id}: {e}")
            return False

        session: Session = SessionLocal()
        try:
            # Check if a record already exists
            stmt = select(SettlementModel).where(SettlementModel.settlement_id == settlement.settlement_id)
            existing = session.execute(stmt).scalars().first()

            if existing:
                # Update record
                upd = (
                    update(SettlementModel)
                    .where(SettlementModel.settlement_id == settlement.settlement_id)
                    .values(
                        settlement_name=settlement.settlement_name,
                        description=settlement.description,
                        location_id=settlement.location_id,
                        relations=settlement.relations,
                        is_repairable=settlement.is_repairable,
                        is_damaged=settlement.is_damaged,
                        has_started_building=settlement.has_started_building,
                        is_under_repair=settlement.is_under_repair,
                        is_built=settlement.is_built,
                        properties=settlement_dict.get("properties", {})
                    )
                )
                session.execute(upd)
            else:
                # Insert new record using SettlementModel's constructor
                new_settlement = SettlementModel(**settlement_dict)
                session.add(new_settlement)
            session.commit()
            settlement.clean()
            logger.info(f"Saved settlement: {settlement.settlement_name} (ID: {settlement.settlement_id})")
            return True
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to save settlement {settlement.settlement_id}: {e}")
            return False
        finally:
            session.close()

    def delete_settlement(self, settlement_id: str) -> bool:
        """
        Delete a settlement from the database and cache.
        """
        self.settlements.pop(settlement_id, None)
        session: Session = SessionLocal()
        try:
            stmt = delete(SettlementModel).where(SettlementModel.settlement_id == settlement_id)
            session.execute(stmt)
            session.commit()
            logger.info(f"Deleted settlement: {settlement_id}")
            return True
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to delete settlement {settlement_id}: {e}")
            return False
        finally:
            session.close()

    def get_all_settlements(self) -> List[Settlement]:
        """
        Retrieve all settlements from the database.
        """
        session: Session = SessionLocal()
        try:
            stmt = select(SettlementModel)
            results = session.execute(stmt).scalars().all()
            settlements = []
            for model in results:
                settlement = Settlement.from_dict(model.to_dict())
                self.settlements[settlement.id] = settlement
                settlements.append(settlement)
            return settlements
        except Exception as e:
            logger.error(f"Error fetching all settlements: {e}")
            return []
        finally:
            session.close()

    def get_settlements_by_location(self, location_id: str) -> List[Settlement]:
        """
        Retrieve settlements at a specific location.
        """
        session: Session = SessionLocal()
        try:
            stmt = select(SettlementModel).where(SettlementModel.location_id == location_id)
            results = session.execute(stmt).scalars().all()
            settlements = []
            for model in results:
                settlement = Settlement.from_dict(model.to_dict())
                self.settlements[settlement.id] = settlement
                settlements.append(settlement)
            return settlements
        except Exception as e:
            logger.error(f"Error fetching settlements at location {location_id}: {e}")
            return []
        finally:
            session.close()

    def get_settlement_by_name(self, name: str) -> Optional[Settlement]:
        """
        Find a settlement by name.
        """
        session: Session = SessionLocal()
        try:
            stmt = select(SettlementModel).where(SettlementModel.name == name)
            result = session.execute(stmt).scalars().first()
            if result:
                settlement = Settlement.from_dict(result.to_dict())
                self.settlements[settlement.id] = settlement
                return settlement
            return None
        except Exception as e:
            logger.error(f"Error fetching settlement by name {name}: {e}")
            return None
        finally:
            session.close()

    def update_settlement_location(self, settlement_id: str, location_id: str) -> bool:
        """
        Update the location of a settlement.
        """
        settlement = self.load_settlement(settlement_id)
        if not settlement:
            logger.warning(f"Settlement not found for update: {settlement_id}")
            return False
        settlement.set_location(location_id)
        return self.save_settlement(settlement)

    def save_all_settlements(self) -> bool:
        """
        Save all loaded (dirty) settlements.
        """
        success = True
        for settlement in self.settlements.values():
            if settlement.is_dirty():
                if not self.save_settlement(settlement):
                    success = False
        return success

    def get_settlement_count(self) -> int:
        """
        Return the total number of settlements in the database.
        """
        session: Session = SessionLocal()
        try:
            stmt = select(SettlementModel)
            results = session.execute(stmt).scalars().all()
            return len(results)
        except Exception as e:
            logger.error(f"Error counting settlements: {e}")
            return 0
        finally:
            session.close()

    def soft_delete_settlement(self, settlement_id: str) -> bool:
        """
        Soft delete a settlement by marking it as inactive.
        (Assumes your domain Settlement supports an 'is_active' attribute.)
        """
        settlement = self.load_settlement(settlement_id)
        if not settlement:
            logger.warning(f"Settlement not found for soft delete: {settlement_id}")
            return False
        settlement.is_active = False
        return self.save_settlement(settlement)

    # Additional methods (pagination, cache refresh, bulk operations, etc.)
    def clear_cache(self) -> None:
        """Clear the settlements cache."""
        self.settlements.clear()
        logger.info("Settlement cache cleared")

    def refresh_cache(self, settlement_id: str) -> Optional[Settlement]:
        """Refresh a specific settlement in the cache."""
        settlement = self.load_settlement(settlement_id)
        if settlement:
            self.settlements[settlement_id] = settlement
        return settlement
