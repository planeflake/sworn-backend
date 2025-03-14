from celery import Celery
import json
import os
import uuid

# Configure paths
CONFIG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config")

# Initialize the Celery app - central hub for all tasks
app = Celery(
    "sworn_rpg",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/0",
    include=[
        'workers.trader_tasks',
        'workers.settlement_tasks',
        'workers.mcts_trader.tasks'
    ]
)

# Load configuration from celeryconfig.py
app.config_from_object('workers.celeryconfig')

# Load configuration data
def load_config(filename):
    config_path = os.path.join(CONFIG_DIR, filename)
    with open(config_path, 'r') as f:
        return json.load(f)

# Load all game configurations
def load_game_configs():
    game_config = load_config("game_config.json")
    trader_config = load_config("trader_config.json")
    settlement_config = load_config("settlement_config.json")
    
    # Extract settlement needs into a separate dictionary for easy access
    settlement_needs = {}
    for settlement in settlement_config["settlements"]:
        if "needs" in settlement:
            settlement_needs[settlement["name"]] = settlement["needs"]
    
    return {
        # Game mechanics
        "building_requirements": game_config["building_requirements"],
        "hunting_chances": game_config["hunting_chances"],
        "area_wildlife": game_config["area_wildlife"],
        "hunting_options": game_config["hunting_options"],
        "location_resources": game_config["location_resources"],
        "resource_yields": game_config["resource_yields"],
        "daily_task_types": game_config["daily_task_types"],
        "player_task_types": game_config["player_task_types"],
        
        # Traders
        "traders": trader_config["traders"],
        
        # Settlements
        "settlements_config": settlement_config["settlements"],
        "settlement_needs": settlement_needs
    }

# Global game config - accessible throughout the application
game_data = load_game_configs()

# Set up Celery Beat schedule for all periodic tasks
app.conf.beat_schedule = {
    # Trader tasks
    'move-traders-every-60-seconds': {
        'task': 'workers.trader_tasks.update_all_traders',
        'schedule': 60.0,
    },
    'trade-every-hour': {
        'task': 'workers.trader_tasks.trader_buy_and_sell',
        'schedule': 90.0,
    },
    
    # MCTS Trader tasks
    'update-traders-with-mcts': {
        'task': 'workers.mcts_trader.tasks.update_all_traders_mcts',
        'schedule': 3600.0,  # Run every hour
    },
    'train-trader-neural-network': {
        'task': 'workers.mcts_trader.tasks.train_trader_nn',
        'schedule': 21600.0,  # Run every 6 hours
    },
    
    # Settlement tasks
    'update-settlements-hourly': {
        'task': 'workers.settlement_tasks.update_all_settlements',
        'schedule': 25.0,
    },
    'process-settlement-events': {
        'task': 'workers.settlement_tasks.process_all_settlement_events',
        'schedule': 45.0,
    },
    
    # Run once at startup to initialize settlements if they don't exist
    'initialize-settlements-at-startup': {
        'task': 'workers.settlement_tasks.initialize_all_settlements',
        'schedule': 10.0,  # Run after 10 seconds from startup
        'options': {'expires': 60.0},  # Task expires after 60 seconds (runs only once)
    },
}

# Convenience functions for accessing data
def get_traders():
    return game_data["traders"]

def get_settlement_needs():
    return game_data["settlement_needs"]

def get_building_requirements():
    return game_data["building_requirements"]

def get_settlements_config():
    return game_data["settlements_config"]

class Settlement:
    def __init__(self, name, area_type='forest', missing_resources=None, threats=None, initial_resources=None):
        self.id = str(uuid.uuid4())
        self.name = name
        self.area_type = area_type
        self.buildings = []
        self.cycle_period = 'Day'
        self.trader_visiting = False
        
        # Basic setup code kept for backward compatibility
        # Detailed implementation moved to settlement_tasks.py
        self.missing_resources = missing_resources if missing_resources is not None else []
        self.threats = threats if threats is not None else []
        self.resources = {}
        
        # Initialize with basic resources
        resource_yields = game_data["resource_yields"]
        all_resources = set()
        for item, yields in resource_yields.items():
            for resource in yields.keys():
                all_resources.add(resource)
        
        for resource in all_resources:
            self.resources[resource] = 0
            
        # Add additional basic resources
        basic_resources = [
            'food', 'wood', 'stone', 'water', 'population', 'defense',
            'iron', 'iron_ore', 'metal', 'copper', 'copper_ore',
            'hardwood', 'softwood', 'hide', 'bone', 'cloth'
        ]
        
        for resource in basic_resources:
            if resource not in self.resources:
                self.resources[resource] = 0
                
        # Set defaults
        self.resources['food'] = 20
        
        # Apply initial resources
        if initial_resources:
            for resource, amount in initial_resources.items():
                self.resources[resource] = amount