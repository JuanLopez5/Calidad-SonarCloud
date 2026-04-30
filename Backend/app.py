"""
ExpiryPalNext Backend - Main Application Entry Point
"""
import sys
from flask_wtf.csrf import CSRFProtect
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

BASE_SRC = os.path.join(BASE_DIR, 'src')
if BASE_SRC not in sys.path:
    sys.path.append(BASE_SRC)

from flask import Flask, jsonify, request, redirect, send_from_directory
from flask_cors import CORS
try:
    from flasgger import Swagger
except Exception:
    Swagger = None

# Load .env early and auto-disable Firebase when key is missing/malformed
from dotenv import load_dotenv
load_dotenv()
import os
# If EP_DISABLE_FIREBASE is not explicitly set, auto-disable when FIREBASE_PRIVATE_KEY
# is absent or doesn't contain the usual BEGIN marker to avoid startup failures.
if os.environ.get('EP_DISABLE_FIREBASE', '') not in ('1', 'true', 'True'):
    fb_key = os.environ.get('FIREBASE_PRIVATE_KEY', '')
    if not fb_key or 'BEGIN PRIVATE KEY' not in fb_key:
        os.environ['EP_DISABLE_FIREBASE'] = '1'
        print('Auto-set EP_DISABLE_FIREBASE=1 because FIREBASE_PRIVATE_KEY is missing or malformed')

# Firebase & auth middleware
from src.config_pkg.firebase import init_firebase
from src.middleware.auth import require_auth, optional_auth
from src.routes.recipe_recomendation import recipe_recommendation_bp

# DB and models
import db
from src.models.users import create_user, list_users, authenticate_user
from src.models.recipes import create_recipe, list_recipes
from src.models.items import create_item, list_items

# Environment variables already loaded above

# Initialize Flask app
app = Flask(__name__)
csrf = CSRFProtect()
csrf.init_app(app)

# NOTE: Swagger will be initialized after route registration so that all
# endpoints (including blueprints) are picked up by the automatic spec.

# Load application configuration from environment (SPOONACULAR keys, etc.)
try:
    from src.app_config import Config
    app.config.from_object(Config)
except Exception:
    # fall back to environment variables if import fails
    app.config['SPOONACULAR_API_KEY'] = os.environ.get('SPOONACULAR_API_KEY')
    app.config['SPOONACULAR_URL_BASE'] = os.environ.get('SPOONACULAR_URL_BASE', 'https://api.spoonacular.com')

