from workers.celery_app import app, get_building_requirements, get_settlements_config
from random import randint, choice
import json
import time
import os

# Helper to get settlement config by name
def get_settlement_config_by_name(name):
    settlements = get_settlements_config()
    return next((s for s in settlements if s["name"] == name), None)

@app.task
def update_settlement_resources(settlement_id):
    """Update resources for a settlement based on its buildings and surroundings"""
    settlement_data = get_settlement_data(settlement_id)
    if not settlement_data:
        return {"error": f"Settlement {settlement_id} not found"}
    
    # Update resources based on buildings
    if "buildings" in settlement_data:
        for building in settlement_data["buildings"]:
            if building["type"] == "Farm":
                settlement_data["resources"]["food"] = settlement_data["resources"].get("food", 0) + 5
            elif building["type"] == "Mine":
                settlement_data["resources"]["metal"] = settlement_data["resources"].get("metal", 0) + 3
                settlement_data["resources"]["stone"] = settlement_data["resources"].get("stone", 0) + 4
            elif building["type"] == "Workshop":
                if settlement_data["resources"].get("wood", 0) >= 2:
                    settlement_data["resources"]["wood"] -= 2
                    settlement_data["resources"]["tools"] = settlement_data["resources"].get("tools", 0) + 1
    
    # Update based on area type
    if settlement_data["area_type"] == "forest":
        settlement_data["resources"]["wood"] = settlement_data["resources"].get("wood", 0) + 3
        settlement_data["resources"]["berries"] = settlement_data["resources"].get("berries", 0) + 2
    elif settlement_data["area_type"] == "coastal":
        settlement_data["resources"]["fish"] = settlement_data["resources"].get("fish", 0) + 3
        settlement_data["resources"]["salt"] = settlement_data["resources"].get("salt", 0) + 1
    elif settlement_data["area_type"] == "mountains":
        settlement_data["resources"]["stone"] = settlement_data["resources"].get("stone", 0) + 3
        if randint(1, 10) == 1:  # 10% chance
            settlement_data["resources"]["gems"] = settlement_data["resources"].get("gems", 0) + 1
    elif settlement_data["area_type"] == "plains":
        settlement_data["resources"]["wheat"] = settlement_data["resources"].get("wheat", 0) + 4
        settlement_data["resources"]["corn"] = settlement_data["resources"].get("corn", 0) + 3
    
    # Resource consumption by population
    if "population" in settlement_data:
        food_needed = settlement_data["population"] * 0.5  # Each person needs 0.5 food per cycle
        
        # Check various food sources in priority order
        remaining_need = food_needed
        for food_type in ["food", "fish", "wheat", "corn", "berries"]:
            if food_type in settlement_data["resources"]:
                available = settlement_data["resources"][food_type]
                consumed = min(available, remaining_need)
                settlement_data["resources"][food_type] -= consumed
                remaining_need -= consumed
                
                if remaining_need <= 0:
                    break
        
        # If still food needed, population decreases
        if remaining_need > 0:
            starvation = min(int(remaining_need * 0.2), settlement_data["population"])
            settlement_data["population"] -= starvation
            
            if "events" not in settlement_data:
                settlement_data["events"] = []
                
            settlement_data["events"].append({
                "type": "starvation",
                "severity": starvation,
                "timestamp": time.time()
            })
    
    # Save the updated settlement data
    save_settlement_data(settlement_id, settlement_data)
    
    return {
        "settlement": settlement_data["name"],
        "updated": True,
        "population": settlement_data.get("population", 0),
        "resources": settlement_data.get("resources", {})
    }

@app.task
def handle_settlement_events(settlement_id):
    """Handle random events for settlements"""
    settlement_data = get_settlement_data(settlement_id)
    if not settlement_data:
        return {"error": f"Settlement {settlement_id} not found"}
    
    if "events" not in settlement_data:
        settlement_data["events"] = []
    
    # Handle threats
    if "threats" in settlement_data:
        for threat in settlement_data["threats"]:
            if threat == "wolves" and randint(1, 10) == 1:  # 10% chance
                # Wolf attack!
                livestock_loss = min(randint(1, 3), settlement_data["resources"].get("livestock", 0))
                settlement_data["resources"]["livestock"] = settlement_data["resources"].get("livestock", 0) - livestock_loss
                
                settlement_data["events"].append({
                    "type": "wolf_attack",
                    "damage": livestock_loss,
                    "timestamp": time.time()
                })
            
            elif threat == "bandits" and randint(1, 20) == 1:  # 5% chance
                # Bandit raid!
                # The more valuable resources get targeted first
                for resource in ["gems", "metal", "tools", "medicine"]:
                    if resource in settlement_data["resources"] and settlement_data["resources"][resource] > 0:
                        loss = min(randint(1, 5), settlement_data["resources"][resource])
                        settlement_data["resources"][resource] -= loss
                        break
                
                settlement_data["events"].append({
                    "type": "bandit_raid",
                    "timestamp": time.time()
                })
            
            elif threat == "storms" and randint(1, 15) == 1:  # ~7% chance
                # Storm damage!
                building_damage = False
                if "buildings" in settlement_data and settlement_data["buildings"]:
                    damaged_building = choice(settlement_data["buildings"])
                    damaged_building["condition"] = max(damaged_building.get("condition", 100) - randint(10, 30), 0)
                    building_damage = True
                
                settlement_data["events"].append({
                    "type": "storm",
                    "building_damage": building_damage,
                    "timestamp": time.time()
                })
    
    # Save the updated settlement data
    save_settlement_data(settlement_id, settlement_data)
    
    return {
        "settlement": settlement_data["name"],
        "events_processed": True
    }

