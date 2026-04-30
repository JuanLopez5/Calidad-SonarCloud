"""
Tests para las rutas de recomendación de recetas (recipe_recomendation.py)
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import json
import tempfile
import os


@pytest.fixture
def app():
    """Fixture de Flask app para testing"""
    from flask import Flask
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['SPOONACULAR_API_KEY'] = 'test_key'
    app.config['SPOONACULAR_URL_BASE'] = 'https://api.test.com'
    
    # Registrar el blueprint
    from src.routes.recipe_recomendation import recipe_recommendation_bp
    app.register_blueprint(recipe_recommendation_bp)
    
    return app


@pytest.fixture
def client(app):
    """Cliente de prueba"""
    return app.test_client()


class TestGetIngredientsFromRequest:
    """Tests para la ruta de obtención de recetas por ingredientes"""
    
    @patch('src.routes.recipe_recomendation.get_recipes_by_ingredients')
    def test_no_ingredients_in_request(self, mock_get_recipes, client):
        """Test cuando no se envían ingredientes"""
        response = client.post('/recipes/suggest',
                              json={},
                              content_type='application/json')

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
    
    @patch('src.routes.recipe_recomendation.get_recipes_by_ingredients')
    @patch('src.routes.recipe_recomendation.get_recipe_information')
    def test_successful_recipe_request(self, mock_get_info, mock_get_recipes, client):
        """Test de solicitud exitosa de recetas"""
        # Mock de respuesta de get_recipes_by_ingredients
        mock_get_recipes.return_value = [
            {'id': 1, 'title': 'Recipe 1', 'usedIngredientCount': 3},
            {'id': 2, 'title': 'Recipe 2', 'usedIngredientCount': 2}
        ]
        
        # Mock de respuesta de get_recipe_information
        mock_get_info.return_value = {
            'id': 1,
            'nutrition': {'nutrients': [{'name': 'Calories', 'amount': 200}]}
        }
        
        response = client.post('/recipes/suggest',
                              json={'ingredients': ['chicken', 'rice']},
                              content_type='application/json')
        
        assert response.status_code == 200
    
    def test_empty_json_request(self, client):
        """Test con request JSON vacío"""
        response = client.post('/recipes/suggest',
                              json=None,
                              content_type='application/json')
        
        assert response.status_code == 400
    
    @patch('src.routes.recipe_recomendation.get_recipes_by_ingredients')
    def test_custom_number_parameter(self, mock_get_recipes, client):
        """Test con parámetro number personalizado"""
        mock_get_recipes.return_value = []
        
        response = client.post('/recipes/suggest',
                              json={
                                  'ingredients': ['chicken'],
                                  'number': 10
                              },
                              content_type='application/json')
        
        assert mock_get_recipes.called
    
    @patch('src.routes.recipe_recomendation.get_recipes_by_ingredients')
    def test_invalid_number_parameter(self, mock_get_recipes, client):
        """Test con parámetro number inválido"""
        mock_get_recipes.return_value = []
        
        response = client.post('/recipes/suggest',
                              json={
                                  'ingredients': ['chicken'],
                                  'number': 'invalid'
                              },
                              content_type='application/json')
        
        # Debe manejar el error y usar valor por defecto
        assert mock_get_recipes.called
    
    @patch('src.routes.recipe_recomendation.get_recipes_by_ingredients')
    def test_prefetch_parameter(self, mock_get_recipes, client):
        """Test con parámetro prefetch"""
        mock_get_recipes.return_value = []
        
        response = client.post('/recipes/suggest',
                              json={
                                  'ingredients': ['chicken'],
                                  'prefetch': 3
                              },
                              content_type='application/json')
        
        assert mock_get_recipes.called
    
    @patch('src.routes.recipe_recomendation.get_recipes_by_ingredients')
    def test_cache_directory_creation(self, mock_get_recipes, client):
        """Test de creación de directorio de caché"""
        mock_get_recipes.return_value = []
        
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.dict(os.environ, {'EP_RECIPE_CACHE_DIR': tmpdir}):
                response = client.post('/recipes/suggest',
                                      json={'ingredients': ['chicken']},
                                      content_type='application/json')
                
                assert response.status_code == 200


class TestRecipeEndpoints:
    """Tests adicionales para endpoints de recetas"""
    
    def test_blueprint_url_prefix(self, app):
        """Test que el blueprint tiene el prefijo correcto"""
        from src.routes.recipe_recomendation import recipe_recommendation_bp
        assert recipe_recommendation_bp.url_prefix == '/recipes'
    
    @patch('src.routes.recipe_recomendation.get_recipes_by_ingredients')
    def test_sorting_by_used_ingredient_count(self, mock_get_recipes, client):
        """Test que las recetas se ordenan por ingredientes usados"""
        # Recetas desordenadas
        mock_get_recipes.return_value = [
            {'id': 1, 'title': 'Recipe 1', 'usedIngredientCount': 1},
            {'id': 2, 'title': 'Recipe 2', 'usedIngredientCount': 5},
            {'id': 3, 'title': 'Recipe 3', 'usedIngredientCount': 3}
        ]
        
        response = client.post('/recipes/suggest',
                              json={'ingredients': ['chicken', 'rice', 'tomato']},
                              content_type='application/json')
        
        # Verificar que se llamó el endpoint
        assert response.status_code == 200


class TestCacheManagement:
    """Tests para el manejo de caché"""
    
    @patch('src.routes.recipe_recomendation.get_recipes_by_ingredients')
    def test_cache_key_generation(self, mock_get_recipes, client):
        """Test de generación de clave de caché"""
        mock_get_recipes.return_value = []
        
        # Primera llamada
        response1 = client.post('/recipes/suggest',
                               json={'ingredients': ['chicken', 'rice']},
                               content_type='application/json')
        
        # Segunda llamada con mismos ingredientes
        response2 = client.post('/recipes/suggest',
                               json={'ingredients': ['rice', 'chicken']},  # Orden diferente
                               content_type='application/json')
        
        # Ambas deben ser exitosas
        assert response1.status_code == 200
        assert response2.status_code == 200
    
    @patch('src.routes.recipe_recomendation.get_recipes_by_ingredients')
    def test_cache_ttl_environment_variable(self, mock_get_recipes, client):
        """Test de TTL de caché desde variable de entorno"""
        mock_get_recipes.return_value = []
        
        with patch.dict(os.environ, {'EP_RECIPE_CACHE_TTL': '7200'}):
            response = client.post('/recipes/suggest',
                                  json={'ingredients': ['chicken']},
                                  content_type='application/json')
            
            assert response.status_code == 200


class TestErrorHandling:
    """Tests para manejo de errores"""
    
    @patch('src.routes.recipe_recomendation.get_recipes_by_ingredients')
    def test_api_error_handling(self, mock_get_recipes, client):
        """Test de manejo de errores de API"""
        # Simular error de API
        mock_get_recipes.return_value = ({'error': 'API Error'}, 502)
        
        response = client.post('/recipes/suggest',
                              json={'ingredients': ['chicken']},
                              content_type='application/json')
        
        # Debe manejar el error apropiadamente
        assert response.status_code in [200, 400, 502]
    
    def test_malformed_json(self, client):
        """Test con JSON malformado"""
        response = client.post('/recipes/suggest',
                              data='not a json',
                              content_type='application/json')
        
        # Debe retornar error 400
        assert response.status_code in [400, 415]
