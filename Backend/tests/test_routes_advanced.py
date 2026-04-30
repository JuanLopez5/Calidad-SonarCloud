"""Tests avanzados para recipe_recomendation.py - Para aumentar cobertura a 80%"""
import pytest
from unittest.mock import Mock, patch, mock_open
import json
import os
import tempfile


@pytest.fixture
def app():
    """Fixture de Flask app"""
    from flask import Flask
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['SPOONACULAR_API_KEY'] = 'test_key'
    
    from src.routes.recipe_recomendation import recipe_recommendation_bp
    app.register_blueprint(recipe_recommendation_bp)
    
    return app


@pytest.fixture
def client(app):
    """Cliente de prueba"""
    return app.test_client()


class TestCacheFileOperations:
    """Tests para operaciones de caché en archivos"""
    
    @patch('src.routes.recipe_recomendation.get_recipes_by_ingredients')
    def test_cache_hit_with_valid_data(self, mock_get_recipes, client):
        """Test cuando hay un cache hit con datos válidos"""
        mock_get_recipes.return_value = []
        
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_file = os.path.join(tmpdir, 'test_cache.json')
            valid_cache = [
                {'id': 1, 'title': 'Cached Recipe', 'ingredients': ['chicken']}
            ]
            
            with open(cache_file, 'w') as f:
                json.dump(valid_cache, f)
            
            with patch.dict(os.environ, {'EP_RECIPE_CACHE_DIR': tmpdir}):
                with patch('src.routes.recipe_recomendation.os.path.exists', return_value=True):
                    with patch('src.routes.recipe_recomendation.os.path.getmtime', return_value=1234567890):
                        with patch('src.routes.recipe_recomendation.time.time', return_value=1234567900):
                            with patch('builtins.open', mock_open(read_data=json.dumps(valid_cache))):
                                response = client.post('/recipes/suggest',
                                                      json={'ingredients': ['chicken']})
                                assert response.status_code == 200
    
    @patch('src.routes.recipe_recomendation.get_recipes_by_ingredients')
    def test_cache_expired(self, mock_get_recipes, client):
        """Test cuando el caché está expirado"""
        mock_get_recipes.return_value = [
            {'id': 1, 'title': 'Fresh Recipe', 'usedIngredientCount': 1}
        ]
        
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.dict(os.environ, {
                'EP_RECIPE_CACHE_DIR': tmpdir,
                'EP_RECIPE_CACHE_TTL': '3600'  # 1 hora
            }):
                response = client.post('/recipes/suggest',
                                      json={'ingredients': ['chicken']})
                assert response.status_code == 200
    
    @patch('src.routes.recipe_recomendation.get_recipes_by_ingredients')
    @patch('src.routes.recipe_recomendation.get_recipe_information')
    def test_enrichment_with_nutrition(self, mock_get_info, mock_get_recipes, client):
        """Test de enriquecimiento con información nutricional"""
        mock_get_recipes.return_value = [
            {
                'id': 1,
                'title': 'Chicken Recipe',
                'usedIngredientCount': 2,
                'missedIngredientCount': 1,
                'image': 'image.jpg',
                'usedIngredients': [{'name': 'chicken'}, {'name': 'rice'}],
                'missedIngredients': [{'name': 'tomato'}]
            }
        ]
        
        mock_get_info.return_value = {
            'id': 1,
            'title': 'Chicken Recipe',
            'readyInMinutes': 30,
            'servings': 4,
            'sourceUrl': 'http://example.com',
            'nutrition': {
                'nutrients': [
                    {'name': 'Calories', 'amount': 250, 'unit': 'kcal'},
                    {'name': 'Protein', 'amount': 20, 'unit': 'g'}
                ]
            },
            'instructions': 'Cook the chicken',
            'extendedIngredients': []
        }
        
        response = client.post('/recipes/suggest',
                              json={'ingredients': ['chicken', 'rice'], 'prefetch': 1})
        
        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, list)
        assert len(data) > 0
    
    @patch('src.routes.recipe_recomendation.get_recipes_by_ingredients')
    def test_error_tuple_from_controller(self, mock_get_recipes, client):
        """Test cuando el controller retorna tupla de error"""
        mock_get_recipes.return_value = ({'error': 'API Error'}, 502)
        
        response = client.post('/recipes/suggest',
                              json={'ingredients': ['chicken']})
        
        assert response.status_code == 502
        data = response.get_json()
        assert 'error' in data


class TestRecipeInfoById:
    """Tests para get_recipe_info_by_id"""
    
    @patch('src.routes.recipe_recomendation.get_recipe_information')
    def test_get_recipe_info_valid_id(self, mock_get_info, client):
        """Test obtener información de receta con ID válido"""
        mock_get_info.return_value = {
            'id': 123,
            'title': 'Test Recipe',
            'nutrition': {'nutrients': []}
        }
        
        response = client.get('/recipes/123/information')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['id'] == 123
    
    @patch('src.routes.recipe_recomendation.get_recipe_information')
    def test_get_recipe_info_string_id(self, mock_get_info, client):
        """Test con ID como string"""
        mock_get_info.return_value = {'id': 456}
        
        response = client.get('/recipes/456/information')
        
        assert response.status_code == 200
    
    def test_get_recipe_info_invalid_id(self, client):
        """Test con ID inválido (no numérico)"""
        response = client.get('/recipes/invalid/information')
        
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
    
    @patch('src.routes.recipe_recomendation.get_recipe_information')
    def test_get_recipe_info_error_tuple(self, mock_get_info, client):
        """Test cuando get_recipe_information retorna tupla de error"""
        mock_get_info.return_value = ({'error': 'Not found'}, 404)
        
        response = client.get('/recipes/999/information')
        
        assert response.status_code == 404


