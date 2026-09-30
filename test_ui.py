import requests

BASE = 'http://127.0.0.1:5000'

def check_home():
    try:
        r = requests.get(BASE + '/', timeout=5)
    except Exception as e:
        print('HOME: request failed', e); return False
    ok = True
    text = r.text
    if 'Elegance on Every Wrist' in text:
        print('HOME: hero text found')
    else:
        print('HOME: hero text NOT found'); ok = False
    if 'style.css' in text:
        print('HOME: style.css linked')
    else:
        print('HOME: style.css NOT linked'); ok = False
    if 'chat-messages' in text or 'Bliss AI' in text:
        print('HOME: chat UI present')
    else:
        print('HOME: chat UI missing'); ok = False
    return ok


def check_chat():
    try:
        r = requests.post(BASE + '/api/chat', json={'message':'show me red bangles'}, timeout=8)
    except Exception as e:
        print('CHAT: request failed', e); return False
    try:
        j = r.json()
        print('CHAT: got JSON:', list(j.keys()))
        return True
    except Exception as e:
        print('CHAT: invalid JSON response', e); return False

if __name__ == '__main__':
    h = check_home()
    c = check_chat()
    print('RESULTS home=', h, 'chat=', c)
