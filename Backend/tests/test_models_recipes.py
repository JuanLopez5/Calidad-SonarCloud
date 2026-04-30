"""Tests para el modelo recipes.py - Cobertura completa"""
import pytest
from unittest.mock import Mock, patch


class TestCreateRecipe:
    """Tests para create_recipe"""
    
    @patch('src.models.recipes.recipes_collection')
    def test_create_recipe_success(self, mock_collection):
        from src.models.recipes import create_recipe
        mock_result = Mock()
        mock_result.inserted_id = "123456"
        mock_collection.insert_one.return_value = mock_result
        result = create_recipe("Pasta", "Delicious pasta", "USER@example.com")
        assert result == "123456"
    
    @patch('src.models.recipes.recipes_collection')
    def test_create_recipe_with_expiration(self, mock_collection):
        from src.models.recipes import create_recipe
        mock_result = Mock()
        mock_result.inserted_id = "789"
        mock_collection.insert_one.return_value = mock_result
        result = create_recipe("Salad", "Fresh salad", "user@example.com", "2024-12-31")
        assert result == "789"
    
    @patch('src.models.recipes.recipes_collection')
    def test_create_recipe_without_expiration(self, mock_collection):
        from src.models.recipes import create_recipe
        mock_result = Mock()
        mock_result.inserted_id = "noexp"
        mock_collection.insert_one.return_value = mock_result
        result = create_recipe("Soup", "Hot soup", "chef@example.com", None)
        assert result == "noexp"
    
    @patch('src.models.recipes.recipes_collection', None)
    def test_create_recipe_no_db(self):
        from src.models.recipes import create_recipe
        result = create_recipe("Test", "Description", "user@example.com")
        assert isinstance(result, dict)
        assert "error" in result


class TestListRecipes:
    """Tests para list_recipes"""
    
    @patch('src.models.recipes.recipes_collection')
    def test_list_recipes_success(self, mock_collection):
        from src.models.recipes import list_recipes
        mock_collection.find.return_value = [
            {"title": "Pasta", "description": "Delicious"},
            {"title": "Pizza", "description": "Tasty"}
        ]
        recipes = list_recipes()
        assert len(recipes) == 2
    
    @patch('src.models.recipes.recipes_collection', None)
    def test_list_recipes_no_db(self):
        from src.models.recipes import list_recipes
        recipes = list_recipes()
        assert recipes == []
    
    @patch('src.models.recipes.recipes_collection')
    def test_list_recipes_empty(self, mock_collection):
        from src.models.recipes import list_recipes
        mock_collection.find.return_value = []
        recipes = list_recipes()
        assert recipes == []
