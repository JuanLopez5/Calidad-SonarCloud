"""
Tests para el controlador de recetas (recipe_controller.py)
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import time


@pytest.fixture
def mock_app():
    """Mock de Flask app con configuración"""
    app = Mock()
    app.config = {
        'RECIPE_CACHE_TTL': 3600,
        'SPOONACULAR_API_KEY': 'test_api_key',
        'SPOONACULAR_URL_BASE': 'https://api.spoonacular.com',
        'SPOONACULAR_MAX_RESULTS': 50
    }
    return app


@pytest.fixture
def mock_current_app(mock_app):
    """Mock del current_app de Flask"""
    with patch('src.controllers.recipe_controller.current_app', mock_app):
        yield mock_app


class TestGetRecipesByIngredients:
    """Tests para get_recipes_by_ingredients"""
    
    def test_no_ingredients_provided(self, mock_current_app):
        """Test cuando no se proporcionan ingredientes"""
        from src.controllers.recipe_controller import get_recipes_by_ingredients
        
        result, status = get_recipes_by_ingredients([])
        assert status == 400
        assert 'error' in result
    
    def test_none_ingredients(self, mock_current_app):
        """Test cuando se pasa None como ingredientes"""
        from src.controllers.recipe_controller import get_recipes_by_ingredients
        
        result, status = get_recipes_by_ingredients(None)
        assert status == 400
    
    @patch('src.controllers.recipe_controller.requests.get')
    def test_successful_api_call(self, mock_get, mock_current_app):
        """Test de llamada exitosa a la API"""
        from src.controllers.recipe_controller import get_recipes_by_ingredients
        
        # Mock de respuesta exitosa
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {'id': 1, 'title': 'Recipe 1'},
            {'id': 2, 'title': 'Recipe 2'}
        ]
        mock_get.return_value = mock_response
        
        result = get_recipes_by_ingredients(['chicken', 'rice'], number=5)
        
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]['id'] == 1
    
    @patch('src.controllers.recipe_controller.requests.get')
    def test_api_request_failure(self, mock_get, mock_current_app):
        """Test cuando la petición a la API falla"""
        from src.controllers.recipe_controller import get_recipes_by_ingredients
        
        # Simular excepción en requests
        mock_get.side_effect = Exception("Connection error")
        
        result, status = get_recipes_by_ingredients(['chicken'])
        
        assert status == 502
        assert 'error' in result
        assert 'Request failed' in result['error']
    
    @patch('src.controllers.recipe_controller.requests.get')
    def test_api_non_200_response(self, mock_get, mock_current_app):
        """Test cuando la API devuelve un código diferente a 200"""
        from src.controllers.recipe_controller import get_recipes_by_ingredients
        
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.text = "Not found"
        mock_get.return_value = mock_response
        
        result, status = get_recipes_by_ingredients(['chicken'])
        
        assert status == 404
        assert 'error' in result
    
    @patch('src.controllers.recipe_controller.requests.get')
    def test_number_parameter_validation(self, mock_get, mock_current_app):
        """Test validación del parámetro number"""
        from src.controllers.recipe_controller import get_recipes_by_ingredients
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_get.return_value = mock_response
        
        # Test con número string
        get_recipes_by_ingredients(['chicken'], number='abc')
        
        # Verificar que se llamó con el número por defecto
        call_args = mock_get.call_args
        assert call_args[1]['params']['number'] == 5
    
    @patch('src.controllers.recipe_controller.requests.get')
    def test_number_parameter_bounds(self, mock_get, mock_current_app):
        """Test límites del parámetro number"""
        from src.controllers.recipe_controller import get_recipes_by_ingredients
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_get.return_value = mock_response
        
        # Test con número muy grande
        get_recipes_by_ingredients(['chicken'], number=1000)
        
        # Debe limitarse a SPOONACULAR_MAX_RESULTS (50)
        call_args = mock_get.call_args
        assert call_args[1]['params']['number'] <= 50
        
        # Test con número negativo
        get_recipes_by_ingredients(['chicken'], number=-5)
        
        # Debe ser al menos 1
        call_args = mock_get.call_args
        assert call_args[1]['params']['number'] >= 1
    
    @patch('src.controllers.recipe_controller.requests.get')
    def test_cache_functionality(self, mock_get, mock_current_app):
        """Test del sistema de caché"""
        from src.controllers.recipe_controller import get_recipes_by_ingredients
        import src.controllers.recipe_controller as rc
        
        # Limpiar caché si existe
        if hasattr(rc, '_recipe_cache'):
            rc._recipe_cache.clear()
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{'id': 1, 'title': 'Cached Recipe'}]
        mock_get.return_value = mock_response
        
        # Primera llamada - debe llamar a la API
        result1 = get_recipes_by_ingredients(['chicken', 'rice'], number=5)
        assert mock_get.call_count == 1
        
        # Segunda llamada con los mismos ingredientes - debe usar caché
        result2 = get_recipes_by_ingredients(['chicken', 'rice'], number=5)
        assert mock_get.call_count == 1  # No debe llamar a la API de nuevo
        
        assert result1 == result2


class TestGetRecipeInformation:
    """Tests para get_recipe_information"""
    
    @patch('src.controllers.recipe_controller.requests.get')
    def test_get_recipe_info_success(self, mock_get, mock_current_app):
        """Test de obtención exitosa de información de receta"""
        from src.controllers.recipe_controller import get_recipe_information
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'id': 123,
            'title': 'Test Recipe',
            'nutrition': {'nutrients': []}
        }
        mock_get.return_value = mock_response
        
        result = get_recipe_information(123, include_nutrition=True)
        
        assert result['id'] == 123
        assert 'nutrition' in result
    
    @patch('src.controllers.recipe_controller.requests.get')
    def test_get_recipe_info_failure(self, mock_get, mock_current_app):
        """Test cuando falla la obtención de información"""
        from src.controllers.recipe_controller import get_recipe_information
        
        mock_get.side_effect = Exception("API Error")
        
        result, status = get_recipe_information(123)
        
        assert status == 502
        assert 'error' in result
    
    @patch('src.controllers.recipe_controller.requests.get')
    def test_get_recipe_info_without_nutrition(self, mock_get, mock_current_app):
        """Test sin incluir información nutricional"""
        from src.controllers.recipe_controller import get_recipe_information
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'id': 123, 'title': 'Test Recipe'}
        mock_get.return_value = mock_response
        
        result = get_recipe_information(123, include_nutrition=False)
        
        # Verificar que el parámetro includeNutrition sea false
        call_args = mock_get.call_args
        assert call_args[1]['params']['includeNutrition'] == 'false'
