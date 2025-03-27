from pydantic import BaseModel
from uuid import uuid4

class Resource(BaseModel):
    id: uuid4
    name: str
    description: str
    type: str
    core_biome: str
    rarity: int
    value: int
    weight: int