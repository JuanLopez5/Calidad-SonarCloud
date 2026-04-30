"""Tests para el modelo users.py - Cobertura completa"""
import pytest
from unittest.mock import Mock, patch
from werkzeug.security import generate_password_hash


class TestRegisterUser:
    """Tests para register_user"""
    
    @patch('src.models.users.users_collection')
    def test_register_user_success(self, mock_collection):
        from src.models.users import register_user
        mock_collection.find_one.return_value = None
        mock_collection.insert_one.return_value = Mock()
        result = register_user("John", "JOHN@example.com", "password123")
        assert "message" in result
        assert "registrado correctamente" in result["message"]
    
    @patch('src.models.users.users_collection')
    def test_register_user_duplicate(self, mock_collection):
        from src.models.users import register_user
        mock_collection.find_one.return_value = {"email": "john@example.com"}
        result = register_user("John", "john@example.com", "password123")
        assert "error" in result
    
    @patch('src.models.users.users_collection', None)
    def test_register_user_no_db(self):
        from src.models.users import register_user
        result = register_user("John", "john@example.com", "password123")
        assert "error" in result


class TestAuthenticateUser:
    """Tests para authenticate_user"""
    
    @patch('src.models.users.users_collection')
    def test_authenticate_user_success(self, mock_collection):
        from src.models.users import authenticate_user
        mock_collection.find_one.return_value = {
            "email": "john@example.com",
            "name": "John",
            "password_hash": generate_password_hash("password123")
        }
        result = authenticate_user("john@example.com", "password123")
        assert "message" in result
    
    @patch('src.models.users.users_collection')
    def test_authenticate_user_not_found(self, mock_collection):
        from src.models.users import authenticate_user
        mock_collection.find_one.return_value = None
        result = authenticate_user("nonexistent@example.com", "password123")
        assert "error" in result
    
    @patch('src.models.users.users_collection')
    def test_authenticate_user_wrong_password(self, mock_collection):
        from src.models.users import authenticate_user
        mock_collection.find_one.return_value = {
            "email": "john@example.com",
            "name": "John",
            "password_hash": generate_password_hash("correct_password")
        }
        result = authenticate_user("john@example.com", "wrong_password")
        assert "error" in result
    
    @patch('src.models.users.users_collection', None)
    def test_authenticate_user_no_db(self):
        from src.models.users import authenticate_user
        result = authenticate_user("john@example.com", "password123")
        assert "error" in result


class TestCreateUser:
    """Tests para create_user"""
    
    @patch('src.models.users.users_collection')
    def test_create_user_success(self, mock_collection):
        from src.models.users import create_user
        mock_collection.insert_one.return_value = Mock()
        result = create_user("Admin", "admin@example.com", "hash123")
        assert "message" in result
    
    @patch('src.models.users.users_collection', None)
    def test_create_user_no_db(self):
        from src.models.users import create_user
        result = create_user("Admin", "admin@example.com", "hash")
        assert "error" in result


class TestListUsers:
    """Tests para list_users"""
    
    @patch('src.models.users.users_collection')
    def test_list_users_success(self, mock_collection):
        from src.models.users import list_users
        mock_collection.find.return_value = [
            {"name": "User 1", "email": "user1@example.com"},
            {"name": "User 2", "email": "user2@example.com"}
        ]
        users = list_users()
        assert len(users) == 2
    
    @patch('src.models.users.users_collection', None)
    def test_list_users_no_db(self):
        from src.models.users import list_users
        users = list_users()
        assert users == []