# Configure CORS — allow the dev frontend origins for all endpoints (including /recipes)
CORS(app, resources={
    r"/*": {
        "origins": ["http://localhost:5173", "http://localhost:3000"],
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})

# Register recipe recommendation blueprint (provides /recipes/suggest)
app.register_blueprint(recipe_recommendation_bp)

# Initialize Flasgger (Swagger UI) when available. Expose docs at /docs
# Initialize here (after blueprints/routes are registered) so /docs works
# whether the app is started via `python app.py` or `flask run`.
if Swagger is not None:
    swagger_template = {
        "info": {
            "title": "ExpiryPalNext API",
            "description": "ExpiryPalNext backend API documentation",
            "version": "1.0.0"
        }
    }
    swagger_config = {
        "headers": [],
        "specs": [
            {
                "endpoint": 'apispec_1',
                "route": '/apispec_1.json',
                "rule_filter": lambda rule: True,
                "model_filter": lambda tag: True,
            }
        ],
        "static_url_path": "/flasgger_static",
        "swagger_ui": True,
        "specs_route": "/docs"
    }
    Swagger(app, config=swagger_config, template=swagger_template)

# Initialize Firebase Admin SDK 
try:
    init_firebase()
except Exception as e:
    print("Warning: init_firebase() falló:", e)

# ---------- Health / Basic endpoints ----------
@app.route('/')
def health_check():
    """Health check
    ---
    tags:
        - Health
    responses:
        200:
            description: Health status
            content:
                application/json:
                    schema:
                        type: object
                        properties:
                            status:
                                type: string
                            service:
                                type: string
                            version:
                                type: string
    """
    return jsonify({
        'status': 'ok',
        'service': 'ExpiryPalNext Backend',
        'version': '1.0.0'
    })

@app.route('/api/public')
def public_endpoint():
    return jsonify({
        'message': 'This is a public endpoint',
        'accessible': 'Everyone can access this'
    })


# Minimal OpenAPI JSON (fallback) so the static Swagger UI can load a spec at /openapi.json
@app.route('/openapi.json')
def openapi_spec():
    spec = {
        "openapi": "3.0.0",
        "info": {"title": "ExpiryPalNext API", "version": "1.0.0"},
        "paths": {
            "/": {
                "get": {
                    "tags": ["Health"],
                    "summary": "Health check",
                    "responses": {
                        "200": {
                            "description": "Health status",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "status": {"type": "string"},
                                            "service": {"type": "string"},
                                            "version": {"type": "string"}
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    return jsonify(spec)


# Serve a tiny static docs UI that uses Swagger UI CDN and fetches /openapi.json
@app.route('/docs/')
def serve_docs_index():
    try:
        return send_from_directory(os.path.join(BASE_DIR, 'docs'), 'index.html')
    except Exception:
        return jsonify({'error': 'Docs not available'}), 404

# ---------- Auth endpoints (require_auth / optional_auth) ----------
@app.route('/api/protected')
@require_auth
def protected_endpoint(current_user):
    return jsonify({
        'message': 'This is a protected endpoint',
        'user': {
            'uid': current_user.get('uid'),
            'email': current_user.get('email'),
            'name': current_user.get('name'),
            'email_verified': current_user.get('email_verified')
        },
        'timestamp': current_user.get('auth_time')
    })

@app.route('/api/optional')
@optional_auth
def optional_endpoint(current_user=None):
    if current_user:
        return jsonify({
            'message': f'Hello {current_user.get("email")}',
            'authenticated': True
        })
    return jsonify({
        'message': 'Hello guest',
        'authenticated': False
    })

@app.route('/api/user/profile')
@require_auth
def user_profile(current_user):
    return jsonify({
        'profile': {
            'uid': current_user.get('uid'),
            'email': current_user.get('email'),
            'name': current_user.get('name'),
            'picture': current_user.get('picture'),
            'email_verified': current_user.get('email_verified'),
            'provider': current_user.get('firebase', {}).get('sign_in_provider')
        }
    })

@app.route("/test-db")
def test_db():
    try:
        test_collection = db.mongo_db["test"]
        test_doc = {"name": "Primer documento", "ok": True}
        test_collection.insert_one(test_doc)
        docs = list(test_collection.find({}, {"_id": 0}))
        return jsonify(docs)
    except Exception as e:
        return jsonify({"error": "DB test failed", "detail": str(e)}), 500

@app.route("/users", methods=["POST"])
def add_user():
    data = request.get_json() or {}
    if not all(k in data for k in ("name", "email", "password_hash")):
        return jsonify({"error": "Missing name, email or password_hash"}), 400

    try:
        # create_user returns a result dict (message or error)
        result = create_user(data["name"], data["email"], data["password_hash"])
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": "Could not create user", "detail": str(e)}), 500

@app.route("/users", methods=["GET"])
def get_users():
    try:
        return jsonify(list_users())
    except Exception as e:
        return jsonify({"error": "Could not list users", "detail": str(e)}), 500

@app.route("/recipes", methods=["POST"])
def add_recipe():
    data = request.get_json() or {}
    if not all(k in data for k in ("title", "description", "user_email")):
        return jsonify({"error": "Missing title, description or user_email"}), 400

    try:
        recipe_id = create_recipe(
            data["title"], data["description"], data["user_email"], data.get("expiration_date")
        )
        return jsonify({"recipe_id": recipe_id, "message": "Receta agregada correctamente"})
    except Exception as e:
        return jsonify({"error": "Could not create recipe", "detail": str(e)}), 500

@app.route("/recipes", methods=["GET"])
def get_recipes():
    try:
        return jsonify(list_recipes())
    except Exception as e:
        return jsonify({"error": "Could not list recipes", "detail": str(e)}), 500

# ---------- Error handlers ----------
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404


@app.route('/docs')
def docs_redirect():
    return redirect('/docs/')

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

# ---------- Main ----------
if __name__ == '__main__':
    # Initialize Flasgger (Swagger UI) when available. Expose docs at /docs
    if Swagger is not None:
        swagger_template = {
            "info": {
                "title": "ExpiryPalNext API",
                "description": "ExpiryPalNext backend API documentation",
                "version": "1.0.0"
            }
        }
        swagger_config = {
            "headers": [],
            "specs": [
                {
                    "endpoint": 'apispec_1',
                    "route": '/apispec_1.json',
                    "rule_filter": lambda rule: True,
                    "model_filter": lambda tag: True,
                }
            ],
            "static_url_path": "/flasgger_static",
            "swagger_ui": True,
            "specs_route": "/docs"
        }
        Swagger(app, config=swagger_config, template=swagger_template)

    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_ENV', 'development') == 'development'
    app.run(debug=debug, host='0.0.0.0', port=port)
