from flask import Blueprint, request, jsonify
import os
import json
import hashlib
import time
from pathlib import Path

from ..controllers.recipe_controller import get_recipes_by_ingredients, get_recipe_information

recipe_recommendation_bp = Blueprint('recipe_recommendation', __name__, url_prefix='/recipes')


def _parse_request_params(data):
    """Parse and validate request parameters for recipe search."""
    if not data or 'ingredients' not in data:
        return None, None, None, None
    
    ingredients = data['ingredients']
    
    req_number = None
    try:
        req_number = int(data.get('number')) if data.get('number') is not None else None
    except Exception:
        req_number = None
    
    prefetch_n = 5
    try:
        prefetch_n = int(data.get('prefetch')) if data.get('prefetch') is not None else 5
    except Exception:
        prefetch_n = 5
    
    return ingredients, req_number, prefetch_n, data


def _get_cache_path(ingredients, req_number, prefetch_n):
    """Generate cache file path for request parameters."""
    cache_dir = os.environ.get('EP_RECIPE_CACHE_DIR') or os.path.join(os.getcwd(), 'cache')
    try:
        Path(cache_dir).mkdir(parents=True, exist_ok=True)
    except Exception:
        return None
    
    try:
        key_src = json.dumps({
            'ings': sorted([str(x).lower() for x in (ingredients or [])]),
            'number': req_number,
            'prefetch': prefetch_n
        }, separators=(',', ':'), ensure_ascii=False)
        cache_key = hashlib.sha1(key_src.encode('utf-8')).hexdigest()
        return os.path.join(cache_dir, f'recipes_{cache_key}.json')
    except Exception:
        return None


def _load_cached_recipes(cache_path):
    """Load recipes from file cache if valid."""
    if not cache_path or not os.path.exists(cache_path):
        return None
    
    cache_ttl = int(os.environ.get('EP_RECIPE_CACHE_TTL', str(60 * 60 * 24)))
    mtime = os.path.getmtime(cache_path)
    
    if (time.time() - mtime) >= cache_ttl:
        return None
    
    try:
        with open(cache_path, 'r', encoding='utf-8') as fh:
            cached = json.load(fh)
        if isinstance(cached, list) and any(isinstance(it, dict) and isinstance(it.get('ingredients'), list) for it in cached):
            return cached
    except Exception:
        pass
    
    return None


def _score_recipe(item):
    """Calculate recipe relevance score based on ingredient matches."""
    used = int(item.get('usedIngredientCount', 0))
    missed = int(item.get('missedIngredientCount', 0))
    total = used + missed if (used + missed) > 0 else 1
    return (used, used / total)


def _build_ingredients_list(used_ings, missed_ings, lower_ings=None):
    """Build normalized ingredients list from API response."""
    ingredients = []
    
    for el in (used_ings or []):
        name = el.get('name') or el.get('original') or ''
        available = (name.lower() in lower_ings) if lower_ings else True
        ingredients.append({
            'id': el.get('id'),
            'name': name,
            'original': el.get('original') if 'original' in el else None,
            'amount': el.get('amount') if 'amount' in el else None,
            'unit': el.get('unit') if 'unit' in el else None,
            'available': available
        })
    
    for el in (missed_ings or []):
        name = el.get('name') or el.get('original') or ''
        available = (name.lower() in lower_ings) if lower_ings else False
        ingredients.append({
            'id': el.get('id'),
            'name': name,
            'original': el.get('original') if 'original' in el else None,
            'amount': el.get('amount') if 'amount' in el else None,
            'unit': el.get('unit') if 'unit' in el else None,
            'available': available
        })
    
    return ingredients


def _build_lightweight_recipe(candidate):
    """Build lightweight recipe object from search result."""
    lightweight_ings = _build_ingredients_list(
        candidate.get('usedIngredients'),
        candidate.get('missedIngredients')
    )
    
    return {
        'id': candidate.get('id'),
        'name': candidate.get('title') or candidate.get('name'),
        'image': candidate.get('image'),
        'readyInMinutes': 30,
        'servings': 1,
        'summary': 'No detailed description available. This recipe was returned from a search result.',
        'dishTypes': [],
        'usedIngredientCount': candidate.get('usedIngredientCount', 0),
        'missedIngredientCount': candidate.get('missedIngredientCount', 0),
        'ingredients': lightweight_ings,
        'steps': [{'number': 1, 'step': 'Follow the source recipe steps.'}],
        'nutrition': None,
        'sourceUrl': None,
        'lightweight': True
    }


