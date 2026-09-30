"""
Flask backend for Bangle Bliss chatbot

This app exposes a single endpoint `/api/chat` which accepts POST requests
with JSON: {"message": "..."} and proxies the message to a locally
running Ollama server (http://localhost:11434) using model `llama3.2`.

Behavior:
- Tries a few common Ollama HTTP endpoints and extracts a textual reply.
- Returns JSON {"reply": "..."} on success.
- Returns 503 with error details when Ollama is unavailable.

Run: `python app.py` (requires Flask and requests)
"""

from flask import Flask, request, jsonify
import requests
import json
import re

# Serve static files (index.html, style.css, script.js, images/) from project root
app = Flask(__name__, static_folder='.', static_url_path='')

# Configuration
OLLAMA_BASE = 'http://localhost:11434'
MODEL = 'llama3.2'

def try_ollama(message):
    """Call Ollama's /api/chat endpoint (non-streaming) and return the assistant content.

    This function calls a single, explicit Ollama endpoint with
    "stream": false to ensure we receive a complete JSON response
    instead of NDJSON streaming fragments.
    """
    url = OLLAMA_BASE + '/api/chat'
    headers = {'Content-Type': 'application/json'}
    # Add a system instruction so the model acts as the shop assistant
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": (
                "You are the official Bangle Bliss shopping assistant."
                " Keep replies concise, friendly, and professional (1-3 short sentences)."
                " Never invent product details, prices, availability, or SKUs."
                " When asked to find products, respond with a short sentence acknowledging and DO NOT list products — instead the backend will run a product search and return results as product cards."
                " For greetings or simple chit-chat, reply with a short natural phrase."
                " If the user asks for recommendations, you may suggest which of the available products (by name) to choose, but only from the actual product catalog which the backend provides."
            )},
            {"role": "user", "content": message}
        ],
        "stream": False
    }

    # Use streaming mode to handle both NDJSON streaming and non-streaming JSON
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=20, stream=True)
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f'Network error when reaching Ollama: {e}')

    if resp.status_code != 200:
        text = resp.text.strip()
        raise RuntimeError(f'Ollama returned status {resp.status_code}: {text}')

    # Attempt to parse full JSON response first
    try:
        data = resp.json()
        # same handling as before
        if isinstance(data, dict):
            choices = data.get('choices')
            if choices and isinstance(choices, list):
                first = choices[0]
                if isinstance(first, dict):
                    msg = first.get('message')
                    if isinstance(msg, dict) and 'content' in msg:
                        return msg['content']
                    if 'text' in first and isinstance(first['text'], str):
                        return first['text']
            for key in ('response', 'reply', 'output'):
                v = data.get(key)
                if isinstance(v, str) and v.strip():
                    return v
    except ValueError:
        # Not a single JSON body; fall back to NDJSON streaming parsing
        pass

    # Parse NDJSON stream lines for message.content fragments
    import json
    pieces = []
    try:
        for raw in resp.iter_lines(decode_unicode=True):
            if not raw:
                continue
            line = raw.strip()
            # Some servers may send keep-alive or other markers
            try:
                obj = json.loads(line)
            except Exception:
                # ignore non-json lines
                continue
            # Ollama streaming fragments often include {'message': {'content': '...'}, 'done': False}
            msg = obj.get('message') if isinstance(obj, dict) else None
            if isinstance(msg, dict) and 'content' in msg:
                pieces.append(msg['content'])
            # If done flag present and true, break
            if obj.get('done') is True:
                break
        if pieces:
            return ''.join(pieces)
    except Exception as e:
        raise RuntimeError(f'Error parsing Ollama stream: {e}')

    # last resort: try to return text body
    text = resp.text.strip()
    if text:
        return text
    raise RuntimeError('Could not extract assistant reply from Ollama response')


def load_products_from_script():
    """Load the products array from script.js to keep backend in sync with frontend catalog.

    This looks for a `const products = [...]` assignment and converts it to JSON.
    It's a best-effort approach intended for this project setup.
    """
    path = 'script.js'
    try:
        with open(path, 'r', encoding='utf-8') as f:
            src = f.read()
    except FileNotFoundError:
        return []

    m = re.search(r"const\s+products\s*=\s*(\[[\s\S]*?\])", src)
    if not m:
        return []
    arr_text = m.group(1)
    text = arr_text
    # Remove JS comments to avoid noise
    text = re.sub(r"//.*?$", "", text, flags=re.MULTILINE)
    text = re.sub(r"/\*[\s\S]*?\*/", "", text)

    # Extract top-level {...} objects inside the array by tracking braces
    objs = []
    i = 0
    n = len(text)
    while i < n:
        if text[i] == '{':
            depth = 0
            start = i
            while i < n:
                if text[i] == '{':
                    depth += 1
                elif text[i] == '}':
                    depth -= 1
                    if depth == 0:
                        i += 1
                        break
                i += 1
            objs.append(text[start:i])
        else:
            i += 1

    products = []
    # For each object text, parse simple key: value pairs
    pair_re = re.compile(r'''([a-zA-Z0-9_\-]+)\s*:\s*(?:'([^']*)'|"([^\"]*)"|([0-9]+(?:\.[0-9]+)?)|(true|false|null))\s*(?:,|$)''', re.IGNORECASE)
    for o in objs:
        d = {}
        for m in pair_re.finditer(o):
            key = m.group(1)
            if m.group(2) is not None:
                val = m.group(2)
            elif m.group(3) is not None:
                val = m.group(3)
            elif m.group(4) is not None:
                num = m.group(4)
                if '.' in num:
                    val = float(num)
                else:
                    val = int(num)
            else:
                t = (m.group(5) or '').lower()
                if t == 'true': val = True
                elif t == 'false': val = False
                else: val = None
            d[key] = val
        if d:
            products.append(d)
    return products


