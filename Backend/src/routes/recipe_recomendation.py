from flask import Blueprint, request, jsonify
import os
import json
import hashlib
import time
from pathlib import Path

from ..controllers.recipe_controller import get_recipes_by_ingredients, get_recipe_information

recipe_recommendation_bp = Blueprint('recipe_recommendation', __name__, url_prefix='/recipes')

def get_ingredients_from_request():
    """
    Accepts JSON { ingredients: [...] }
    Returns an array of enriched recipe objects. Workflow:
      - call findByIngredients
      - sort candidates by usedIngredientCount desc (prioritize recipes that use more of the fridge items)
      - for each candidate call information with include_nutrition=True and merge results
    Responses are cached in controller layer to reduce external requests.
    """
    data = request.get_json()
    if not data or 'ingredients' not in data:
        return jsonify({"error": "No ingredients provided"}), 400

    ingredients = data['ingredients']
    # optional: allow client to request more results (capped by backend)
    req_number = data.get('number') if isinstance(data, dict) else None
    # coerce number to int or None to satisfy callers and static analysis
    try:
        req_number = int(req_number) if req_number is not None else None
    except Exception:
        req_number = None
    # optional: how many candidates to prefetch full details for (default: 5)
    prefetch_n = data.get('prefetch') if isinstance(data, dict) else None
    try:
        prefetch_n = int(prefetch_n) if prefetch_n is not None else 5
    except Exception:
        prefetch_n = 5
    # default prefetch_n is an integer now; prepare optional file-backed cache
    CACHE_DIR = os.environ.get('EP_RECIPE_CACHE_DIR') or os.path.join(os.getcwd(), 'cache')
    CACHE_TTL = int(os.environ.get('EP_RECIPE_CACHE_TTL', str(60 * 60 * 24)))  # default 24h
    try:
        Path(CACHE_DIR).mkdir(parents=True, exist_ok=True)
    except Exception:
        CACHE_DIR = None

    cache_path = None
    if CACHE_DIR:
        try:
            key_src = json.dumps({
                'ings': sorted([str(x).lower() for x in (ingredients or [])]),
                'number': int(req_number) if req_number is not None else None,
                'prefetch': int(prefetch_n)
            }, separators=(',', ':'), ensure_ascii=False)
            cache_key = hashlib.sha1(key_src.encode('utf-8')).hexdigest()
            cache_path = os.path.join(CACHE_DIR, f'recipes_{cache_key}.json')
            if os.path.exists(cache_path):
                mtime = os.path.getmtime(cache_path)
                if (time.time() - mtime) < CACHE_TTL:
                    try:
                        with open(cache_path, 'r', encoding='utf-8') as fh:
                            cached = json.load(fh)
                        # validate cached payload: accept only if at least one item has an 'ingredients' list
                        if isinstance(cached, list) and any(isinstance(it, dict) and isinstance(it.get('ingredients'), list) for it in cached):
                            return jsonify(cached)
                        # otherwise treat cache as stale/invalid and regenerate
                    except Exception:
                        cache_path = None
        except Exception:
            cache_path = None

    # first-level search (this returns lightweight candidate objects from Spoonacular)
    # Ensure we pass an int for `number` (controller expects int)
    res = get_recipes_by_ingredients(ingredients, number=(req_number if req_number is not None else 5))
    # controller may return (payload, status) on error
    if isinstance(res, tuple) and len(res) == 2 and isinstance(res[1], int):
        payload, status = res
        return jsonify(payload), status

    candidates = res or []

    # sort by usedIngredientCount desc, then by usedIngredientCount/total ratio
    def score(item):
        used = int(item.get('usedIngredientCount', 0))
        missed = int(item.get('missedIngredientCount', 0))
        total = used + missed if (used + missed) > 0 else 1
        return (used, used / total)

    candidates_sorted = sorted(candidates, key=score, reverse=True)

    enriched = []
    # We'll prefetch full information only for the first `prefetch_n` candidates.
    # For the remaining candidates we return lightweight objects derived from the
    # initial search (so the frontend can show image/title/ingredient counts and
    # compute availability from used/missed ingredient names without extra API calls).
    lower_ings = set([str(x).lower() for x in (ingredients or [])])
    for idx, c in enumerate(candidates_sorted):
        rid = c.get('id')
        if not rid:
            continue

        # Prefetch detailed info only for top N
        if idx < prefetch_n:
            info = get_recipe_information(rid, include_nutrition=True)
            # controller may return (payload, status)
            if isinstance(info, tuple) and len(info) == 2 and isinstance(info[1], int):
                payload, status = info
                # Build a lightweight ingredients list from the search result so the frontend
                # can still compute totals and availability even if detailed info failed.
                lightweight_ings = []
                for el in (c.get('usedIngredients') or []):
                    name = el.get('name') or el.get('original') or ''
                    lightweight_ings.append({
                        'id': el.get('id'),
                        'name': name,
                        'original': el.get('original') if 'original' in el else None,
                        'amount': el.get('amount') if 'amount' in el else None,
                        'unit': el.get('unit') if 'unit' in el else None,
                        'available': True
                    })
                for el in (c.get('missedIngredients') or []):
                    name = el.get('name') or el.get('original') or ''
                    lightweight_ings.append({
                        'id': el.get('id'),
                        'name': name,
                        'original': el.get('original') if 'original' in el else None,
                        'amount': el.get('amount') if 'amount' in el else None,
                        'unit': el.get('unit') if 'unit' in el else None,
                        'available': False
                    })

                enriched.append({
                    'id': c.get('id'),
                    'name': c.get('title') or c.get('name'),
                    'image': c.get('image'),
                    'usedIngredientCount': c.get('usedIngredientCount', 0),
                    'missedIngredientCount': c.get('missedIngredientCount', 0),
                    'ingredients': lightweight_ings,
                    # defaults for missing fields so frontend can compute and display non-empty cards
                    'readyInMinutes': 30,
                    'servings': 1,
                    'summary': 'No detailed description available. This recipe was returned from a search result.',
                    'steps': [{'number': 1, 'step': 'Follow the source recipe steps.'}],
                    'nutrition': None,
                    'error': payload
                })
                continue

            # Normalize info to a dict for safe attribute access. The controller
            # may return either a payload dict or a (payload, status) tuple.
            if isinstance(info, tuple):
                # Extract payload if present and is a dict
                payload = info[0] if len(info) > 0 else None
                data_info = payload if isinstance(payload, dict) else {}
            elif isinstance(info, dict):
                data_info = info
            else:
                data_info = {}
            # use extendedIngredients to build availability flags
            extended = data_info.get('extendedIngredients') or []
            mapped_ings = []
            for el in extended:
                # some upstream data may be strings or malformed; guard for dicts
                if not isinstance(el, dict):
                    continue
                name = el.get('name') or el.get('originalName') or ''
                mapped_ings.append({
                    'id': el.get('id'),
                    'name': name,
                    'original': el.get('original'),
                    'amount': el.get('amount'),
                    'unit': el.get('unit'),
                    'available': (name.lower() in lower_ings)
                })

            # safe defaults if upstream returned incomplete info
            ready = data_info.get('readyInMinutes') or 30
            serv = data_info.get('servings') or 1
            summ = data_info.get('summary') or 'No detailed description available.'
            # Safely extract steps from analyzedInstructions if present
            ai = data_info.get('analyzedInstructions')
            if isinstance(ai, list) and len(ai) > 0 and isinstance(ai[0], dict):
                steps_payload = ai[0].get('steps') or []
            else:
                steps_payload = []
            if not steps_payload:
                steps_payload = [{'number': 1, 'step': 'Follow the source recipe steps.'}]

            enriched.append({
                'id': data_info.get('id') or c.get('id'),
                'name': data_info.get('title') or c.get('title') or c.get('name'),
                'image': data_info.get('image') or c.get('image'),
                'readyInMinutes': ready,
                'servings': serv,
                'summary': summ,
                'dishTypes': data_info.get('dishTypes') or [],
                'usedIngredientCount': c.get('usedIngredientCount', 0),
                'missedIngredientCount': c.get('missedIngredientCount', 0),
                'ingredients': mapped_ings,
                'steps': steps_payload,
                'nutrition': data_info.get('nutrition') or None,
                'sourceUrl': data_info.get('sourceUrl') or data_info.get('spoonacularSourceUrl')
            })
        else:
            # Lightweight candidate payload derived from the search result.
            # Spoonacular's findByIngredients typically returns 'usedIngredients' and 'missedIngredients' arrays.
            lightweight_ings = []
            for el in (c.get('usedIngredients') or []):
                name = el.get('name') or el.get('original') or ''
                lightweight_ings.append({
                    'id': el.get('id'),
                    'name': name,
                    'original': el.get('original') if 'original' in el else None,
                    'amount': el.get('amount') if 'amount' in el else None,
                    'unit': el.get('unit') if 'unit' in el else None,
                    'available': True
                })
            for el in (c.get('missedIngredients') or []):
                name = el.get('name') or el.get('original') or ''
                lightweight_ings.append({
                    'id': el.get('id'),
                    'name': name,
                    'original': el.get('original') if 'original' in el else None,
                    'amount': el.get('amount') if 'amount' in el else None,
                    'unit': el.get('unit') if 'unit' in el else None,
                    'available': False
                })

            enriched.append({
                'id': c.get('id'),
                'name': c.get('title') or c.get('name'),
                'image': c.get('image'),
                # set sane defaults so UI shows something useful when details are not available
                'readyInMinutes': 30,
                'servings': 1,
                'summary': 'No detailed description available. This recipe was returned from a search result.',
                'dishTypes': [],
                'usedIngredientCount': c.get('usedIngredientCount', 0),
                'missedIngredientCount': c.get('missedIngredientCount', 0),
                'ingredients': lightweight_ings,
                'steps': [{'number': 1, 'step': 'Follow the source recipe steps.'}],
                'nutrition': None,
                'sourceUrl': None,
                'lightweight': True
            })

    # persist enriched result to file cache (atomic write) so subsequent identical
    # requests can be served without refetching external APIs
    if cache_path:
        try:
            tmp_path = cache_path + '.tmp'
            with open(tmp_path, 'w', encoding='utf-8') as fh:
                json.dump(enriched, fh, ensure_ascii=False)
            try:
                os.replace(tmp_path, cache_path)
            except Exception:
                # fallback to os.rename for older Python/FS
                os.rename(tmp_path, cache_path)
        except Exception:
            # ignore cache write errors
            pass

    return jsonify(enriched)


recipe_recommendation_bp.add_url_rule('/suggest', 'get_recipes_by_ingredients', get_ingredients_from_request, methods=['POST'])


def get_recipe_info_by_id(id):
    # proxy route to fetch full recipe information by id
    # We accept string ids to support static/front-end ids, but only numeric ids are
    # proxied to Spoonacular. We force include_nutrition=True regardless of query params
    from ..controllers.recipe_controller import get_recipe_information

    # try to coerce numeric id
    numeric_id = None
    try:
        numeric_id = int(id)
    except Exception:
        numeric_id = None

    if numeric_id is None:
        return jsonify({"error": "Invalid recipe id for external lookup"}), 400

    # ignore incoming includeNutrition query param and force true
    res = get_recipe_information(numeric_id, include_nutrition=True)
    # controller may return (payload, status) or payload
    if isinstance(res, tuple) and len(res) == 2 and isinstance(res[1], int):
        payload, status = res
        return jsonify(payload), status
    else:
        return jsonify(res)


recipe_recommendation_bp.add_url_rule('/<id>/information', 'get_recipe_information', get_recipe_info_by_id, methods=['GET'])