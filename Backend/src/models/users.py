from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from db import mongo_db

# Colección principal (safe lookup: mongo_db may be None while DB is disabled)
try:
    users_collection = mongo_db["users"]
except Exception:
    users_collection = None

# Register, validate & hash
def register_user(name, email, password):
    """Registra un nuevo usuario validando duplicados."""
    if users_collection is None:
        return {"error": "DB no disponible: registro deshabilitado en entorno de desarrollo."}

    if users_collection.find_one({"email": email.lower()}):
        return {"error": "El correo ya está registrado."}

    hashed_password = generate_password_hash(password)
    user = {
        "name": name,
        "email": email.lower(),
        "password_hash": hashed_password,
        "created_at": datetime.utcnow()
    }
    users_collection.insert_one(user)
    return {"message": "Usuario registrado correctamente."}


# Authentication
def authenticate_user(email, password):
    """Valida credenciales de inicio de sesión."""
    if users_collection is None:
        return {"error": "DB no disponible: autenticación deshabilitada en entorno de desarrollo."}

    user = users_collection.find_one({"email": email.lower()})
    if not user:
        return {"error": "Usuario no encontrado."}
    if not check_password_hash(user["password_hash"], password):
        return {"error": "Contraseña incorrecta."}

    return {
        "message": "Autenticación exitosa.",
        "email": user["email"],
        "name": user["name"]
    }


# administration o seeds
def create_user(name, email, password_hash):
    """Crea un usuario directamente sin validar duplicados ni hashear (por ejemplo, import masivo)."""
    if users_collection is None:
        return {"error": "DB no disponible: creación de usuario deshabilitada en entorno de desarrollo."}

    user = {
        "name": name,
        "email": email.lower(),
        "password_hash": password_hash,
        "created_at": datetime.utcnow()
    }
    users_collection.insert_one(user)
    return {"message": f"Usuario {name} creado correctamente."}


# List users
def list_users():
    """Devuelve una lista de usuarios sin incluir hash de contraseña."""
    if users_collection is None:
        return []
    users = list(users_collection.find({}, {"_id": 0, "password_hash": 0}))
    return users
