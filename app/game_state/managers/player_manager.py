from typing import List, Dict, Optional, Any, Type, Union
from sqlalchemy.orm import Session
from database.connection import get_db
from app.models.item import Item
import logging
import uuid
import json

logger = logging.getLogger(__name__)

EntityType = Item

class PlayerManager:
    """
    Template for entity managers that handle persistence and lifecycle.
    
    Managers are responsible for:
    1. Loading entities from the database
    2. Saving entities to the database
    3. Creating new entities
    4. Maintaining a cache of loaded entities
    5. Providing query methods for finding entities
    
    Each entity type should have its own manager class.
    """
    
    def __init__(self):
        """Initialize the manager."""
        # Cache of loaded entities
        self.entities = {}  # Dictionary to store loaded entities by ID
        
        logger.info(f"{self.__class__.__name__} initialized")
    