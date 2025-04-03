# app/main.py
from fastapi import FastAPI, Depends, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from database.connection import get_db
from app.routers import world, player, settlement, trader, area, animal, item, equipment, task
from app.routers import trader_router_new

from typing import Dict, List

app = FastAPI(title="RPG Game API")
active_connections: Dict[str, List[WebSocket]] = {}

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await websocket.accept()
    if "world" not in active_connections:
        active_connections["world"] = []
    active_connections["world"].append(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # can process received data here if needed
    except WebSocketDisconnect:
        active_connections["world"].remove(websocket)

# Add to your game state manager to broadcast updates
async def broadcast_world_update(world_id: str, update_data: dict):
    """Broadcast an update to all connected clients for a specific world"""
    if "world" in active_connections:
        for connection in active_connections["world"]:
            await connection.send_json({
                "world_id": world_id,
                "update_type": "world_state",
                "data": update_data
            })

# Set up CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(world.router)
app.include_router(player.router)
app.include_router(settlement.router)
app.include_router(trader.router)
app.include_router(area.router)
app.include_router(animal.router)
app.include_router(item.router)
app.include_router(equipment.router)
app.include_router(task.router)

# Include new routers using entity-manager pattern
app.include_router(trader_router_new.router)

# Mount static files directory
static_directory = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "old", "static")
app.mount("/static", StaticFiles(directory=static_directory), name="static")

@app.get("/")
async def root():
    return {"message": "Welcome to the RPG Game API"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}