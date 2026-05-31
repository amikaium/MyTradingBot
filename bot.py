import os
import time
import hmac
import hashlib
import requests
from urllib.parse import urlencode
import threading
from flask import Flask, jsonify

# আপনার API Keys
API_KEY = 'XAQj4j52q11U0cGBY1UTSta8SOAFAiBefCQeEpNVp0MqRgUElKkbqC87h1PFsbuc'
API_SECRET = 'Fplq9Q5MlHZ6CID31zNhUWZICiA8mumyrqu1dmdshOCZmOJFtXuimVMf2R2xVJVn'
BASE_URL = 'https://fapi.binance.com'

app = Flask(__name__)
exchange_info = {}

# বাইনান্স এপিআই তে সিকিউর রিকোয়েস্ট পাঠানোর ফাংশন (Server Error ফিক্স)
def send_signed_request(http_method, endpoint, payload={}):
    payload['timestamp'] = int(time.time() * 1000)
    payload['recvWindow'] = 10000
    
    query_string = urlencode(payload)
    signature = hmac.new(API_SECRET.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()
    url = f"{BASE_URL}{endpoint}?{query_string}&signature={signature}"
    
    headers = {
        'X-MBX-APIKEY': API_KEY,
        'Content-Type': 'application/json'
    }
    
    try:
        if http_method == 'GET':
            res = requests.get(url, headers=headers)
        else:
            res = requests.post(url, headers=headers)
        return res.json(), res.status_code
    except Exception as e:
        return {"code": -1, "msg": str(e)}, 500

# কয়েনের ডেসিমাল প্রিসিশন আপডেট করা (ফিউচার্সে এটা খুবই জরুরি)
def update_exchange_info():
    global exchange_info
    try:
        res = requests.get(f"{BASE_URL}/fapi/v1/exchangeInfo").json()
        for s in res.get('symbols', []):
            if s['contractType'] == 'PERPETUAL':
                exchange_info[s['symbol']] = s['quantityPrecision']
    except Exception as e:
        print("Exchange Info Error:", e)

update_exchange_info()

def get_balance():
    try:
        data, status = send_signed_request('GET', '/fapi/v2/balance')
        if status == 200:
            for asset in data:
                if asset['asset'] == 'USDT':
                    return round(float(asset['balance']), 2), round(float(asset['availableBalance']), 2)
    except:
        pass
    return 0.0, 0.0

def get_auto_best_coins():
    try:
        url = f"{BASE_URL}/fapi/v1/ticker/24hr"
        res = requests.get(url).json()
        valid_coins = []
        
        for item in res:
            symbol = item.get('symbol', '')
            if symbol.endswith('USDT') and '_' not in symbol:
                change = float(item.get('priceChangePercent', 0))
                vol = float(item.get('quoteVolume', 0))
                
                # ভলিউম ভালো এবং ১.৫% থেকে ১০% লাভে আছে এমন কয়েন
                if vol > 10000000 and 1.5 < change < 10.0:
                    valid_coins.append({
                        'symbol': symbol,
                        'change': change,
                        'price': float(item.get('lastPrice', 0))
                    })
        
        valid_coins.sort(key=lambda x: x['change'], reverse=True)
        return valid_coins[:4] # সর্বোচ্চ ৪টি কয়েন
    except:
        return []

def place_auto_trades():
    _, free_bal = get_balance()
    
    if free_bal < 6: 
        return [{"symbol": "SYSTEM", "status": "error", "msg": f"Low Balance! Free USDT: {free_bal}"}]

    best_coins = get_auto_best_coins()
    if not best_coins: 
        return [{"symbol": "SYSTEM", "status": "error", "msg": "No highly profitable coins found now."}]

    trading_budget = free_bal * 0.90 # ফি এর জন্য কিছু ব্যালেন্স রেখে দিবে
    max_possible_coins = int(trading_budget // 6) 
    coins_to_trade = min(len(best_coins), max_possible_coins)
    
    if coins_to_trade == 0:
        return [{"symbol": "SYSTEM", "status": "error", "msg": "Balance too low to split."}]
        
    budget_per_coin = trading_budget / coins_to_trade
    results = []
    
    for i in range(coins_to_trade):
        coin = best_coins[i]
        symbol = coin['symbol']
        price = coin['price']
        
        raw_qty = budget_per_coin / price
        precision = exchange_info.get(symbol, 0)
        
        # ফিউচার্সের জন্য একুরেট কোয়ান্টিটি ফরম্যাট
        if precision == 0:
            qty_str = str(int(raw_qty))
        else:
            qty_str = f"{raw_qty:.{precision}f}"
            
        if float(qty_str) <= 0: continue

        payload = {
            'symbol': symbol,
            'side': 'BUY',
            'type': 'MARKET',
            'quantity': qty_str
        }
        
        data, status = send_signed_request('POST', '/fapi/v1/order', payload)
        
        if status == 200:
            results.append({"symbol": symbol, "qty": qty_str, "side": "BUY", "status": "success", "orderId": data.get('orderId')})
        else:
            results.append({"symbol": symbol, "qty": qty_str, "side": "BUY", "status": "error", "msg": data.get('msg', 'Unknown Error')})
            
    return results

@app.route('/')
def home():
    return "✅ Auto AI Trading Bot Server is Online!"

@app.route('/api/data', methods=['GET'])
def api_data():
    try:
        best_coins = get_auto_best_coins()
        prices = {coin['symbol']: coin['price'] for coin in best_coins}
        total_bal, free_bal = get_balance()
        return jsonify({
            "status": "success",
            "prices": prices,
            "total_usdt": total_bal,
            "free_usdt": free_bal
        })
    except Exception as e:
        return jsonify({"status": "error", "msg": str(e)})

@app.route('/api/trade', methods=['GET', 'POST'])
def api_trade():
    try:
        trade_results = place_auto_trades()
        return jsonify({"status": "completed", "trades": trade_results})
    except Exception as e:
        return jsonify({"status": "error", "trades": [{"symbol": "SERVER", "status": "error", "msg": str(e)}]})

def background_worker():
    while True:
        time.sleep(20) 
        
if __name__ == '__main__':
    threading.Thread(target=background_worker, daemon=True).start()
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