# Load products once at startup
PRODUCTS = load_products_from_script()


def parse_filters_with_ollama(message):
    """Ask Ollama to parse the user's message into a JSON filter object.

    The model is instructed to output ONLY valid JSON with keys:
      {"action": "search"|"chat", "filters": {"color":..., "max_price":..., "category":..., "size":..., "keywords": ...}}
    If parsing fails, return None.
    """
    url = OLLAMA_BASE + '/api/chat'
    headers = {'Content-Type': 'application/json'}
    system = (
        "You are a structured-data extractor for a shopping site."
        " For any user shopping query, output ONLY a single valid JSON object and nothing else."
        " The JSON must include an `action` key whose value is one of: `search`, `recommend`, or `chat`."
        " Include a `filters` object when action is `search` or `recommend`."
        " Valid filters: color (string), max_price (number), min_price(number), category(string), size(string), keywords(string)."
        " If the user asks for a recommendation (phrases like 'which one should I buy', 'recommend', 'what should I choose'), set action to `recommend` and include any inferred filters."
        " For simple greetings or chit-chat, set action to `chat` and return an empty filters object."
        " Examples:\nUser: 'Show me red bangles under ₹500' -> {\"action\":\"search\",\"filters\":{\"color\":\"red\",\"max_price\":500}}"
    )
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": message}
        ],
        "stream": False
    }
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=15)
    except requests.exceptions.RequestException:
        return None
    if resp.status_code != 200:
        return None
    text = ''
    try:
        data = resp.json()
        # extract assistant text if present
        choices = data.get('choices')
        if isinstance(choices, list) and choices:
            first = choices[0]
            msg = first.get('message') if isinstance(first, dict) else None
            if isinstance(msg, dict) and 'content' in msg:
                text = msg['content']
    except Exception:
        text = resp.text

    if not text:
        return None

    # Try to find JSON substring in the text
    jmatch = re.search(r"\{[\s\S]*\}", text)
    if not jmatch:
        return None
    jtext = jmatch.group(0)
    try:
        parsed = json.loads(jtext)
        return parsed
    except Exception:
        return None


def parse_filters_local(message):
    """A lightweight local parser for intents and filters as a fallback.

    Returns a dict like {action: 'search'|'recommend'|'chat', filters: {...}}
    or None when no local parse applies.
    """
    txt = (message or '').lower()
    # short greetings
    greetings = ['hi', 'hello', 'hey']
    for g in greetings:
        if re.fullmatch(rf".*\b{g}\b.*", txt):
            return {'action': 'chat', 'filters': {}, 'reply': "Hey! 👋 How can I help you with Bangle Bliss today?"}
    if any(w in txt for w in ('thank', 'thanks')):
        return {'action': 'chat', 'filters': {}, 'reply': "You're welcome! Glad to help."}
    if any(w in txt for w in ('bye', 'goodbye')):
        return {'action': 'chat', 'filters': {}, 'reply': "Goodbye! Come back anytime."}

    # detect recommendation intent
    if any(kw in txt for kw in ('which one should i buy', 'which should i buy', 'recommend', 'what should i choose', 'suggest')):
        action = 'recommend'
    else:
        action = None

    # price parsing
    max_price = None
    m = re.search(r'under\s*₹?\s*([0-9,]+)', txt)
    if not m:
        m = re.search(r'below\s*₹?\s*([0-9,]+)', txt)
    if not m:
        m = re.search(r'less than\s*₹?\s*([0-9,]+)', txt)
    if m:
        try:
            max_price = float(m.group(1).replace(',', ''))
        except Exception:
            max_price = None
    # between X and Y
    m2 = re.search(r'between\s*₹?\s*([0-9,]+)\s*(and|-)\s*₹?\s*([0-9,]+)', txt)
    min_price = None
    if m2:
        try:
            min_price = float(m2.group(1).replace(',', ''))
            max_price = float(m2.group(3).replace(',', ''))
        except Exception:
            min_price = None

    # simple color list match
    colors = ['red','green','blue','gold','silver','pink','white','black','brown','maroon','burgundy','multicolor']
    color = None
    for c in colors:
        if re.search(rf"\b{re.escape(c)}\b", txt):
            color = c
            break

    # category detection from PRODUCTS
    categories = set([p.get('category','').lower() for p in PRODUCTS if p.get('category')])
    category = None
    for cat in categories:
        if re.search(rf"\b{re.escape(cat)}\b", txt):
            category = cat
            break

    # if we found any relevant filter or explicit product words, treat as search
    if color or max_price is not None or min_price is not None or category:
        return {'action': action or 'search', 'filters': {'color': color, 'max_price': max_price, 'min_price': min_price, 'category': category}}

    return None