@app.task
def create_settlement(name):
    """Create a new settlement from configuration"""
    settlement_config = get_settlement_config_by_name(name)
    if not settlement_config:
        return {"error": f"No configuration found for settlement: {name}"}
    
    # Generate a unique ID
    settlement_id = f"s_{int(time.time())}_{name.lower().replace(' ', '_')}"
    
    # Create settlement data from config
    settlement_data = {
        "id": settlement_id,
        "name": name,
        "area_type": settlement_config.get("area_type", "forest"),
        "buildings": [],
        "cycle_period": "Day",
        "trader_visiting": False,
        "missing_resources": settlement_config.get("missing_resources", []),
        "threats": settlement_config.get("threats", []),
        "resources": {
            "food": 20,
            "wood": 0,
            "stone": 0,
            "water": 10,
            "population": 5
        },
        "events": []
    }
    
    # Apply initial resources from config
    if "initial_resources" in settlement_config:
        for resource, amount in settlement_config["initial_resources"].items():
            settlement_data["resources"][resource] = amount
    
    # Save the settlement
    save_settlement_data(settlement_id, settlement_data)
    
    return {
        "id": settlement_id,
        "name": name,
        "created": True
    }

def get_settlement_data(settlement_id):
    """Get settlement data from storage"""
    # This would typically load from a database
    data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "settlements")
    os.makedirs(data_dir, exist_ok=True)
    
    settlement_file = os.path.join(data_dir, f"{settlement_id}.json")
    if os.path.exists(settlement_file):
        with open(settlement_file, 'r') as f:
            return json.load(f)
    return None

def save_settlement_data(settlement_id, data):
    """Save settlement data to storage"""
    # This would typically save to a database
    data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "settlements")
    os.makedirs(data_dir, exist_ok=True)
    
    settlement_file = os.path.join(data_dir, f"{settlement_id}.json") 
    with open(settlement_file, 'w') as f:
        json.dump(data, f, indent=2)
        
def ensure_data_directory():
    """Ensure the data directory exists"""
    data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "settlements")
    os.makedirs(data_dir, exist_ok=True)
    return data_dir

@app.task
def update_all_settlements():
    """Update resources for all settlements"""
    # Get list of settlement files from the data directory
    data_dir = ensure_data_directory()
    
    settlement_files = [f for f in os.listdir(data_dir) if f.endswith('.json')]
    
    if not settlement_files:
        # Trigger settlement initialization if no settlements exist
        initialize_all_settlements.delay()
        return {"status": "No settlements found, triggering initialization"}
    
    settlement_ids = []
    for i, settlement_file in enumerate(settlement_files):
        settlement_id = settlement_file[:-5]  # Remove .json extension
        settlement_ids.append(settlement_id)
        
        # Stagger task execution to prevent all settlements updating simultaneously
        update_settlement_resources.apply_async(
            args=[settlement_id],
            countdown=1 * i  # Stagger by 1 second per settlement
        )
    
    return {
        "status": "Settlement update tasks dispatched", 
        "count": len(settlement_ids),
        "settlement_ids": settlement_ids
    }

@app.task
def process_all_settlement_events():
    """Process events for all settlements"""
    data_dir = ensure_data_directory()
    
    settlement_files = [f for f in os.listdir(data_dir) if f.endswith('.json')]
    
    if not settlement_files:
        # No need to process events if no settlements exist
        return {"status": "No settlements found"}
    
    settlement_ids = []
    for i, settlement_file in enumerate(settlement_files):
        settlement_id = settlement_file[:-5]  # Remove .json extension
        settlement_ids.append(settlement_id)
        
        # Stagger task execution to prevent all settlements processing simultaneously
        handle_settlement_events.apply_async(
            args=[settlement_id],
            countdown=1 * i  # Stagger by 1 second per settlement
        )
    
    return {
        "status": "Settlement event processing tasks dispatched", 
        "count": len(settlement_ids),
        "settlement_ids": settlement_ids
    }

@app.task
def initialize_all_settlements():
    """Initialize all settlements from config"""
    # Ensure the data directory exists
    data_dir = ensure_data_directory()
    
    # Check if settlements already exist
    settlement_files = [f for f in os.listdir(data_dir) if f.endswith('.json')]
    if settlement_files:
        return {"status": "Settlements already exist, skipping initialization"}
    
    settlements = get_settlements_config()
    settlement_names = []
    
    for i, settlement in enumerate(settlements):
        settlement_names.append(settlement["name"])
        
        # Stagger task execution to prevent all settlements initializing simultaneously
        create_settlement.apply_async(
            args=[settlement["name"]],
            countdown=1 * i  # Stagger by 1 second per settlement
        )
    
    return {
        "status": "Settlement initialization tasks dispatched", 
        "count": len(settlement_names),
        "settlement_names": settlement_names
    }