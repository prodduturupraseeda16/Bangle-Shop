import requests, json

URL = 'http://localhost:5000/api/chat'

tests = [
    'hey',
    'can you help me find red color bangles?',
    'show me red bangles under 1500',
    'Which one should I buy?',
    'do you have purple bangles?'
]

for t in tests:
    print('---')
    print('USER:', t)
    try:
        r = requests.post(URL, json={'message': t}, timeout=10)
        print('STATUS', r.status_code)
        try:
            data = r.json()
            print(json.dumps(data, indent=2, ensure_ascii=False))
        except Exception:
            print('Non-JSON response:', r.text)
    except Exception as e:
        print('Request error:', e)

print('Done')
