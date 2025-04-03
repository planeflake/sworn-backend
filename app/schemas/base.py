# schemas/base.py
from pydantic import BaseModel, UUID4, validator, Field
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
import uuid
from enum import Enum

class TimeStampModel(BaseModel):
    created_at: Optional[datetime] = None
    last_updated: Optional[datetime] = None

    class Config:
        has_attributes = True