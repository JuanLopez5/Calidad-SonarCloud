"""Tests para el modelo items.py - Cobertura completa"""
import pytest
from unittest.mock import Mock, patch
from datetime import datetime


class TestCreateItem:
    """Tests para create_item"""
    
    @patch('src.models.items.items_collection')
    def test_create_item_success(self, mock_collection):
        from src.models.items import create_item
        mock_collection.insert_one.return_value = Mock()
        result = create_item("USER@example.com", "Milk", "dairy", "2024-12-31")
        assert "message" in result
        assert "exitosamente" in result["message"]
        call_args = mock_collection.insert_one.call_args[0][0]
        assert call_args["user_email"] == "user@example.com"
        assert call_args["name"] == "Milk"
    
    @patch('src.models.items.items_collection', None)
    def test_create_item_no_db(self):
        from src.models.items import create_item
        result = create_item("user@example.com", "Milk", "dairy", "2024-12-31")
        assert "error" in result
        assert "DB no disponible" in result["error"]


class TestListItems:
    """Tests para list_items"""
    
    @patch('src.models.items.items_collection')
    def test_list_items_by_user(self, mock_collection):
        from src.models.items import list_items
        mock_collection.find.return_value = [
            {"name": "Milk", "category": "dairy"},
            {"name": "Eggs", "category": "protein"}
        ]
        items = list_items("USER@example.com")
        assert len(items) == 2
    
    @patch('src.models.items.items_collection')
    def test_list_items_all(self, mock_collection):
        from src.models.items import list_items
        mock_collection.find.return_value = [{"name": "Milk"}, {"name": "Eggs"}, {"name": "Bread"}]
        items = list_items(None)
        assert len(items) == 3
    
    @patch('src.models.items.items_collection', None)
    def test_list_items_no_db(self):
        from src.models.items import list_items
        items = list_items("user@example.com")
        assert items == []


class TestUpdateItemStatus:
    """Tests para update_item_status"""
    
    @patch('src.models.items.items_collection')
    def test_update_item_status_success(self, mock_collection):
        from src.models.items import update_item_status
        mock_result = Mock()
        mock_result.modified_count = 1
        mock_collection.update_one.return_value = mock_result
        result = update_item_status("Milk", "consumed")
        assert "message" in result
    
    @patch('src.models.items.items_collection')
    def test_update_item_status_not_found(self, mock_collection):
        from src.models.items import update_item_status
        mock_result = Mock()
        mock_result.modified_count = 0
        mock_collection.update_one.return_value = mock_result
        result = update_item_status("NonExistent", "consumed")
        assert "error" in result
    
    @patch('src.models.items.items_collection', None)
    def test_update_item_status_no_db(self):
        from src.models.items import update_item_status
        result = update_item_status("Milk", "consumed")
        assert "error" in result
    
    @patch('src.models.items.items_collection')
    def test_update_item_status_db_error(self, mock_collection):
        from src.models.items import update_item_status
        mock_collection.update_one.side_effect = Exception("Connection error")
        result = update_item_status("Milk", "consumed")
        assert "error" in result
