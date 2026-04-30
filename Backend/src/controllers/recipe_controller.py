import os
import time
import threading
import requests
from flask import current_app

# Global cache and lock (thread-safe)
_recipe_cache = {}
_recipe_cache_lock = threading.Lock()


def _get_cached_or_fetch(cache_key, url, params):
    """
    Helper function to fetch data with TTL-based caching.
    Eliminates code duplication between get_recipes_by_ingredients and get_recipe_information.
    Returns: payload on success, or (error_dict, status_code) tuple on error
    """
    cache_ttl = int(current_app.config.get('RECIPE_CACHE_TTL', 60 * 60 * 24))
    now = int(time.time())
    
    # Check cache
    with _recipe_cache_lock:
        entry = _recipe_cache.get(cache_key)
        if entry and now - entry['ts'] < cache_ttl:
            return entry['value']
    
    # Fetch from API
    try:
        response = requests.get(url, params=params, timeout=10)
    except Exception as e:
        return {"error": f"Request failed: {e}"}, 502
    
    # Handle response
    if response.status_code == 200:
        payload = response.json()
        with _recipe_cache_lock:
            _recipe_cache[cache_key] = {'ts': now, 'value': payload}
        return payload
    else:
        return {"error": "Failed to fetch data"}, response.status_code


def get_recipes_by_ingredients(ingredients, number=5):
    """Fetch recipes by ingredients from Spoonacular API with caching."""
    if not ingredients:
        return {"error": "No ingredients provided"}, 400

    cache_key = f"findByIngredients:{','.join(sorted([str(i).lower() for i in ingredients]))}"
    
    api_key = current_app.config["SPOONACULAR_API_KEY"]
    url = f"{current_app.config['SPOONACULAR_URL_BASE']}/recipes/findByIngredients"
    
    # Validate and normalize number parameter
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

    return _get_cached_or_fetch(cache_key, url, params)


def get_recipe_information(recipe_id, include_nutrition=True):
    """Fetch full recipe information by id from Spoonacular API with caching."""
    if not recipe_id:
        return {"error": "No recipe id provided"}, 400

    cache_key = f"information:{recipe_id}:nutrition={bool(include_nutrition)}"
    
    api_key = current_app.config["SPOONACULAR_API_KEY"]
    base = current_app.config.get('SPOONACULAR_URL_BASE')
    url = f"{base}/recipes/{recipe_id}/information"
    
    params = {
        "includeNutrition": 'true' if include_nutrition else 'false',
        "apiKey": api_key
    }

    return _get_cached_or_fetch(cache_key, url, params)