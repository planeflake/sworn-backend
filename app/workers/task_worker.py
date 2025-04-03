# app/workers/task_worker.py
import logging
from celery import shared_task
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

from sqlalchemy.orm import Session
from database.connection import SessionLocal
from app.game_state.services.task_service import TaskService

logger = logging.getLogger(__name__)

@shared_task(name="app.workers.task_worker.process_expired_tasks")
def process_expired_tasks() -> Dict[str, Any]:
    """
    Celery task to check for and process expired tasks.
    This should be run on a schedule, e.g. once per hour.
    
    Returns:
        Dict with results of processing
    """
    logger.info("Processing expired tasks")
    
    try:
        db = SessionLocal()
        try:
            task_service = TaskService(db)
            result = task_service.check_expired_tasks()
            return result
        finally:
            db.close()
    except Exception as e:
        logger.exception(f"Error processing expired tasks: {e}")
        return {
            "status": "error",
            "message": f"Error processing expired tasks: {str(e)}",
            "expired_count": 0
        }

@shared_task(name="app.workers.task_worker.clean_completed_tasks")
def clean_completed_tasks(days_old: int = 30) -> Dict[str, Any]:
    """
    Celery task to archive or clean up old completed/failed tasks.
    This should be run on a schedule, e.g. once per day.
    
    Args:
        days_old: Tasks older than this many days will be cleaned up
        
    Returns:
        Dict with results of cleaning
    """
    logger.info(f"Cleaning up tasks older than {days_old} days")
    
    try:
        db = SessionLocal()
        try:
            from sqlalchemy import text
            from datetime import datetime, timedelta
            
            # Calculate cutoff date
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)
            
            # Update tasks older than the cutoff to inactive
            result = db.execute(
                text("""
                UPDATE tasks
                SET is_active = false
                WHERE (status = 'completed' OR status = 'failed')
                AND completion_time < :cutoff_date
                AND is_active = true
                """),
                {"cutoff_date": cutoff_date}
            )
            
            rows_affected = result.rowcount
            db.commit()
            
            logger.info(f"Cleaned up {rows_affected} old tasks")
            
            return {
                "status": "success",
                "message": f"Cleaned up {rows_affected} old tasks",
                "cleaned_count": rows_affected
            }
        finally:
            db.close()
    except Exception as e:
        logger.exception(f"Error cleaning up tasks: {e}")
        return {
            "status": "error",
            "message": f"Error cleaning up tasks: {str(e)}",
            "cleaned_count": 0
        }

@shared_task(name="app.workers.task_worker.notify_task_deadlines")
def notify_task_deadlines(hours_remaining: int = 24) -> Dict[str, Any]:
    """
    Celery task to notify players of upcoming task deadlines.
    This should be run on a schedule, e.g. once per day.
    
    Args:
        hours_remaining: Notify for tasks with this many hours remaining
        
    Returns:
        Dict with results of notifications
    """
    logger.info(f"Checking tasks with deadlines in the next {hours_remaining} hours")
    
    try:
        db = SessionLocal()
        try:
            from sqlalchemy import text
            from datetime import datetime, timedelta
            
            # Calculate time window
            start_time = datetime.utcnow()
            end_time = start_time + timedelta(hours=hours_remaining)
            
            # Find tasks with deadlines in the window
            result = db.execute(
                text("""
                SELECT t.task_id, t.title, t.deadline, c.character_id, c.character_name
                FROM tasks t
                JOIN characters c ON t.character_id = c.character_id
                WHERE t.status IN ('accepted', 'in_progress')
                AND t.deadline >= :start_time
                AND t.deadline <= :end_time
                AND t.is_active = true
                """),
                {
                    "start_time": start_time,
                    "end_time": end_time
                }
            )
            
            tasks_to_notify = result.fetchall()
            notification_count = len(tasks_to_notify)
            
            # In a real implementation, you would send notifications here
            # For each task in tasks_to_notify, you'd queue a notification
            # to the appropriate player/character
            
            logger.info(f"Found {notification_count} tasks approaching deadline")
            
            return {
                "status": "success",
                "message": f"Notified {notification_count} tasks approaching deadline",
                "notification_count": notification_count,
                "notified_tasks": [str(task[0]) for task in tasks_to_notify]
            }
        finally:
            db.close()
    except Exception as e:
        logger.exception(f"Error notifying task deadlines: {e}")
        return {
            "status": "error",
            "message": f"Error notifying task deadlines: {str(e)}",
            "notification_count": 0
        }

