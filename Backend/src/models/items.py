from datetime import datetime
from db import mongo_db

# Safe collection lookup (DB may be disabled during development)
try:
    items_collection = mongo_db["items"]
except Exception:
    items_collection = None

def create_item(user_email, name, category, expiration_date):
    item = {
        "user_email": user_email.lower(),
        "name": name,
        "category": category,
        "expiration_date": expiration_date,
        "created_at": datetime.utcnow(),
        "status": "active"
    }
    if items_collection is None:
        return {"error": "DB no disponible: no se puede crear item en entorno de desarrollo."}

    items_collection.insert_one(item)
    return {"message": "Item agregado exitosamente."}

def list_items(user_email=None):
    query = {"user_email": user_email.lower()} if user_email else {}
    if items_collection is None:
        return []
    items = list(items_collection.find(query, {"_id": 0}))
    return items

def update_item_status(item_name, new_status):
    if items_collection is None:
        return {"error": "DB no disponible: no se puede actualizar item en entorno de desarrollo."}
    try:
        result = items_collection.update_one({"name": item_name}, {"$set": {"status": new_status}})
    except Exception as e:
        return {"error": "DB error during update", "detail": str(e)}

    # Defensive handling: drivers/placeholder may return different shapes.
    modified = None
    try:
        modified = getattr(result, 'modified_count')
    except Exception:
        try:
            modified = result.get('modified_count') if isinstance(result, dict) else None
        except Exception:
            modified = None

    if not modified:
        return {"error": "Item no encontrado."}
    return {"message": "Estado del item actualizado correctamente."}
