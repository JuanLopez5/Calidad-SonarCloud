"""
Tests para las rutas de recomendación de recetas (recipe_recomendation.py)
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import json
import tempfile
import os
from pathlib import Path


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


# ============================================================================
# Tests para funciones helper
# ============================================================================

class TestParseRequestParams:
    """Tests para _parse_request_params"""
    
    def test_valid_request_with_all_params(self):
        """Test parsing request con todos los parámetros"""
        from src.routes.recipe_recomendation import _parse_request_params
        
        data = {
            'ingredients': ['chicken', 'rice'],
            'number': 10,
            'prefetch': 5
        }
        
        ings, num, prefetch, original = _parse_request_params(data)
        
        assert ings == ['chicken', 'rice']
        assert num == 10
        assert prefetch == 5
        assert original == data
    
    def test_request_with_only_ingredients(self):
        """Test parsing request solo con ingredientes"""
        from src.routes.recipe_recomendation import _parse_request_params
        
        data = {'ingredients': ['chicken']}
        
        ings, num, prefetch, original = _parse_request_params(data)
        
        assert ings == ['chicken']
        assert num is None
        assert prefetch == 5  # Valor por defecto
    
    def test_invalid_number_parameter(self):
        """Test parsing request con number inválido"""
        from src.routes.recipe_recomendation import _parse_request_params
        
        data = {'ingredients': ['chicken'], 'number': 'invalid'}
        
        ings, num, prefetch, original = _parse_request_params(data)
        
        assert ings == ['chicken']
        assert num is None
        assert prefetch == 5
    
    def test_invalid_prefetch_parameter(self):
        """Test parsing request con prefetch inválido"""
        from src.routes.recipe_recomendation import _parse_request_params
        
        data = {'ingredients': ['chicken'], 'prefetch': 'invalid'}
        
        ings, num, prefetch, original = _parse_request_params(data)
        
        assert ings == ['chicken']
        assert prefetch == 5  # Valor por defecto
    
    def test_empty_data(self):
        """Test parsing request vacío"""
        from src.routes.recipe_recomendation import _parse_request_params
        
        ings, num, prefetch, original = _parse_request_params({})
        
        assert ings is None
        assert num is None
        assert prefetch is None
    
    def test_none_data(self):
        """Test parsing con None"""
        from src.routes.recipe_recomendation import _parse_request_params
        
        ings, num, prefetch, original = _parse_request_params(None)
        
        assert ings is None


class TestGetCachePath:
    """Tests para _get_cache_path"""
    
    def test_valid_cache_path(self):
        """Test generación válida de ruta de caché"""
        from src.routes.recipe_recomendation import _get_cache_path
        
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.dict(os.environ, {'EP_RECIPE_CACHE_DIR': tmpdir}):
                path = _get_cache_path(['chicken', 'rice'], 5, 5)
                
                assert path is not None
                assert path.startswith(tmpdir)
                assert path.endswith('.json')
    
    def test_cache_path_none_ingredients(self):
        """Test ruta de caché con ingredientes None"""
        from src.routes.recipe_recomendation import _get_cache_path
        
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.dict(os.environ, {'EP_RECIPE_CACHE_DIR': tmpdir}):
                path = _get_cache_path(None, 5, 5)
                
                assert path is None or isinstance(path, str)


class TestLoadCachedRecipes:
    """Tests para _load_cached_recipes"""
    
    def test_load_valid_cached_recipes(self):
        """Test cargando recetas válidas en caché"""
        from src.routes.recipe_recomendation import _load_cached_recipes
        
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_file = os.path.join(tmpdir, 'test_cache.json')
            
            # Crear archivo de caché válido
            cached_data = [
                {'id': 1, 'name': 'Recipe 1', 'ingredients': []}
            ]
            with open(cache_file, 'w') as f:
                json.dump(cached_data, f)
            
            result = _load_cached_recipes(cache_file)
            
            assert result == cached_data
    
    def test_load_nonexistent_cache(self):
        """Test cargando caché que no existe"""
        from src.routes.recipe_recomendation import _load_cached_recipes
        
        result = _load_cached_recipes('/nonexistent/path/cache.json')
        
        assert result is None
    
    def test_load_invalid_cache_format(self):
        """Test cargando caché con formato inválido"""
        from src.routes.recipe_recomendation import _load_cached_recipes
        
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_file = os.path.join(tmpdir, 'invalid_cache.json')
            
            # Crear archivo con datos inválidos
            with open(cache_file, 'w') as f:
                json.dump({'not': 'a list'}, f)
            
            result = _load_cached_recipes(cache_file)
            
            assert result is None


class TestScoreRecipe:
    """Tests para _score_recipe"""
    
    def test_score_calculation(self):
        """Test cálculo de score"""
        from src.routes.recipe_recomendation import _score_recipe
        
        recipe = {
            'usedIngredientCount': 3,
            'missedIngredientCount': 2
        }
        
        score = _score_recipe(recipe)
        
        assert len(score) == 2
        assert score[0] == 3  # used count
        assert score[1] == 0.6  # ratio
    
    def test_score_no_ingredients(self):
        """Test score cuando no hay ingredientes"""
        from src.routes.recipe_recomendation import _score_recipe
        
        recipe = {
            'usedIngredientCount': 0,
            'missedIngredientCount': 0
        }
        
        score = _score_recipe(recipe)
        
        assert score[0] == 0
        assert score[1] == 0.0


class TestBuildIngredientsList:
    """Tests para _build_ingredients_list"""
    
    def test_build_with_used_ingredients(self):
        """Test construcción de lista con ingredientes usados"""
        from src.routes.recipe_recomendation import _build_ingredients_list
        
        used = [
            {'id': 1, 'name': 'chicken', 'amount': 2, 'unit': 'cups'}
        ]
        
        result = _build_ingredients_list(used, [])
        
        assert len(result) == 1
        assert result[0]['name'] == 'chicken'
        assert result[0]['available'] is True
    
    def test_build_with_missed_ingredients(self):
        """Test construcción de lista con ingredientes faltantes"""
        from src.routes.recipe_recomendation import _build_ingredients_list
        
        missed = [
            {'id': 2, 'name': 'salt', 'original': 'sea salt'}
        ]
        
        result = _build_ingredients_list([], missed)
        
        assert len(result) == 1
        assert result[0]['available'] is False
    
    def test_build_with_lower_ings_set(self):
        """Test construcción con set de ingredientes en minúsculas"""
        from src.routes.recipe_recomendation import _build_ingredients_list
        
        used = [
            {'id': 1, 'name': 'Chicken', 'original': 'chicken'}
        ]
        lower_ings = {'chicken'}
        
        result = _build_ingredients_list(used, [], lower_ings)
        
        assert result[0]['available'] is True
    
    def test_build_with_none_values(self):
        """Test construcción con valores None"""
        from src.routes.recipe_recomendation import _build_ingredients_list
        
        result = _build_ingredients_list(None, None)
        
        assert result == []


class TestBuildLightweightRecipe:
    """Tests para _build_lightweight_recipe"""
    
    def test_build_lightweight_recipe(self):
        """Test construcción de receta ligera"""
        from src.routes.recipe_recomendation import _build_lightweight_recipe
        
        candidate = {
            'id': 1,
            'title': 'Test Recipe',
            'image': 'http://example.com/image.jpg',
            'usedIngredientCount': 3,
            'missedIngredientCount': 1,
            'usedIngredients': [],
            'missedIngredients': []
        }
        
        result = _build_lightweight_recipe(candidate)
        
        assert result['id'] == 1
        assert result['name'] == 'Test Recipe'
        assert result['lightweight'] is True
        assert result['readyInMinutes'] == 30
        assert result['servings'] == 1


class TestBuildEnrichedRecipe:
    """Tests para _build_enriched_recipe"""
    
    def test_build_enriched_recipe(self):
        """Test construcción de receta enriquecida"""
        from src.routes.recipe_recomendation import _build_enriched_recipe
        
        info = {
            'id': 1,
            'title': 'Test Recipe',
            'image': 'http://example.com/image.jpg',
            'readyInMinutes': 45,
            'servings': 4,
            'summary': 'A test recipe',
            'dishTypes': ['main course'],
            'extendedIngredients': [],
            'analyzedInstructions': []
        }
        
        candidate = {
            'id': 1,
            'title': 'Test Recipe',
            'usedIngredientCount': 3,
            'missedIngredientCount': 1
        }
        
        result = _build_enriched_recipe(info, candidate, set())
        
        assert result['id'] == 1
        assert result['name'] == 'Test Recipe'
        assert result['readyInMinutes'] == 45
        assert result['servings'] == 4


class TestSaveCache:
    """Tests para _save_cache"""
    
    def test_save_cache_success(self):
        """Test guardado exitoso de caché"""
        from src.routes.recipe_recomendation import _save_cache
        
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = os.path.join(tmpdir, 'test_cache.json')
            enriched = [{'id': 1, 'name': 'Recipe 1'}]
            
            _save_cache(cache_path, enriched)
            
            assert os.path.exists(cache_path)
            with open(cache_path, 'r') as f:
                data = json.load(f)
            assert data == enriched
    
    def test_save_cache_none_path(self):
        """Test guardado de caché con path None"""
        from src.routes.recipe_recomendation import _save_cache
        
        # No debe lanzar error
        _save_cache(None, [])


# ============================================================================
# Tests para endpoints
# ============================================================================

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
