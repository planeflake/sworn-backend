# workers/area_worker_new.py
from app.workers.celery_app import app
from database.connection import SessionLocal, get_db
import logging
import random
import json
from typing import Dict, List, Optional, Any
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)

from app.models.core import (
    Areas, 
    AreaEncounterTypes,
    AreaEncounterOutcomes,
    AreaEncounters,
    AreaSecrets,
    Characters,
    Traders,
    Settlements
)

@app.task
def process_area_encounters(world_id: Optional[str] = None):
    """
    Process active area encounters and potentially resolve them.
    
    Args:
        world_id (str, optional): The ID of the world to limit processing to
        
    Returns:
        Dict[str, Any]: Result of the encounter processing
    """
    logger.info(f"Processing active encounters" + (f" in world {world_id}" if world_id else ""))
    
    db = SessionLocal()
    try:
        # Get active encounters
        query = db.query(AreaEncounters).filter(
            AreaEncounters.is_active == True,
            AreaEncounters.is_completed == False
        )
        
        # Filter by world if provided (via area's world_id)
        if world_id:
            query = query.join(Areas).filter(Areas.world_id == world_id)
            
        active_encounters = query.all()
        
        processed_count = 0
        for encounter in active_encounters:
            try:
                # Process encounter based on current state
                if encounter.current_state == "initial":
                    # Encounter has just been created, mark as in progress
                    encounter.current_state = "in_progress"
                    logger.info(f"Encounter {encounter.encounter_id} is now in progress")
                    processed_count += 1
                
                # Progress existing encounters based on elapsed time
                elif encounter.current_state == "in_progress":
                    # Determine if encounter should progress to next stage or be auto-resolved
                    created_time = encounter.created_at
                    current_time = datetime.now()
                    time_diff = (current_time - created_time).total_seconds() / 60  # minutes
                    
                    # Auto-resolve encounters that are more than 24 hours old
                    if time_diff > 1440:  # 24 hours in minutes
                        # Auto-resolve with neutral outcome
                        outcome = "neutral"
                        resolve_encounter.delay(str(encounter.encounter_id), None, None, outcome)
                        logger.info(f"Auto-resolving stale encounter {encounter.encounter_id} with {outcome} outcome")
                        processed_count += 1
                
                # Add more logic here to handle progression of multi-stage encounters
                
            except Exception as e:
                logger.exception(f"Error processing encounter {encounter.encounter_id}: {e}")
        
        db.commit()
        
        return {
            "status": "success",
            "total_encounters": len(active_encounters),
            "processed": processed_count
        }
        
    except Exception as e:
        db.rollback()
        logger.exception(f"Error processing area encounters: {e}")
        return {"status": "error", "message": f"Error: {str(e)}"}
    finally:
        db.close()

