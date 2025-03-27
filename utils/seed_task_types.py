#!/usr/bin/env python3
"""
Seed script to populate initial task types in the database.
Run this after running the migration to create the task tables.

Usage:
    python utils/seed_task_types.py
"""
import sys
import os
import uuid
from datetime import datetime

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.connection import SessionLocal
from app.models.tasks import TaskTypes

def seed_task_types():
    """Seed the basic task types into the database."""
    db = SessionLocal()
    try:
        # Check if we already have task types
        existing_count = db.query(TaskTypes).count()
        if existing_count > 0:
            print(f"Found {existing_count} existing task types. Skipping seed.")
            return
        
        # Define the basic task types
        task_types = [
            {
                "task_type_id": uuid.uuid4(),
                "code": "trader_assistance",
                "name": "Trader Assistance",
                "description": "Help a trader who encountered a problem during their journey.",
                "base_xp": 25,
                "base_gold": 15,
                "icon": "trader_icon",
                "color_hex": "#FF7D3D"
            },
            {
                "code": "resource_gathering",
                "name": "Resource Gathering",
                "description": "Gather specific resources from the surrounding area.",
                "base_xp": 10,
                "base_gold": 5,
                "icon": "resource_icon",
                "color_hex": "#4DA6FF"
            },
            {
                "code": "building_construction",
                "name": "Building Construction",
                "description": "Help construct or repair a building in a settlement.",
                "base_xp": 30,
                "base_gold": 20,
                "icon": "building_icon",
                "color_hex": "#FF4D4D"
            },
            {
                "code": "exploration",
                "name": "Exploration",
                "description": "Explore and map out an area or discover a location.",
                "base_xp": 20,
                "base_gold": 10,
                "icon": "exploration_icon",
                "color_hex": "#4DFF73"
            },
            {
                "code": "crafting",
                "name": "Crafting",
                "description": "Craft specific items from available resources.",
                "base_xp": 15,
                "base_gold": 10,
                "icon": "crafting_icon",
                "color_hex": "#A64DFF"
            },
            {
                "code": "trading",
                "name": "Trading",
                "description": "Complete a trading transaction for a settlement or trader.",
                "base_xp": 20,
                "base_gold": 25,
                "icon": "trading_icon",
                "color_hex": "#FFD34D"
            },
            {
                "code": "escort",
                "name": "Escort Mission",
                "description": "Escort an NPC safely from one location to another.",
                "base_xp": 35,
                "base_gold": 30,
                "icon": "escort_icon",
                "color_hex": "#4DFFB6"
            },
            {
                "code": "defense",
                "name": "Settlement Defense",
                "description": "Help defend a settlement against threats.",
                "base_xp": 40,
                "base_gold": 35,
                "icon": "defense_icon",
                "color_hex": "#FF4DA6"
            }
        ]
        
        # Insert task types
        for task_type in task_types:
            # Add UUID if not present
            if "task_type_id" not in task_type:
                task_type["task_type_id"] = uuid.uuid4()
                
            db.add(TaskTypes(**task_type))
        
        db.commit()
        print(f"Successfully seeded {len(task_types)} task types.")
        
    except Exception as e:
        db.rollback()
        print(f"Error seeding task types: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_task_types()