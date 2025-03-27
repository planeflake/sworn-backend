# app/ai/decision/trader_decision.py
from app.ai.mcts.core import MCTS
from app.ai.mcts.states.item_state import ItemState
import logging
import random

logger = logging.getLogger(__name__)

class ItemDecisionMaker:
    def __init__(self, db_session, num_simulations=100):
        self.db = db_session
        self.num_simulations = num_simulations