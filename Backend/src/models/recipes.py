from datetime import datetime
from db import mongo_db  

# Safe collection lookup (DB may be disabled during development)
try:
    recipes_collection = mongo_db["recipes"]
except Exception:
    recipes_collection = None

def create_recipe(title, description, user_email, expiration_date=None):
    recipe = {
        "title": title,
        "description": description,
        "user_email": user_email.lower(),
        "created_at": datetime.utcnow(),
        "expiration_date": expiration_date
    }
    if recipes_collection is None:
        return {"error": "DB no disponible: no se puede crear receta en entorno de desarrollo."}

    result = recipes_collection.insert_one(recipe)
    return str(result.inserted_id)

def list_recipes():
    if recipes_collection is None:
        return []
    return list(recipes_collection.find({}, {"_id": 0}))