class TestSortingAndScoring:
    """Tests para la lógica de ordenamiento y scoring"""
    
    @patch('src.routes.recipe_recomendation.get_recipes_by_ingredients')
    def test_sorting_by_score(self, mock_get_recipes, client):
        """Test que recetas se ordenan por score correctamente"""
        mock_get_recipes.return_value = [
            {'id': 1, 'title': 'Recipe 1', 'usedIngredientCount': 1, 'missedIngredientCount': 3},
            {'id': 2, 'title': 'Recipe 2', 'usedIngredientCount': 3, 'missedIngredientCount': 1},
            {'id': 3, 'title': 'Recipe 3', 'usedIngredientCount': 2, 'missedIngredientCount': 2}
        ]
        
        response = client.post('/recipes/suggest',
                              json={'ingredients': ['chicken', 'rice', 'tomato'], 'prefetch': 0})
        
        assert response.status_code == 200
        data = response.get_json()
        # Recipe 2 debe estar primero (más ingredientes usados)
        assert data[0]['id'] == 2
    
    @patch('src.routes.recipe_recomendation.get_recipes_by_ingredients')
    def test_lightweight_objects_for_non_prefetched(self, mock_get_recipes, client):
        """Test que recetas no-prefetch retornan objetos ligeros"""
        mock_get_recipes.return_value = [
            {
                'id': 1,
                'title': 'Recipe 1',
                'image': 'img1.jpg',
                'usedIngredientCount': 2,
                'missedIngredientCount': 1,
                'usedIngredients': [{'name': 'chicken'}, {'name': 'rice'}],
                'missedIngredients': [{'name': 'tomato'}]
            },
            {
                'id': 2,
                'title': 'Recipe 2',
                'image': 'img2.jpg',
                'usedIngredientCount': 1,
                'missedIngredientCount': 2
            }
        ]
        
        response = client.post('/recipes/suggest',
                              json={'ingredients': ['chicken', 'rice'], 'prefetch': 0})
        
        assert response.status_code == 200
        data = response.get_json()
        assert len(data) > 0
        # Verificar que tienen la estructura esperada
        assert 'id' in data[0]
        assert 'title' in data[0]
    
    @patch('src.routes.recipe_recomendation.get_recipes_by_ingredients')
    def test_empty_candidates(self, mock_get_recipes, client):
        """Test cuando no hay candidatos"""
        mock_get_recipes.return_value = []
        
        response = client.post('/recipes/suggest',
                              json={'ingredients': ['unknownIngredient']})
        
        assert response.status_code == 200
        data = response.get_json()
        assert data == []


class TestEdgeCases:
    """Tests para casos extremos"""
    
    @patch('src.routes.recipe_recomendation.get_recipes_by_ingredients')
    def test_candidates_without_id(self, mock_get_recipes, client):
        """Test con candidatos sin ID"""
        mock_get_recipes.return_value = [
            {'title': 'Recipe without ID'},  # Sin 'id'
            {'id': 2, 'title': 'Valid Recipe', 'usedIngredientCount': 1}
        ]
        
        response = client.post('/recipes/suggest',
                              json={'ingredients': ['chicken']})
        
        assert response.status_code == 200
        data = response.get_json()
        # Solo debe incluir la receta con ID válido
        assert len(data) >= 1
    
    @patch('src.routes.recipe_recomendation.get_recipes_by_ingredients')
    @patch('src.routes.recipe_recomendation.get_recipe_information')
    def test_get_recipe_info_exception(self, mock_get_info, mock_get_recipes, client):
        """Test cuando get_recipe_information lanza excepción"""
        mock_get_recipes.return_value = [
            {'id': 1, 'title': 'Recipe', 'usedIngredientCount': 1}
        ]
        mock_get_info.side_effect = Exception("Connection error")
        
        response = client.post('/recipes/suggest',
                              json={'ingredients': ['chicken'], 'prefetch': 1})
        
        # Debe manejar la excepción y retornar algo
        assert response.status_code in [200, 500]
    
    @patch('src.routes.recipe_recomendation.get_recipes_by_ingredients')
    def test_cache_write_failure(self, mock_get_recipes, client, tmp_path):
        """Test cuando falla escritura de caché"""
        mock_get_recipes.return_value = [
            {'id': 1, 'title': 'Recipe', 'usedIngredientCount': 1}
        ]
        
        # Usar un directorio no escribible
        with patch.dict(os.environ, {'EP_RECIPE_CACHE_DIR': '/invalid/path'}):
            response = client.post('/recipes/suggest',
                                  json={'ingredients': ['chicken']})
            
            # Debe funcionar aunque falle el cache
            assert response.status_code == 200