@app.task
def generate_encounter(character_id=None, trader_id=None, area_id=None):
    """
    Generate a new encounter when a character or trader enters an area.
    
    Args:
        character_id (str, optional): The ID of the character entering the area
        trader_id (str, optional): The ID of the trader entering the area
        area_id (str): The ID of the area
        
    Returns:
        Dict[str, Any]: Result of the encounter generation
    """
    if not area_id or (not character_id and not trader_id):
        return {"status": "error", "message": "Must provide area_id and either character_id or trader_id"}
    
    logger.info(f"Generating encounter in area {area_id} for {'character' if character_id else 'trader'} {character_id or trader_id}")
    
    db = SessionLocal()
    try:
        # Get the area
        area = db.query(Areas).filter(Areas.area_id == area_id).first()
        if not area:
            return {"status": "error", "message": f"Area {area_id} not found"}
        
        # Get actor details (character or trader)
        actor_type = "character" if character_id else "trader"
        actor_id = character_id if character_id else trader_id
        actor = None
        
        if actor_type == "character":
            actor = db.query(Characters).filter(Characters.character_id == character_id).first()
            if not actor:
                return {"status": "error", "message": f"Character {character_id} not found"}
        else:
            actor = db.query(Traders).filter(Traders.trader_id == trader_id).first()
            if not actor:
                return {"status": "error", "message": f"Trader {trader_id} not found"}
        
        # Determine whether an encounter happens (based on area danger level)
        encounter_chance = 0.1 + (area.danger_level * 0.05)  # 10% base chance + 5% per danger level
        
        # Check for area secrets - they increase encounter chance
        area_secrets = db.query(AreaSecrets).filter(
            AreaSecrets.area_id == area_id,
            AreaSecrets.is_discovered == False
        ).all()
        
        # Adjust encounter chance based on number of undiscovered secrets
        if area_secrets:
            # Increase encounter chance by 2% per undiscovered secret
            encounter_chance += len(area_secrets) * 0.02
            
        encounter_roll = random.random()
        
        if encounter_roll > encounter_chance:
            # No encounter this time
            logger.info(f"No encounter generated for {actor_type} {actor_id} in area {area.area_name}")
            return {"status": "success", "result": "no_encounter"}
        
        # Get possible encounter types for this area
        encounter_types = db.query(AreaEncounterTypes).filter(
            AreaEncounterTypes.min_danger_level <= area.danger_level
        ).all()
        
        valid_encounters = []
        for encounter_type in encounter_types:
            # Check if this encounter is compatible with the area type
            if not encounter_type.compatible_area_types:
                continue
                
            compatible_areas = json.loads(encounter_type.compatible_area_types)
            if area.area_type in compatible_areas:
                valid_encounters.append(encounter_type)
        
        if not valid_encounters:
            # Add the uneventful travel encounter as fallback
            uneventful = db.query(AreaEncounterTypes).filter(
                AreaEncounterTypes.encounter_code == "uneventful_travel"
            ).first()
            
            if uneventful:
                valid_encounters.append(uneventful)
            else:
                return {"status": "success", "result": "no_encounter"}
        
        # First, check if we can generate an entity-specific encounter based on the area
        
        # Find potential entities for each encounter type
        entity_based_encounters = []
        
        # Check for injured/lost traders in this area
        if any(et.encounter_code in ["lost_merchant", "injured_traveler"] for et in valid_encounters):
            # Find any traders that might be stuck/lost in this area
            # This could be based on trader state in your game logic
            nearby_traders = db.query(Traders).filter(
                Traders.current_settlement_id.is_(None),  # Traders not in a settlement
                # Additional criteria like trader health, etc. would go here
            ).limit(2).all()
            
            if nearby_traders:
                for trader in nearby_traders:
                    for et in valid_encounters:
                        if et.encounter_code == "lost_merchant":
                            entity_based_encounters.append({
                                "encounter_type": et,
                                "entity_id": trader.trader_id,
                                "entity_type": "trader",
                                "narrative": f"You come across {trader.npc_name}, a trader who seems to have lost their way.",
                                "probability_boost": 2.0  # Make this more likely than random encounters
                            })
                        elif et.encounter_code == "injured_traveler" and random.random() < 0.5:  # 50% chance trader is injured
                            entity_based_encounters.append({
                                "encounter_type": et,
                                "entity_id": trader.trader_id,
                                "entity_type": "trader",
                                "narrative": f"You find {trader.npc_name}, a trader who has been injured while traveling.",
                                "probability_boost": 2.0
                            })
        
        # Check for secrets that might be discovered
        if area_secrets and random.random() < 0.2:  # 20% chance to encounter a secret
            # Pick a random undiscovered secret
            secret = random.choice(area_secrets)
            
            # Find a neutral encounter type to use as a vessel for discovering the secret
            secret_encounter = next((et for et in valid_encounters 
                                  if et.encounter_category in ["neutral", "reward"]), None)
            
            if secret_encounter:
                entity_based_encounters.append({
                    "encounter_type": secret_encounter,
                    "secret_id": secret.secret_id,
                    "secret_revealed": True,
                    "narrative": f"While traveling, you notice something unusual: {secret.description}",
                    "probability_boost": 1.5
                })
        
        # Select an encounter - first check if we have entity-based ones
        selected_encounter_data = None
        selected_encounter = None
        
        if entity_based_encounters and random.random() < 0.8:  # 80% chance to use entity-based over random
            # Select an entity-based encounter with weighted probability
            total_weight = sum(e.get("probability_boost", 1.0) for e in entity_based_encounters)
            roll = random.random() * total_weight
            cumulative = 0
            
            for encounter_data in entity_based_encounters:
                cumulative += encounter_data.get("probability_boost", 1.0)
                if roll <= cumulative:
                    selected_encounter_data = encounter_data
                    selected_encounter = encounter_data["encounter_type"]
                    break
                    
            if not selected_encounter_data and entity_based_encounters:
                selected_encounter_data = entity_based_encounters[0]
                selected_encounter = selected_encounter_data["encounter_type"]
        
        # If no entity-based encounter was selected, use the standard selection process
        if not selected_encounter:
            # Normalize rarities and calculate cumulative probabilities
            total_rarity = sum(et.rarity for et in valid_encounters)
            cumulative_prob = 0
            encounter_probs = []
            
            for et in valid_encounters:
                probability = et.rarity / total_rarity
                cumulative_prob += probability
                encounter_probs.append((et, cumulative_prob))
            
            # Roll and select
            roll = random.random()
            for et, threshold in encounter_probs:
                if roll <= threshold:
                    selected_encounter = et
                    break
            
            # If somehow we didn't select one (shouldn't happen), use the last one
            if not selected_encounter and encounter_probs:
                selected_encounter = encounter_probs[-1][0]
            
        if not selected_encounter:
            return {"status": "success", "result": "no_encounter"}
        
        # Create the encounter
        encounter_id = str(uuid.uuid4())
        new_encounter = AreaEncounters(
            encounter_id=encounter_id,
            area_id=area_id,
            encounter_type_id=selected_encounter.encounter_type_id,
            is_active=True,
            is_completed=False,
            current_state="initial",
            created_at=datetime.now(),
            resolved_at=None,
            resolved_by=None,
            resolution_outcome_id=None,
            custom_narrative=None
        )
        
        # If this is an entity-based encounter, add entity details
        if selected_encounter_data:
            if "entity_id" in selected_encounter_data:
                new_encounter.entity_id = selected_encounter_data["entity_id"]
                new_encounter.entity_type = selected_encounter_data.get("entity_type")
                
            if "faction_id" in selected_encounter_data:
                new_encounter.faction_id = selected_encounter_data["faction_id"]
                
            if "secret_id" in selected_encounter_data:
                new_encounter.secret_id = selected_encounter_data["secret_id"]
                new_encounter.secret_revealed = selected_encounter_data.get("secret_revealed", False)
                
            if "narrative" in selected_encounter_data:
                new_encounter.custom_narrative = selected_encounter_data["narrative"]
        
        db.add(new_encounter)
        db.commit()
        
        logger.info(f"Generated {selected_encounter.encounter_name} encounter for {actor_type} {actor_id} in {area.area_name}")
        
        # Prepare the response
        description = new_encounter.custom_narrative or selected_encounter.description
        
        return {
            "status": "success", 
            "result": "encounter_created",
            "encounter_id": encounter_id,
            "encounter_name": selected_encounter.encounter_name,
            "encounter_type": selected_encounter.encounter_code,
            "description": description,
            "entity_based": selected_encounter_data is not None
        }
    except Exception as e:
        db.rollback()
        logger.exception(f"Error generating encounter: {e}")
        return {"status": "error", "message": f"Error: {str(e)}"}
    finally:
        db.close()

