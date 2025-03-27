# app/routers/task.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID

from database.connection import get_db
from app.game_state.services.task_service import TaskService
from app.schemas.tasks import (
    TaskCreate, 
    TaskResponse, 
    TaskListResponse, 
    TaskUpdate,
    TaskCompleteRequest,
    TaskAcceptRequest,
    TaskCompleteResponse
)

router = APIRouter(prefix="/tasks", tags=["tasks"])

@router.get("/", response_model=TaskListResponse)
async def get_tasks(
    world_id: UUID,
    location_id: Optional[str] = None,
    character_id: Optional[UUID] = None,
    db: Session = Depends(get_db)
):
    """
    Get available tasks in a world, optionally filtered by location or character.
    """
    task_service = TaskService(db)
    tasks = await task_service.get_available_tasks(
        world_id=str(world_id),
        location_id=location_id,
        character_id=str(character_id) if character_id else None
    )
    
    return {"tasks": tasks, "count": len(tasks)}

@router.get("/character/{character_id}", response_model=TaskListResponse)
async def get_character_tasks(
    character_id: UUID,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get tasks assigned to a specific character.
    """
    task_service = TaskService(db)
    tasks = await task_service.get_character_tasks(
        character_id=str(character_id),
        status=status
    )
    
    return {"tasks": tasks, "count": len(tasks)}

@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(task_id: UUID, db: Session = Depends(get_db)):
    """
    Get details of a specific task.
    """
    task_service = TaskService(db)
    task = await task_service.get_task(str(task_id))
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return task

@router.post("/{task_id}/accept", status_code=status.HTTP_200_OK)
async def accept_task(
    task_id: UUID,
    request: TaskAcceptRequest,
    db: Session = Depends(get_db)
):
    """
    Accept a task for a character.
    """
    task_service = TaskService(db)
    result = await task_service.accept_task(
        task_id=str(task_id),
        character_id=str(request.character_id)
    )
    
    if result["status"] == "error":
        raise HTTPException(status_code=400, detail=result["message"])
    
    return result

@router.post("/{task_id}/complete", response_model=TaskCompleteResponse)
async def complete_task(
    task_id: UUID,
    request: TaskCompleteRequest,
    db: Session = Depends(get_db)
):
    """
    Complete a task and receive rewards.
    """
    task_service = TaskService(db)
    result = await task_service.complete_task(
        task_id=str(task_id),
        character_id=str(request.character_id)
    )
    
    if result["status"] == "error":
        raise HTTPException(status_code=400, detail=result["message"])
    
    return result

@router.get("/trader/{trader_id}", response_model=TaskListResponse)
async def get_trader_tasks(trader_id: UUID, db: Session = Depends(get_db)):
    """
    Get tasks related to a specific trader.
    """
    task_service = TaskService(db)
    tasks = await task_service.get_trader_tasks(str(trader_id))
    
    return {"tasks": tasks, "count": len(tasks)}

@router.get("/location/{location_id}", response_model=TaskListResponse)
async def get_location_tasks(
    location_id: str,
    world_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Get tasks available at a specific location.
    """
    task_service = TaskService(db)
    tasks = await task_service.get_available_tasks(
        world_id=str(world_id),
        location_id=location_id
    )
    
    return {"tasks": tasks, "count": len(tasks)}

@router.post("/create_test_task", status_code=status.HTTP_201_CREATED)
async def create_test_task(
    world_id: UUID,
    title: str = "Help a Trader in Trouble",
    description: str = "A trader has encountered bandits on the road and needs your help!",
    location_id: Optional[str] = None,
    target_id: Optional[str] = None,
    task_type: str = "trader_assistance",
    db: Session = Depends(get_db)
):
    """
    Create a test task for development purposes.
    """
    task_service = TaskService(db)
    result = await task_service.create_task(
        task_type=task_type,
        title=title,
        description=description,
        world_id=str(world_id),
        location_id=location_id,
        target_id=target_id,
        requirements={},
        rewards={
            "gold": 50,
            "reputation": 2,
            "xp": 100
        }
    )
    
    if result["status"] != "success":
        raise HTTPException(status_code=400, detail=result["message"])
        
    return result