@shared_task(name="tasks.create_trader_assistance_task")
def create_trader_assistance_task(trader_id: str, area_id: str, world_id: str, issue_type: str) -> Dict[str, Any]:
    """
    Create a task for a trader who needs assistance in an area.
    
    Args:
        trader_id: The ID of the trader
        area_id: The ID of the area
        world_id: The ID of the world
        issue_type: Type of issue the trader is facing (e.g., 'bandit_attack', 'broken_cart')
        
    Returns:
        Dict with task creation result
    """
    logger.info(f"Creating assistance task for trader {trader_id} in area {area_id}")
    
    try:
        db = SessionLocal()
        try:
            # Get trader and area information
            from app.models.trader import TraderModel
            from app.models.area import AreaModel
            
            trader = db.query(TraderModel).filter(TraderModel.trader_id == trader_id).first()
            logging.info(f"Trader: {trader.npc_name if trader else None}")
            area = db.query(AreaModel).filter(AreaModel.area_id == area_id).first()
            
            if not trader or not area:
                logger.error(f"Trader {trader_id} or area {area_id} not found")
                return {"status": "error", "message": "Trader or area not found"}
            
            trader_name = trader.npc_name if trader.npc_name else f"Trader {trader_id}"
            area_name = area.area_name if hasattr(area, 'area_name') else "unknown area"
            area_danger_level = area.danger_level if hasattr(area, 'danger_level') else 0
            controlling_faction = area.controlling_faction if hasattr(area, 'controlling_faction') else None

            # Generate task details based on issue type
            issue_descriptions = {
                "bandit_attack": f"Trader {trader_name} is being attacked by bandits in {area_name}. Help fight them off so the trader can continue their journey.",
                "broken_cart": f"Trader {trader_name}'s cart has broken down in {area_name}. They need materials and assistance to repair it.",
                "sick_animals": f"The animals pulling Trader {trader_name}'s cart have fallen ill in {area_name}. They need medicine and care.",
                "lost_cargo": f"Trader {trader_name} lost some valuable cargo in {area_name}. Help them recover it before someone else finds it.",
                "food_shortage": f"Trader {trader_name} has run out of food in {area_name}. They need provisions to continue their journey."
            }
            
            description = issue_descriptions.get(
                issue_type, 
                f"Trader {trader_name} needs assistance in {area_name}. Find them and help resolve their issue."
            )
            
            # Create the task using task service
            task_service = TaskService(db)
            
            # Use title that reflects the issue
            issue_titles = {
                "bandit_attack": f"Rescue trader from bandits in {area_name}",
                "broken_cart": f"Repair trader's cart in {area_name}",
                "sick_animals": f"Heal trader's animals in {area_name}",
                "lost_cargo": f"Recover lost cargo in {area_name}",
                "food_shortage": f"Provide food to stranded trader in {area_name}"
            }
            
            title = issue_titles.get(issue_type, f"Help trader in {area_name}")
            
            # Generate rewards based on issue difficulty
            difficulty_map = {
                "bandit_attack": 8,  # Highest difficulty
                "broken_cart": 5,
                "sick_animals": 6,
                "lost_cargo": 7,
                "food_shortage": 4  # Lowest difficulty
            }
            
            difficulty = difficulty_map.get(issue_type, 5)
            
            # Scale rewards based on difficulty
            gold_reward = 20 + (difficulty * 10)
            xp_reward = 30 + (difficulty * 15)
            reputation_reward = 1 + (difficulty // 2)
            
            # Add guard bonus for escort quests
            if issue_type == "bandit_attack" and hasattr(trader, 'hired_guards'):
                gold_reward += trader.hired_guards * 15
            
            # Create the task using a direct database approach to avoid asyncio issues
            from app.models.tasks import Tasks, TaskTypes
            import uuid
            import json
            from datetime import datetime
            
            # Get the task type ID for trader assistance
            task_type = db.query(TaskTypes).filter(TaskTypes.code == "trader_assistance").first()
            if not task_type:
                logger.error(f"Task type 'trader_assistance' not found")
                return {"status": "error", "message": "Task type not found"}
            
            # Create task ID
            task_id = str(uuid.uuid4())
            
            # Set up rewards
            rewards = {
                "gold": gold_reward,
                "reputation": reputation_reward,
                "xp": xp_reward
            }
            
            # Create task data
            task_data = {
                "task_type_display": "Trader Assistance",
                "issue_type": issue_type
            }
            
            # Create the task record directly
            new_task = Tasks(
                task_id=task_id,
                title=title,
                description=description,
                task_type_id=task_type.task_type_id,
                world_id=world_id,
                location_id=area_id,
                target_id=trader_id,
                difficulty=difficulty,
                duration_minutes=30,  # Default 30 minutes
                requirements={},
                rewards=rewards,
                task_data=task_data,
                repeatable=False,
                status='available',
                is_active=True,
                created_at=datetime.utcnow()
            )
            
            # Add and commit
            db.add(new_task)
            db.commit()
            
            result = {
                "status": "success",
                "message": "Task created successfully",
                "task_id": task_id
            }
            
            log_level = logging.ERROR if result.get("status") != "success" else logging.INFO
            logger.log(log_level, f"Task creation result: {result}")
            
            if result.get("status") == "success" and result.get("task_id"):
                # Update trader to be blocked by this task
                trader.can_move = False
                logging.info(f"Blocking trader {trader_id} from moving until task {result.get('task_id')} is completed")
                db.refresh(trader)
                trader.active_task_id = result.get("task_id")
                db.commit()
                
                trader = db.query(TraderModel).filter(TraderModel.trader_id == trader_id).first()
                logging.info(f"Trader: {trader.npc_name if trader else None}")
                logging.info(f"Trader: {trader.active_task_id if trader else None}")
                logger.info(f"Trader {trader_id} is now waiting for task {result.get('task_id')} completion")
            
            return result
        finally:
            db.close()
    except Exception as e:
        logger.exception(f"Error creating trader assistance task: {e}")
        return {"status": "error", "message": str(e)}