@app.task
def resolve_encounter(encounter_id: str, character_id=None, trader_id=None, chosen_outcome_code=None):
    """
    Resolve an encounter with a specific outcome.
    
    Args:
        encounter_id (str): The ID of the encounter to resolve
        character_id (str, optional): The ID of the character resolving the encounter
        trader_id (str, optional): The ID of the trader resolving the encounter
        chosen_outcome_code (str, optional): The outcome code to use, or None for random
        
    Returns:
        Dict[str, Any]: Result of the encounter resolution
    """
    if not encounter_id:
        return {"status": "error", "message": "Must provide encounter_id"}
    
    logger.info(f"Resolving encounter {encounter_id} with outcome {chosen_outcome_code or 'random'}")
    
    db = SessionLocal()
    try:
        # Get the encounter
        encounter = db.query(AreaEncounters).filter(AreaEncounters.encounter_id == encounter_id).first()
        if not encounter:
            return {"status": "error", "message": f"Encounter {encounter_id} not found"}
        
        if encounter.is_completed:
            return {"status": "error", "message": f"Encounter {encounter_id} is already completed"}
        
        # Get the encounter type
        encounter_type = db.query(AreaEncounterTypes).filter(
            AreaEncounterTypes.encounter_type_id == encounter.encounter_type_id
        ).first()
        
        if not encounter_type:
            return {"status": "error", "message": f"Encounter type not found for encounter {encounter_id}"}
        
        # Get area information
        area = db.query(Areas).filter(Areas.area_id == encounter.area_id).first()
        area_name = area.area_name if area else "the area"
        
        # Check if this is an entity-based encounter
        entity_narrative = None
        additional_rewards = {}
        additional_narrative = ""
        
        # Handle specific entity types
        if encounter.entity_type and encounter.entity_id:
            if encounter.entity_type == "trader":
                # This is a trader-based encounter
                trader = db.query(Traders).filter(Traders.trader_id == encounter.entity_id).first()
                if trader:
                    entity_narrative = f"You encountered {trader.npc_name}, a trader who was {encounter_type.encounter_name.lower()}."
                    
                    # Update trader state if they were helped
                    if chosen_outcome_code in ["help", "guide", "heal"]:
                        # Update trader state, make them grateful, etc.
                        # This would connect to your trader system
                        additional_rewards["reputation"] = 10
                        additional_narrative = f" {trader.npc_name} is grateful for your assistance."
        
        # Check if this encounter reveals a secret
        if encounter.secret_revealed and encounter.secret_id:
            secret = db.query(AreaSecrets).filter(AreaSecrets.secret_id == encounter.secret_id).first()
            if secret and not secret.is_discovered:
                # Mark the secret as discovered
                secret.is_discovered = True
                secret.discovered_by = character_id if character_id else trader_id
                secret.discovered_at = datetime.now()
                
                # Add rewards from the secret
                if secret.rewards:
                    try:
                        secret_rewards = json.loads(secret.rewards)
                        for reward_type, reward_value in secret_rewards.items():
                            additional_rewards[f"secret_{reward_type}"] = reward_value
                    except json.JSONDecodeError:
                        pass
                
                entity_narrative = f"You discovered {secret.secret_name} in {area_name}!"
                additional_narrative = f" {secret.description}"
        
        # Get possible outcomes
        possible_outcomes = json.loads(encounter_type.possible_outcomes) if encounter_type.possible_outcomes else []
        outcomes = db.query(AreaEncounterOutcomes).filter(
            AreaEncounterOutcomes.outcome_id.in_(possible_outcomes)
        ).all()
        
        if not outcomes:
            # If no outcomes defined, mark as completed with no specific outcome
            encounter.is_completed = True
            encounter.is_active = False
            encounter.current_state = "resolved"
            encounter.resolved_at = datetime.now()
            encounter.resolved_by = character_id if character_id else trader_id
            db.commit()
            
            # Even with no predefined outcomes, we might have entity-specific results
            if entity_narrative:
                return {
                    "status": "success",
                    "result": "encounter_resolved",
                    "encounter_id": encounter_id,
                    "outcome": "entity_resolution",
                    "narrative": entity_narrative + additional_narrative,
                    "rewards": additional_rewards,
                    "penalties": {}
                }
            
            return {
                "status": "success",
                "result": "encounter_resolved",
                "encounter_id": encounter_id,
                "outcome": "default_resolution"
            }
        
        # Determine which outcome to use
        selected_outcome = None
        
        if chosen_outcome_code:
            # User selected a specific outcome
            for outcome in outcomes:
                if outcome.outcome_code == chosen_outcome_code:
                    selected_outcome = outcome
                    break
                    
            if not selected_outcome:
                return {"status": "error", "message": f"Outcome '{chosen_outcome_code}' not valid for this encounter"}
        else:
            # Automatically select an outcome based on probabilities
            total_prob = sum(o.probability for o in outcomes)
            cumulative_prob = 0
            outcome_probs = []
            
            for o in outcomes:
                probability = o.probability / total_prob
                cumulative_prob += probability
                outcome_probs.append((o, cumulative_prob))
            
            roll = random.random()
            for o, threshold in outcome_probs:
                if roll <= threshold:
                    selected_outcome = o
                    break
            
            # If somehow we didn't select one (shouldn't happen), use the last one
            if not selected_outcome and outcome_probs:
                selected_outcome = outcome_probs[-1][0]
        
        if not selected_outcome:
            return {"status": "error", "message": "Could not determine outcome"}
        
        # Apply the outcome
        encounter.is_completed = True
        encounter.is_active = False
        encounter.current_state = "resolved"
        encounter.resolved_at = datetime.now()
        encounter.resolved_by = character_id if character_id else trader_id
        encounter.resolution_outcome_id = selected_outcome.outcome_id
        
        # Apply entity-specific effects
        if encounter.entity_type == "trader" and encounter.entity_id:
            trader = db.query(Traders).filter(Traders.trader_id == encounter.entity_id).first()
            if trader:
                # Update trader based on outcome
                if selected_outcome.outcome_type == "success":
                    # If a lost trader was helped, update their location
                    if encounter_type.encounter_code == "lost_merchant":
                        # Get nearest settlement to guide them to
                        # In a real implementation, you'd find the closest settlement
                        settlements = db.query(Settlements).limit(1).all()
                        if settlements:
                            trader.current_settlement_id = settlements[0].settlement_id
                    
                    # If trader was injured and healed, update health/status
                    if encounter_type.encounter_code == "injured_traveler":
                        # Update trader health or status
                        pass
        
        db.commit()
        
        # Gather rewards and narrative
        base_rewards = json.loads(selected_outcome.rewards) if selected_outcome.rewards else {}
        penalties = json.loads(selected_outcome.penalties) if selected_outcome.penalties else {}
        
        # Combine base and additional rewards
        rewards = {**base_rewards, **additional_rewards}
        
        # Prepare narrative
        if entity_narrative:
            narrative = entity_narrative + " " + selected_outcome.narrative + additional_narrative
        else:
            narrative = selected_outcome.narrative + additional_narrative
        
        return {
            "status": "success",
            "result": "encounter_resolved",
            "encounter_id": encounter_id,
            "outcome_name": selected_outcome.outcome_name,
            "outcome_type": selected_outcome.outcome_type,
            "narrative": narrative,
            "rewards": rewards,
            "penalties": penalties,
            "entity_based": encounter.entity_id is not None or encounter.secret_id is not None
        }
    except Exception as e:
        db.rollback()
        logger.exception(f"Error resolving encounter: {e}")
        return {"status": "error", "message": f"Error: {str(e)}"}
    finally:
        db.close()

