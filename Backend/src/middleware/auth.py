"""
Authentication Middleware
Provides decorator for protecting routes with Firebase authentication
"""
from functools import wraps
from flask import request, jsonify
import importlib


def _verify_token(id_token):
    """
    Dynamic loader for verify_token to avoid static import failures in editor
    Resolves one of the likely module paths at runtime and calls its
    verify_token function. Raises the underlying exception if verification
    fails.
    """
    # Try a sequence of plausible module names (package vs. src layout)
    candidates = [
           "Backend.src.config_pkg.firebase",
           "src.config_pkg.firebase",
           "config_pkg.firebase",
           ".config_pkg.firebase",
    ]
    last_exc = None
    for mod_name in candidates:
        try:
            mod = importlib.import_module(mod_name)
            if hasattr(mod, 'verify_token'):
                return mod.verify_token(id_token)
        except Exception as e:
            last_exc = e
            continue
    # If we get here, none of the candidates worked — raise the last error
    if last_exc:
        raise last_exc
    raise Exception('verify_token implementation not found')

def require_auth(f):
    """
    Decorator to protect routes with Firebase authentication
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Get token from Authorization header
        auth_header = request.headers.get('Authorization')
        
        if not auth_header:
            return jsonify({
                'error': 'Missing authorization header',
                'message': 'Please provide an Authorization header with Bearer token'
            }), 401
        
        # Extract token from "Bearer <token>"
        try:
            token_parts = auth_header.split(' ')
            if len(token_parts) != 2 or token_parts[0] != 'Bearer':
                return jsonify({
                    'error': 'Invalid authorization header format',
                    'message': 'Format should be: Bearer <token>'
                }), 401
            
            token = token_parts[1]
        except Exception:
            return jsonify({
                'error': 'Invalid authorization header',
                'message': 'Could not parse authorization header'
            }), 401
        
        # Verify token with Firebase
        try:
            decoded_token = _verify_token(token)
            # Add decoded user info to kwargs
            kwargs['current_user'] = decoded_token
            return f(*args, **kwargs)
        except Exception as e:
            return jsonify({
                'error': 'Invalid or expired token',
                'message': str(e)
            }), 401
    
    return decorated_function

def optional_auth(f):
    """
    Decorator for routes where authentication is optional
    If token is provided and valid, current_user is passed to the route
    If no token or invalid token, current_user is None
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        
        if auth_header:
            try:
                token_parts = auth_header.split(' ')
                if len(token_parts) == 2 and token_parts[0] == 'Bearer':
                    token = token_parts[1]
                    decoded_token = _verify_token(token)
                    kwargs['current_user'] = decoded_token
            except Exception:
                # If token is invalid, just pass None
                kwargs['current_user'] = None
        else:
            kwargs['current_user'] = None
        
        return f(*args, **kwargs)
    
    return decorated_function
