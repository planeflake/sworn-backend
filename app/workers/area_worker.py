#!/usr/bin/env python
import json
import uuid
import random
from datetime import datetime

from workers.celery_app import app
from database.connection import SessionLocal
from models.core import (
    Areas, 
    AreaEncounterTypes,
    AreaEncounterOutcomes,
    AreaEncounters,
    AreaSecrets,
    Characters,
    Traders
)

@app.task
def process_area_encounters(world_id=None):
    """
    Process active area encounters and potentially resolve them.
    This would be run periodically to update the state of ongoing encounters.
    """
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
        
        for encounter in active_encounters:
            # Process encounter based on current state
            if encounter.current_state == "initial":
                # Encounter has just been created, mark as in progress
                encounter.current_state = "in_progress"
                print(f"Encounter {encounter.encounter_id} is now in progress")
            
            # Add more logic here to handle progression of multi-stage encounters
            
        db.commit()
        return {"status": "success", "count": len(active_encounters)}
    except Exception as e:
        db.rollback()
        print(f"Error processing area encounters: {str(e)}")
        return {"status": "error", "error": str(e)}
    finally:
        db.close()

@app.task
def generate_encounter(character_id=None, trader_id=None, area_id=None):
    """
    Generate a new encounter when a character or trader enters an area.
    Either character_id or trader_id must be provided, along with area_id.
    The encounter will be based on actual entities in the world when possible.
    """
    if not area_id or (not character_id and not trader_id):
        return {"status": "error", "error": "Must provide area_id and either character_id or trader_id"}
    
    db = SessionLocal()
    try:
        # Get the area
        area = db.query(Areas).filter(Areas.area_id == area_id).first()
        if not area:
            return {"status": "error", "error": f"Area {area_id} not found"}
        
        # Get actor details (character or trader)
        actor_type = "character" if character_id else "trader"
        actor_id = character_id if character_id else trader_id
        actor = None
        
        if actor_type == "character":
            actor = db.query(Characters).filter(Characters.character_id == character_id).first()
            if not actor:
                return {"status": "error", "error": f"Character {character_id} not found"}
        else:
            actor = db.query(Traders).filter(Traders.trader_id == trader_id).first()
            if not actor:
                return {"status": "error", "error": f"Trader {trader_id} not found"}
        
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
            print(f"No encounter generated for {actor_type} {actor_id} in area {area.area_name}")
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
        
        # Check for bandits in this area (would connect to your faction system)
        if any(et.encounter_code == "bandit_ambush" for et in valid_encounters):
            # In a real implementation, you'd query your faction/bandit system
            # For now, simulate with a random chance to create a "faction"
            if random.random() < 0.3:  # 30% chance for bandits
                bandit_encounter = next((et for et in valid_encounters if et.encounter_code == "bandit_ambush"), None)
                if bandit_encounter:
                    entity_based_encounters.append({
                        "encounter_type": bandit_encounter,
                        "entity_id": "local_brigands",  # This would be a real faction/group ID in your system
                        "entity_type": "faction",
                        "faction_id": "brigands_faction",  # Actual faction ID
                        "narrative": "A group of local brigands has set up an ambush in the area.",
                        "probability_boost": 1.5
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
        
        print(f"Generated {selected_encounter.encounter_name} encounter for {actor_type} {actor_id} in {area.area_name}")
        
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
        print(f"Error generating encounter: {str(e)}")
        return {"status": "error", "error": str(e)}
    finally:
        db.close()

@app.task
def resolve_encounter(encounter_id, character_id=None, trader_id=None, chosen_outcome_code=None):
    """
    Resolve an encounter with a specific outcome.
    If no outcome is specified, one will be selected automatically.
    This function handles both standard and entity-based encounters.
    """
    if not encounter_id:
        return {"status": "error", "error": "Must provide encounter_id"}
    
    db = SessionLocal()
    try:
        # Get the encounter
        encounter = db.query(AreaEncounters).filter(AreaEncounters.encounter_id == encounter_id).first()
        if not encounter:
            return {"status": "error", "error": f"Encounter {encounter_id} not found"}
        
        if encounter.is_completed:
            return {"status": "error", "error": f"Encounter {encounter_id} is already completed"}
        
        # Get the encounter type
        encounter_type = db.query(AreaEncounterTypes).filter(
            AreaEncounterTypes.encounter_type_id == encounter.encounter_type_id
        ).first()
        
        if not encounter_type:
            return {"status": "error", "error": f"Encounter type not found for encounter {encounter_id}"}
        
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
            
            elif encounter.entity_type == "faction":
                # This is a faction-based encounter
                faction_id = encounter.faction_id
                if faction_id:
                    # In a real system, you'd get faction details here
                    faction_name = "local brigands"  # Placeholder
                    
                    entity_narrative = f"You encountered a group from the {faction_name}."
                    
                    # Update faction relations based on outcome
                    if chosen_outcome_code == "defeat":
                        additional_rewards["faction_reputation_decrease"] = 5
                        additional_narrative = f" Your victory against them has damaged your standing with the {faction_name}."
                    elif chosen_outcome_code == "negotiate":
                        additional_rewards["faction_reputation_increase"] = 5
                        additional_narrative = f" Your peaceful resolution has improved your standing with the {faction_name}."
        
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
                
                # This could trigger a quest or other game events
        
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
                return {"status": "error", "error": f"Outcome '{chosen_outcome_code}' not valid for this encounter"}
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
            return {"status": "error", "error": "Could not determine outcome"}
        
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
        print(f"Error resolving encounter: {str(e)}")
        return {"status": "error", "error": str(e)}
    finally:
        db.close()