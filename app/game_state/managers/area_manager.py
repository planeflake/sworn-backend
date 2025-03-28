import json
import uuid
import logging
from typing import List, Optional
from sqlalchemy import select, insert, update, delete
from sqlalchemy.orm import Session
from database.connection import SessionLocal

from app.game_state.entities.area import Area
from app.models.area import AreaModel

logger = logging.getLogger(__name__)

class AreaManager:
    """
    Manages persistence and lifecycle for Area entities.
    Responsible for loading, saving, creating, and querying Areas.
    """
    def __init__(self):
        self.entities = {}  # Cache of loaded areas
        logger.info("AreaManager initialized")
    
    def create_area(self, name: str, description: Optional[str] = None, area_type: Optional[str] = None) -> Area:
        """
        Create and persist a new Area entity.
        """
        area_id = str(uuid.uuid4())
        area = Area(name=name, description=description, area_type=area_type, area_id=area_id)
        area.set_basic_info(name, description or f"An area named {name}")
        self.entities[area_id] = area
        self.save_entity(area)
        logger.info(f"Created new area: {name} (ID: {area_id})")
        return area

    def load_entity(self, area_id: str) -> Optional[Area]:
        """
        Load an Area entity from cache or the database.
        """
        if area_id in self.entities:
            return self.entities[area_id]
        
        session: Session = SessionLocal()
        try:
            stmt = select(AreaModel).where(AreaModel.area_id == area_id)
            result = session.execute(stmt).scalars().first()
            if not result:
                logger.warning(f"Area not found: {area_id}")
                return None
            # Assuming AreaModel has a to_dict() method for conversion
            area_data = result.to_dict()
            area = Area.from_dict(area_data)
            self.entities[area_id] = area
            logger.info(f"Loaded area: {area.area_name} (ID: {area_id})")
            return area
        except Exception as e:
            logger.error(f"Error loading area {area_id}: {e}")
            return None
        finally:
            session.close()

    def save_entity(self, area: Area) -> bool:
        """
        Save (insert/update) an Area entity to the database.
        """
        if not area.is_dirty():
            return True

        try:
            area_dict = area.to_dict()
            session: Session = SessionLocal()
            try:
                # Try to load an existing record
                stmt = select(AreaModel).where(AreaModel.area_id == area.area_id)
                existing = session.execute(stmt).scalars().first()
                if existing:
                    # Update the existing record
                    stmt = (
                        update(AreaModel)
                        .where(AreaModel.area_id == area.area_id)
                        .values(
                            area_name=area.area_name,
                            description=area.description,
                            area_type=area.area_type,
                            controlling_faction=area.controlling_faction,
                            dominant_species=area.dominant_species,
                            weather=area.weather,
                            quests=area.quests  # if your column supports JSON
                        )
                    )
                    session.execute(stmt)
                else:
                    # Create a new record using the model's constructor
                    new_area = AreaModel(**area_dict)
                    session.add(new_area)
                session.commit()
                area.mark_clean()
                logger.info(f"Saved area: {area.area_name} (ID: {area.area_id})")
                return True
            except Exception as e:
                session.rollback()
                logger.error(f"Failed to save area {area.area_id}: {e}")
                return False
            finally:
                session.close()
        except Exception as e:
            logger.error(f"Error serializing area {area.area_id}: {e}")
            return False

    def delete_entity(self, area_id: str) -> bool:
        """
        Delete an Area entity from the database and remove it from cache.
        """
        self.entities.pop(area_id, None)
        session: Session = SessionLocal()
        try:
            stmt = delete(AreaModel).where(AreaModel.area_id == area_id)
            session.execute(stmt)
            session.commit()
            logger.info(f"Deleted area: {area_id}")
            return True
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to delete area {area_id}: {e}")
            return False
        finally:
            session.close()

    def get_all_entities(self) -> List[Area]:
        """
        Retrieve all Area entities from the database.
        """
        session: Session = SessionLocal()
        try:
            stmt = select(AreaModel)
            results = session.execute(stmt).scalars().all()
            areas = []
            for model in results:
                area = Area.from_dict(model.to_dict())
                self.entities[area.area_id] = area
                areas.append(area)
            return areas
        except Exception as e:
            logger.error(f"Error fetching all areas: {e}")
            return []
        finally:
            session.close()

    def get_entities_at_location(self, location_id: str) -> List[Area]:
        """
        Get all Area entities that match the given location.
        """
        session: Session = SessionLocal()
        try:
            stmt = select(AreaModel).where(AreaModel.location_id == location_id)
            results = session.execute(stmt).scalars().all()
            areas = []
            for model in results:
                area = Area.from_dict(model.to_dict())
                self.entities[area.area_id] = area
                areas.append(area)
            return areas
        except Exception as e:
            logger.error(f"Error fetching areas at location {location_id}: {e}")
            return []
        finally:
            session.close()

    def get_entity_by_name(self, name: str) -> Optional[Area]:
        """
        Retrieve an Area entity by its name.
        """
        session: Session = SessionLocal()
        try:
            stmt = select(AreaModel).where(AreaModel.name == name)
            result = session.execute(stmt).scalars().first()
            if result:
                area = Area.from_dict(result.to_dict())
                self.entities[area.area_id] = area
                return area
            return None
        except Exception as e:
            logger.error(f"Error fetching area by name {name}: {e}")
            return None
        finally:
            session.close()

    def update_entity_location(self, area_id: str, location_id: str) -> bool:
        """
        Update the location of an Area entity.
        """
        area = self.load_entity(area_id)
        if not area:
            logger.warning(f"Cannot update location: Area not found: {area_id}")
            return False
        area.set_location(location_id)
        return self.save_entity(area)

    def save_all_entities(self) -> bool:
        """
        Save all dirty (modified) Area entities.
        """
        success = True
        for area in self.entities.values():
            if area.is_dirty():
                if not self.save_entity(area):
                    success = False
        return success

    def get_entity_count(self) -> int:
        """
        Return the total number of Area entities in the database.
        """
        session: Session = SessionLocal()
        try:
            stmt = select(AreaModel)
            results = session.execute(stmt).scalars().all()
            return len(results)
        except Exception as e:
            logger.error(f"Error counting areas: {e}")
            return 0
        finally:
            session.close()
