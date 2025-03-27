from app.game_state.services.item_service import ItemService
from unittest.mock import MagicMock
import pytest

def test_change_item_owner_success():
    mock_manager = MagicMock()
    mock_manager.load_item.return_value = {"id": "item1"}
    mock_manager.load_owner.return_value = {"id": "owner1"}
    mock_manager.change_item_owner.return_value = {"status": "success"}
    
    service = ItemService(mock_manager)
    result = service.change_item_owner("item1", "owner1")
    
    assert result["status"] == "success"

def test_change_item_owner_item_not_found():
    mock_manager = MagicMock()
    mock_manager.load_item.return_value = None
    
    service = ItemService(mock_manager)
    result = service.change_item_owner("invalid_item", "owner1")
    
    assert result["status"] == "error"
    assert result["message"] == "Item not found"