"""
Tests para el middleware de autenticación (auth.py)
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from flask import Flask, jsonify


@pytest.fixture
def app():
    """Fixture de Flask app"""
    app = Flask(__name__)
    app.config['TESTING'] = True
    return app


@pytest.fixture
def mock_verify_token():
    """Mock de la función verify_token"""
    with patch('src.middleware.auth._verify_token') as mock:
        yield mock


class TestRequireAuth:
    """Tests para el decorador require_auth"""
    
    def test_missing_authorization_header(self, app, mock_verify_token):
        """Test cuando falta el header de autorización"""
        from src.middleware.auth import require_auth
        
        @app.route('/protected')
        @require_auth
        def protected_route():
            return jsonify({'message': 'Success'})
        
        with app.test_client() as client:
            response = client.get('/protected')
            
            assert response.status_code == 401
            data = response.get_json()
            assert 'error' in data
            assert 'Missing authorization header' in data['error']
    
    def test_invalid_authorization_format(self, app, mock_verify_token):
        """Test con formato de autorización inválido"""
        from src.middleware.auth import require_auth
        
        @app.route('/protected')
        @require_auth
        def protected_route():
            return jsonify({'message': 'Success'})
        
        with app.test_client() as client:
            response = client.get('/protected',
                                 headers={'Authorization': 'InvalidFormat'})
            
            assert response.status_code == 401
            data = response.get_json()
            assert 'error' in data
    
    def test_missing_bearer_prefix(self, app, mock_verify_token):
        """Test cuando falta el prefijo Bearer"""
        from src.middleware.auth import require_auth
        
        @app.route('/protected')
        @require_auth
        def protected_route():
            return jsonify({'message': 'Success'})
        
        with app.test_client() as client:
            response = client.get('/protected',
                                 headers={'Authorization': 'token123'})
            
            assert response.status_code == 401
    
    def test_valid_token(self, app, mock_verify_token):
        """Test con token válido"""
        from src.middleware.auth import require_auth
        
        # Mock de usuario verificado
        mock_verify_token.return_value = {
            'uid': 'user123',
            'email': 'test@example.com'
        }
        
        @app.route('/protected')
        @require_auth
        def protected_route():
            return jsonify({'message': 'Success'})
        
        with app.test_client() as client:
            response = client.get('/protected',
                                 headers={'Authorization': 'Bearer valid_token'})
            
            assert response.status_code == 200
            data = response.get_json()
            assert data['message'] == 'Success'
    
    def test_expired_token(self, app, mock_verify_token):
        """Test con token expirado"""
        from src.middleware.auth import require_auth
        
        # Simular token expirado
        mock_verify_token.side_effect = Exception('Token expired')
        
        @app.route('/protected')
        @require_auth
        def protected_route():
            return jsonify({'message': 'Success'})
        
        with app.test_client() as client:
            response = client.get('/protected',
                                 headers={'Authorization': 'Bearer expired_token'})
            
            assert response.status_code == 401
            data = response.get_json()
            assert 'error' in data
    
    def test_invalid_token(self, app, mock_verify_token):
        """Test con token inválido"""
        from src.middleware.auth import require_auth
        
        mock_verify_token.side_effect = Exception('Invalid token')
        
        @app.route('/protected')
        @require_auth
        def protected_route():
            return jsonify({'message': 'Success'})
        
        with app.test_client() as client:
            response = client.get('/protected',
                                 headers={'Authorization': 'Bearer invalid_token'})
            
            assert response.status_code == 401
    
    def test_function_wrapping(self, app, mock_verify_token):
        """Test que el decorador mantiene el nombre de la función"""
        from src.middleware.auth import require_auth
        
        @require_auth
        def test_function():
            """Test docstring"""
            pass
        
        # Verificar que se mantiene el nombre y docstring
        assert test_function.__name__ == 'test_function'
        assert test_function.__doc__ == 'Test docstring'
    
    def test_request_context_variables(self, app, mock_verify_token):
        """Test que el user_id se agrega al contexto de request"""
        from src.middleware.auth import require_auth
        from flask import g
        
        mock_verify_token.return_value = {'uid': 'user123'}
        
        @app.route('/protected')
        @require_auth
        def protected_route():
            # El decorador debe agregar user_id a g
            return jsonify({'user_id': getattr(g, 'user_id', None)})
        
        with app.test_client() as client:
            response = client.get('/protected',
                                 headers={'Authorization': 'Bearer valid_token'})
            
            assert response.status_code == 200


class TestVerifyToken:
    """Tests para la función _verify_token"""
    
    @patch('src.middleware.auth.importlib.import_module')
    def test_verify_token_module_not_found(self, mock_import):
        """Test cuando no se encuentra el módulo"""
        from src.middleware.auth import _verify_token
        
        mock_import.side_effect = ModuleNotFoundError('Module not found')
        
        with pytest.raises(Exception):
            _verify_token('test_token')
    
    @patch('src.middleware.auth.importlib.import_module')
    def test_verify_token_success(self, mock_import):
        """Test de verificación exitosa de token"""
        from src.middleware.auth import _verify_token
        
        # Mock del módulo firebase
        mock_module = Mock()
        mock_module.verify_token.return_value = {'uid': 'user123'}
        mock_import.return_value = mock_module
        
        result = _verify_token('valid_token')
        
        assert result['uid'] == 'user123'
    
    @patch('src.middleware.auth.importlib.import_module')
    def test_verify_token_tries_multiple_paths(self, mock_import):
        """Test que intenta múltiples rutas de módulo"""
        from src.middleware.auth import _verify_token
        
        # Primeros intentos fallan, el último funciona
        mock_module = Mock()
        mock_module.verify_token.return_value = {'uid': 'user123'}
        
        def side_effect(name):
            if 'config_pkg.firebase' in name:
                return mock_module
            raise ModuleNotFoundError()
        
        mock_import.side_effect = side_effect
        
        result = _verify_token('valid_token')
        
        assert result['uid'] == 'user123'
        # Debe haber intentado múltiples módulos
        assert mock_import.call_count > 1


class TestAuthIntegration:
    """Tests de integración del middleware de autenticación"""
    
    def test_multiple_protected_routes(self, app, mock_verify_token):
        """Test con múltiples rutas protegidas"""
        from src.middleware.auth import require_auth
        
        mock_verify_token.return_value = {'uid': 'user123'}
        
        @app.route('/route1')
        @require_auth
        def route1():
            return jsonify({'route': '1'})
        
        @app.route('/route2')
        @require_auth
        def route2():
            return jsonify({'route': '2'})
        
        with app.test_client() as client:
            headers = {'Authorization': 'Bearer valid_token'}
            
            response1 = client.get('/route1', headers=headers)
            response2 = client.get('/route2', headers=headers)
            
            assert response1.status_code == 200
            assert response2.status_code == 200
    
    def test_mixed_protected_and_public_routes(self, app, mock_verify_token):
        """Test con rutas protegidas y públicas"""
        from src.middleware.auth import require_auth
        
        mock_verify_token.return_value = {'uid': 'user123'}
        
        @app.route('/public')
        def public_route():
            return jsonify({'type': 'public'})
        
        @app.route('/protected')
        @require_auth
        def protected_route():
            return jsonify({'type': 'protected'})
        
        with app.test_client() as client:
            # Ruta pública debe funcionar sin token
            response1 = client.get('/public')
            assert response1.status_code == 200
            
            # Ruta protegida requiere token
            response2 = client.get('/protected')
            assert response2.status_code == 401
            
            # Ruta protegida funciona con token
            response3 = client.get('/protected',
                                   headers={'Authorization': 'Bearer valid_token'})
            assert response3.status_code == 200
