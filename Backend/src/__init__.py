# Backend package
from flask import Flask, jsonify
from flask_cors import CORS
from .routes.recipe_recomendation import recipe_recommendation_bp
from flask_wtf.csrf import CSRFProtect

# Optional Firebase init and auth decorators
# Use a dynamic loader to avoid static analysis/missing-import diagnostics in
# editors that don't include Backend/src on their analysis path. At runtime
# this will try a few plausible module names and fall back to no-op
# placeholders if the modules aren't available.
import importlib


def _load_optional_auth_and_firebase():
    init_firebase_fn = lambda: None
    require_auth_fn = lambda f: f
    optional_auth_fn = lambda f: f

    # Try a few likely module names (package vs src layout)
    firebase_candidates = [
    "Backend.src.config_pkg.firebase",
    "src.config_pkg.firebase",
    "config_pkg.firebase",
    ".config_pkg.firebase",
    ]
    for mod_name in firebase_candidates:
        try:
            mod = importlib.import_module(mod_name)
            init_firebase_fn = getattr(mod, 'init_firebase', init_firebase_fn)
            break
        except Exception:
            continue

    auth_candidates = [
        "Backend.src.middleware.auth",
        "src.middleware.auth",
        "middleware.auth",
        ".middleware.auth",
    ]
    for mod_name in auth_candidates:
        try:
            mod = importlib.import_module(mod_name)
            require_auth_fn = getattr(mod, 'require_auth', require_auth_fn)
            optional_auth_fn = getattr(mod, 'optional_auth', optional_auth_fn)
            break
        except Exception:
            continue

    return init_firebase_fn, require_auth_fn, optional_auth_fn


init_firebase, require_auth, optional_auth = _load_optional_auth_and_firebase()

def create_app():
    app = Flask(__name__)
    csrf = CSRFProtect()
    csrf.init_app(app)
    
    # Load configuration
    # Import Config directly so static analysis can resolve it
    from .config import Config
    app.config.from_object(Config)

    # Configure CORS to allow Authorization header from dev servers
    CORS(app, resources={r"/*": {"origins": ["http://localhost:5173","http://localhost:3000"], "allow_headers": ["Content-Type","Authorization"]}})

    # Initialize Firebase Admin SDK (best-effort; non-fatal)
    try:
        init_firebase()
    except Exception as e:
        # If firebase is not configured in this environment, log and continue
        print("Warning: init_firebase() failed:", e)

    # Register blueprints
    app.register_blueprint(recipe_recommendation_bp)

    # Minimal protected endpoints so frontend can test auth flows
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

    return app