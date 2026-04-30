import os
import time
import threading
import requests
from flask import current_app

def get_recipes_by_ingredients(ingredients, number=5):

    if not ingredients:
        return {"error": "No ingredients provided"}, 400

    # Simple in-memory TTL cache to avoid repeated identical requests to Spoonacular
    cache_ttl = int(current_app.config.get('RECIPE_CACHE_TTL', 60 * 60 * 24))  # default 24h
    cache_key = f"findByIngredients:{','.join(sorted([str(i).lower() for i in ingredients]))}"

    # ensure globals exist on module
    global _recipe_cache, _recipe_cache_lock
    if '_recipe_cache' not in globals():
        _recipe_cache = {}
        _recipe_cache_lock = threading.Lock()

    now = int(time.time())
    with _recipe_cache_lock:
        entry = _recipe_cache.get(cache_key)
        if entry and now - entry['ts'] < cache_ttl:
            return entry['value']

    api_key = current_app.config["SPOONACULAR_API_KEY"]
    url = f"{current_app.config['SPOONACULAR_URL_BASE']}/recipes/findByIngredients"
    # enforce sensible bounds for number to avoid accidental large queries
    try:
        n = int(number)
    except Exception:
        n = 5
    n = max(1, min(n, int(current_app.config.get('SPOONACULAR_MAX_RESULTS', 50))))

    params = {
        "ingredients": ",".join(ingredients),
        "number": n,
        "apiKey": api_key
    }

    try:
        response = requests.get(url, params=params, timeout=10)
    except Exception as e:
        return {"error": f"Request failed: {e}"}, 502

    if response.status_code == 200:
        payload = response.json()
        with _recipe_cache_lock:
            _recipe_cache[cache_key] = {'ts': now, 'value': payload}
        return payload
    else:
        return {"error": "Failed to fetch recipes"}, response.status_code


def get_recipe_information(recipe_id, include_nutrition=True):
    """
    Fetch full recipe information by id from Spoonacular.
    Returns JSON on success or tuple (dict, status_code) on error.
    """
    if not recipe_id:
        return {"error": "No recipe id provided"}, 400

    # In-memory TTL cache for recipe information
    cache_ttl = int(current_app.config.get('RECIPE_CACHE_TTL', 60 * 60 * 24))  # default 24h
    cache_key = f"information:{recipe_id}:nutrition={bool(include_nutrition)}"

    global _recipe_cache, _recipe_cache_lock
    if '_recipe_cache' not in globals():
        _recipe_cache = {}
        _recipe_cache_lock = threading.Lock()

    now = int(time.time())
    with _recipe_cache_lock:
        entry = _recipe_cache.get(cache_key)
        if entry and now - entry['ts'] < cache_ttl:
            return entry['value']

    api_key = current_app.config["SPOONACULAR_API_KEY"]
    base = current_app.config.get('SPOONACULAR_URL_BASE')
    url = f"{base}/recipes/{recipe_id}/information"
    params = {
        "includeNutrition": 'true' if include_nutrition else 'false',
        "apiKey": api_key
    }

    try:
        response = requests.get(url, params=params, timeout=10)
    except Exception as e:
        return {"error": f"Request failed: {e}"}, 502

    if response.status_code == 200:
        payload = response.json()
        with _recipe_cache_lock:
            _recipe_cache[cache_key] = {'ts': now, 'value': payload}
        return payload
    else:
        # propagate status
        return {"error": "Failed to fetch recipe information", "status": response.status_code}, response.status_code