@app.task
def update_area_danger_levels(world_id: Optional[str] = None):
    """
    Update the danger levels of areas based on recent encounter outcomes.
    
    Args:
        world_id (str, optional): The ID of the world to update area danger levels for
        
    Returns:
        Dict[str, Any]: Result of the update
    """
    logger.info(f"Updating area danger levels" + (f" in world {world_id}" if world_id else ""))
    
    db = SessionLocal()
    try:
        # Query areas
        query = db.query(Areas)
        if world_id:
            query = query.filter(Areas.world_id == world_id)
        
        areas = query.all()
        updated_count = 0
        
        for area in areas:
            try:
                # Get recent resolved encounters in this area
                recent_encounters = db.query(AreaEncounters).filter(
                    AreaEncounters.area_id == area.area_id,
                    AreaEncounters.is_completed == True,
                    AreaEncounters.resolved_at > datetime.now().replace(day=1)  # Encounters from this month
                ).all()
                
                if not recent_encounters:
                    continue
                
                # Count encounters by outcome type
                outcome_counts = {"combat": 0, "danger": 0, "neutral": 0, "peaceful": 0}
                
                for encounter in recent_encounters:
                    if encounter.resolution_outcome_id:
                        outcome = db.query(AreaEncounterOutcomes).filter(
                            AreaEncounterOutcomes.outcome_id == encounter.resolution_outcome_id
                        ).first()
                        
                        if outcome and outcome.outcome_type in outcome_counts:
                            outcome_counts[outcome.outcome_type] += 1
                
                # Calculate danger level adjustment
                total_encounters = sum(outcome_counts.values())
                if total_encounters < 3:
                    continue  # Not enough data to adjust
                
                combat_ratio = (outcome_counts["combat"] + outcome_counts["danger"]) / total_encounters
                peaceful_ratio = (outcome_counts["peaceful"] + outcome_counts["neutral"]) / total_encounters
                
                # Adjust danger level
                original_level = area.danger_level
                if combat_ratio > 0.7:  # More than 70% dangerous encounters
                    area.danger_level = min(10, area.danger_level + 1)
                elif peaceful_ratio > 0.8:  # More than 80% peaceful encounters
                    area.danger_level = max(1, area.danger_level - 1)
                
                if area.danger_level != original_level:
                    updated_count += 1
                    logger.info(f"Updated danger level for area {area.area_name} from {original_level} to {area.danger_level}")
            
            except Exception as e:
                logger.exception(f"Error updating danger level for area {area.area_id}: {e}")
        
        db.commit()
        
        return {
            "status": "success",
            "total_areas": len(areas),
            "updated": updated_count
        }
        
    except Exception as e:
        db.rollback()
        logger.exception(f"Error updating area danger levels: {e}")
        return {"status": "error", "message": f"Error: {str(e)}"}
    finally:
        db.close()