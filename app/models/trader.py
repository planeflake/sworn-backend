from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, String, Integer, Boolean, Text, JSON

Base = declarative_base()

class TraderModel(Base):
    __tablename__ = 'traders'

    trader_id = Column(String, primary_key=True)
    npc_name = Column(String, nullable=False)
    description = Column(Text)
    trader_type = Column(String, default='merchant')
    current_location_id = Column(String, nullable=True)
    destination_id = Column(String, nullable=True)
    home_settlement_id = Column(String, nullable=True)
    # For properties that are naturally lists or dictionaries,
    # you can use JSON columns if your database supports it.
    preferred_biomes = Column(JSON, default=[])
    preferred_settlements = Column(JSON, default=[])
    unacceptable_settlements = Column(JSON, default=[])
    visited_settlements = Column(JSON, default=[])
    faction_id = Column(String, nullable=True)
    reputation = Column(JSON, default={})  # e.g. settlement_id -> reputation value
    relations = Column(JSON, default={})   # e.g. entity_id -> relation value
    gold = Column(Integer, default=0)
    inventory = Column(JSON, default={})   # item_id -> quantity
    inventory_capacity = Column(Integer, default=100)
    buy_prices = Column(JSON, default={})
    sell_prices = Column(JSON, default={})
    trade_priorities = Column(JSON, default={})
    trade_routes = Column(JSON, default=[])
    is_traveling = Column(Boolean, default=False)
    is_settled = Column(Boolean, default=False)
    is_retired = Column(Boolean, default=False)
    has_shop = Column(Boolean, default=False)
    shop_location_id = Column(String, nullable=True)
    can_move = Column(Boolean, default=True)
    active_task_id = Column(String, nullable=True)
    traits = Column(JSON, default=[])
    skills = Column(JSON, default={})
    life_goals = Column(JSON, default=[])
    available_quests = Column(JSON, default=[])
    locked_quests = Column(JSON, default=[])
    completed_quests = Column(JSON, default=[])
    known_secrets = Column(JSON, default=[])
