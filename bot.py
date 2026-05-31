import os, time, requests, hmac, hashlib
from urllib.parse import urlencode
from flask import Flask, jsonify
import threading

API_KEY = 'XAQj4j52q11U0cGBY1UTSta8SOAFAiBefCQeEpNVp0MqRgUElKkbqC87h1PFsbuc'
API_SECRET = 'Fplq9Q5MlHZ6CID31zNhUWZICiA8mumyrqu1dmdshOCZmOJFtXuimVMf2R2xVJVn'
BASE_URL = 'https://fapi.binance.com'

# কয়েন লিস্ট
SYMBOLS = ['XRPUSDT', 'DOGEUSDT', 'TRXUSDT', 'ADAUSDT', 'MATICUSDT', 'LINKUSDT'] 
TARGET_PROFIT = 0.10  # আপনার চাহিদা অনুযায়ী ১০ সেন্ট প্রফিট টার্গেট
STOP_LOSS_PCT = 0.008 # ০.৮% লস লিমিট (আরও সেফটি বাড়ানো হলো)

app = Flask(__name__)

def binance_request(method, endpoint, params=None):
    if params is None: params = {}
    params['timestamp'] = int(time.time() * 1000)
    query_string = urlencode(params)
    signature = hmac.new(API_SECRET.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()
    url = f"{BASE_URL}{endpoint}?{query_string}&signature={signature}"
    headers = {'X-MBX-APIKEY': API_KEY}
    return requests.post(url, headers=headers).json() if method == 'POST' else requests.get(url, headers=headers).json()

def auto_trading_loop():
    while True:
        try:
            acc = binance_request('GET', '/fapi/v2/account')
            free_bal = float(acc['availableBalance'])
            positions = acc['positions']
            
            for sym in SYMBOLS:
                binance_request('POST', '/fapi/v1/leverage', {'symbol': sym, 'leverage': 20})
                
                # ক্লোজ লজিক
                for pos in positions:
                    if pos['symbol'] == sym and float(pos['positionAmt']) != 0:
                        amt = float(pos['positionAmt'])
                        pnl = float(pos['unrealizedProfit'])
                        entry = float(pos['entryPrice'])
                        
                        # ১০ সেন্ট লাভ বা ০.৮% লস হলে ক্লোজ
                        if pnl >= TARGET_PROFIT or pnl <= -(abs(amt) * entry * STOP_LOSS_PCT):
                            side = 'SELL' if amt > 0 else 'BUY'
                            binance_request('POST', '/fapi/v1/order', {'symbol': sym, 'side': side, 'type': 'MARKET', 'quantity': abs(amt)})
                
                # এন্ট্রি লজিক (৩ ডলার ফ্রি থাকলেই ট্রেড ধরবে)
                if free_bal > 3.0:
                    price = float(requests.get(f"{BASE_URL}/fapi/v1/ticker/price?symbol={sym}").json()['price'])
                    qty = round((free_bal * 0.9 * 20) / price, 1)
                    binance_request('POST', '/fapi/v1/order', {'symbol': sym, 'side': 'BUY', 'type': 'MARKET', 'quantity': qty})
            
            time.sleep(0.5) 
        except: time.sleep(2)

threading.Thread(target=auto_trading_loop, daemon=True).start()
app.run(host='0.0.0.0', port=10000)