def _build_enriched_recipe(info, candidate, lower_ings):
    """Build enriched recipe object from detailed API response."""
    extended = info.get('extendedIngredients') or []
    mapped_ings = _build_ingredients_list(extended, [], lower_ings)
    
    ai = info.get('analyzedInstructions', [])
    steps_payload = []
    if isinstance(ai, list) and len(ai) > 0 and isinstance(ai[0], dict):
        steps_payload = ai[0].get('steps') or []
    if not steps_payload:
        steps_payload = [{'number': 1, 'step': 'Follow the source recipe steps.'}]
    
    return {
        'id': info.get('id') or candidate.get('id'),
        'name': info.get('title') or candidate.get('title') or candidate.get('name'),
        'image': info.get('image') or candidate.get('image'),
        'readyInMinutes': info.get('readyInMinutes') or 30,
        'servings': info.get('servings') or 1,
        'summary': info.get('summary') or 'No detailed description available.',
        'dishTypes': info.get('dishTypes') or [],
        'usedIngredientCount': candidate.get('usedIngredientCount', 0),
        'missedIngredientCount': candidate.get('missedIngredientCount', 0),
        'ingredients': mapped_ings,
        'steps': steps_payload,
        'nutrition': info.get('nutrition') or None,
        'sourceUrl': info.get('sourceUrl') or info.get('spoonacularSourceUrl')
    }


def _save_cache(cache_path, enriched):
    """Save enriched recipes to file cache."""
    if not cache_path:
        return
    
    try:
        tmp_path = cache_path + '.tmp'
        with open(tmp_path, 'w', encoding='utf-8') as fh:
            json.dump(enriched, fh, ensure_ascii=False)
        try:
            os.replace(tmp_path, cache_path)
        except Exception:
            os.rename(tmp_path, cache_path)
    except Exception:
        pass


def get_ingredients_from_request():
    """
    POST /recipes/suggest
    Fetch recipes by ingredients with smart caching and enrichment.
    Request: { ingredients: [...], number?: int, prefetch?: int }
    Response: Array of recipe objects with ingredient availability.
    """
    data = request.get_json()
    
    # Parse and validate parameters
    ingredients, req_number, prefetch_n, _ = _parse_request_params(data)
    if ingredients is None:
        return jsonify({"error": "No ingredients provided"}), 400
    
    # Check file-based cache first
    cache_path = _get_cache_path(ingredients, req_number, prefetch_n)
    cached_recipes = _load_cached_recipes(cache_path)
    if cached_recipes:
        return jsonify(cached_recipes)
    
    # Fetch from API
    res = get_recipes_by_ingredients(ingredients, number=(req_number if req_number is not None else 5))
    if isinstance(res, tuple) and len(res) == 2 and isinstance(res[1], int):
        payload, status = res
        return jsonify(payload), status
    
    candidates = res or []
    candidates_sorted = sorted(candidates, key=_score_recipe, reverse=True)
    
    lower_ings = set([str(x).lower() for x in (ingredients or [])])
    enriched = []
    
    # Process candidates
    for idx, candidate in enumerate(candidates_sorted):
        recipe_id = candidate.get('id')
        if not recipe_id:
            continue
        
        if idx < prefetch_n:
            # Fetch full recipe information
            info = get_recipe_information(recipe_id, include_nutrition=True)
            
            if isinstance(info, tuple) and len(info) == 2 and isinstance(info[1], int):
                # Error fetching details - use lightweight version
                enriched.append(_build_lightweight_recipe(candidate))
            elif isinstance(info, dict):
                enriched.append(_build_enriched_recipe(info, candidate, lower_ings))
            else:
                enriched.append(_build_lightweight_recipe(candidate))
        else:
            # Return lightweight recipe for remaining candidates
            enriched.append(_build_lightweight_recipe(candidate))
    
    # Cache results
    _save_cache(cache_path, enriched)
    
    return jsonify(enriched)


recipe_recommendation_bp.add_url_rule('/suggest', 'get_recipes_by_ingredients', get_ingredients_from_request, methods=['POST'])


def get_recipe_info_by_id(id):
    """GET /recipes/<id>/information - Fetch full recipe information by id."""
    try:
        numeric_id = int(id)
    except Exception:
        return jsonify({"error": "Invalid recipe id for external lookup"}), 400
    
    res = get_recipe_information(numeric_id, include_nutrition=True)
    if isinstance(res, tuple) and len(res) == 2 and isinstance(res[1], int):
        payload, status = res
        return jsonify(payload), status
    else:
        return jsonify(res)


recipe_recommendation_bp.add_url_rule('/<id>/information', 'get_recipe_information', get_recipe_info_by_id, methods=['GET'])