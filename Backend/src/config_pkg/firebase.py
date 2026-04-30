"""
Firebase Admin Configuration (moved to config_pkg)
Initialize Firebase Admin SDK for token verification
"""
import os
import firebase_admin
from firebase_admin import credentials, auth
from dotenv import load_dotenv

load_dotenv()


def init_firebase():
    """
    Initialize Firebase Admin SDK
    If EP_DISABLE_FIREBASE is set in the environment, skip initialization.
    """
    # Allow opting out in development when the service account PEM is not available
    if os.environ.get('EP_DISABLE_FIREBASE', '') in ('1', 'true', 'True'):
        print('EP_DISABLE_FIREBASE is set — skipping Firebase Admin initialization')
        return
    """
    Initialize Firebase Admin SDK
    """
    try:
        # Check if already initialized
        firebase_admin.get_app()
        print("Firebase Admin SDK already initialized")
    except ValueError:
        # Create credentials from environment variables
        firebase_config = {
            "type": "service_account",
            "project_id": os.getenv('FIREBASE_PROJECT_ID'),
            "private_key_id": os.getenv('FIREBASE_PRIVATE_KEY_ID'),
            "private_key": os.getenv('FIREBASE_PRIVATE_KEY', '').replace('\\n', '\n'),
            "client_email": os.getenv('FIREBASE_CLIENT_EMAIL'),
            "client_id": os.getenv('FIREBASE_CLIENT_ID'),
            "auth_uri": os.getenv('FIREBASE_AUTH_URI', 'https://accounts.google.com/o/oauth2/auth'),
            "token_uri": os.getenv('FIREBASE_TOKEN_URI', 'https://oauth2.googleapis.com/token'),
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_x509_cert_url": f"https://www.googleapis.com/robot/v1/metadata/x509/{os.getenv('FIREBASE_CLIENT_EMAIL')}"
        }
        
        # Initialize Firebase Admin
        try:
            cred = credentials.Certificate(firebase_config)
            firebase_admin.initialize_app(cred)
            print("Firebase Admin SDK initialized successfully")
        except Exception as e:
            # Re-raise so caller may log/handle; include helpful hint about PEM formatting
            raise Exception(str(e) + ' — Ensure FIREBASE_PRIVATE_KEY is correctly formatted (no surrounding quotes, use \\n for newlines)')

def verify_token(id_token):
    try:
        decoded_token = auth.verify_id_token(id_token)
        return decoded_token
    except Exception as e:
        raise Exception(f"Invalid token: {str(e)}")

def get_user_by_uid(uid):
    try:
        user = auth.get_user(uid)
        return user
    except Exception as e:
        raise Exception(f"User not found: {str(e)}")