@app.route('/api/chat', methods=['POST'])
def chat():
    payload = request.get_json(force=True, silent=True) or {}
    message = payload.get('message') or payload.get('prompt') or ''
    if not message:
        return jsonify({'error': 'Missing "message" in request body'}), 400

    try:
        # First, attempt to interpret the user's intent as a product search
        parsed = parse_filters_with_ollama(message)
        # fallback to a local parser if structured parse fails
        if not parsed:
            parsed = parse_filters_local(message)
        if parsed and parsed.get('action') == 'search' and isinstance(parsed.get('filters'), dict):
            filters = parsed['filters']
            # perform server-side filtering on PRODUCTS
            results = PRODUCTS
            # color filter (simple substring match on name or category)
            color = filters.get('color')
            if color:
                lc = color.lower()
                def match_color(p):
                    # check explicit color field, name, category, description
                    if lc in str(p.get('color','')).lower():
                        return True
                    hay = ' '.join([str(p.get(k,'') or '') for k in ('name','category','description')]).lower()
                    return lc in hay
                results = [p for p in results if match_color(p)]
            # category filter
            category = filters.get('category')
            if category:
                cat_l = category.lower()
                results = [p for p in results if cat_l in str(p.get('category','')).lower()]
            # size
            size = filters.get('size')
            if size:
                results = [p for p in results if size.lower() == p.get('size','').lower()]
            # max_price
            max_price = filters.get('max_price')
            min_price = filters.get('min_price')
            def to_float(v):
                try:
                    return float(v)
                except Exception:
                    return None
            mp = to_float(max_price)
            mip = to_float(min_price)
            if mp is not None:
                results = [p for p in results if to_float(p.get('price',0)) is not None and to_float(p.get('price',0)) <= mp]
            if mip is not None:
                results = [p for p in results if to_float(p.get('price',0)) is not None and to_float(p.get('price',0)) >= mip]

            # build response payload referencing actual product fields
            if results:
                return jsonify({'response': 'search_results', 'products': results})
            else:
                return jsonify({'response': 'No matching Bangle Bliss products found.'})

        # recommendation handling: pick a single product from catalog based on inferred filters
        if parsed and parsed.get('action') == 'recommend' and isinstance(parsed.get('filters'), dict):
            filters = parsed['filters']
            results = PRODUCTS
            color = filters.get('color')
            if color:
                results = [p for p in results if color.lower() in (p.get('name','').lower() + ' ' + p.get('category','').lower() + ' ' + str(p.get('color','')).lower())]
            category = filters.get('category')
            if category:
                results = [p for p in results if category.lower() in p.get('category','').lower()]
            max_price = filters.get('max_price')
            if isinstance(max_price, (int, float)):
                results = [p for p in results if float(p.get('price',0)) <= float(max_price)]

            if not results:
                return jsonify({'response': "I couldn't find products matching those preferences."})

            # simple recommendation strategy: prefer available items, then lowest price
            avail = [p for p in results if p.get('availability')]
            pick_list = avail or results
            pick = min(pick_list, key=lambda p: float(p.get('price', 1e9)))
            explain = f"I recommend the {pick.get('name')} — {pick.get('description','A lovely choice')}. It's priced at ₹{pick.get('price')} and currently {'in stock' if pick.get('availability') else 'not in stock'} at Bangle Bliss."
            return jsonify({'response': 'recommend', 'product': pick, 'explain': explain})

        # Otherwise fallback to normal chat completion
        reply = try_ollama(message)
        return jsonify({'response': reply})
    except Exception as e:
        return jsonify({'error': 'Ollama unavailable', 'details': str(e)}), 503


@app.after_request
def add_cors(resp):
    # Allow simple CORS for local development
    resp.headers['Access-Control-Allow-Origin'] = '*'
    resp.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    resp.headers['Access-Control-Allow-Methods'] = 'GET,POST,OPTIONS'
    return resp


@app.route('/')
def index():
    # Serve the existing index.html from the project root
    return app.send_static_file('index.html')


if __name__ == '__main__':
    # Run on localhost:5000
    app.run(host='0.0.0.0', port=5000, debug=True)
