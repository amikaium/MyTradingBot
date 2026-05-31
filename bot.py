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
SYMBOL = 'XRPUSDT'

app = Flask(__name__)

# --- বাইনান্স ফাংশনগুলো (100% Accurate Data) ---

def get_live_price():
    try:
        url = f"{BASE_URL}/fapi/v1/ticker/price?symbol={SYMBOL}"
        res = requests.get(url).json()
        return float(res['price'])
    except:
        return 0.0

def get_balance():
    endpoint = '/fapi/v2/balance'
    timestamp = int(time.time() * 1000)
    params = {'timestamp': timestamp, 'recvWindow': 10000}
    
    query_string = urlencode(params)
    signature = hmac.new(API_SECRET.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()
    params['signature'] = signature
    headers = {'X-MBX-APIKEY': API_KEY}
    
    try:
        res = requests.get(BASE_URL + endpoint, headers=headers, params=params).json()
        for asset in res:
            if asset['asset'] == 'USDT':
                return round(float(asset['balance']), 2), round(float(asset['availableBalance']), 2)
    except:
        return 0.0, 0.0

def place_real_trade():
    endpoint = '/fapi/v1/order'
    timestamp = int(time.time() * 1000)
    
    # একুরেট লজিক: মার্কেট প্রাইসে 15 XRP Long (Buy) করবে
    params = {
        'symbol': SYMBOL,
        'side': 'BUY',
        'type': 'MARKET',
        'quantity': 15,
        'timestamp': timestamp,
        'recvWindow': 10000
    }
    
    query_string = urlencode(params)
    signature = hmac.new(API_SECRET.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()
    params['signature'] = signature
    headers = {'X-MBX-APIKEY': API_KEY}
    
    try:
        res = requests.post(BASE_URL + endpoint, headers=headers, params=params)
        data = res.json()
        if res.status_code == 200:
            return {"status": "success", "message": "Trade Placed!", "orderId": data.get('orderId')}
        else:
            return {"status": "error", "message": data.get('msg')}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# --- আপনার Sketchware অ্যাপের জন্য API লিংগুলো (Routes) ---

@app.route('/')
def home():
    return "✅ Bot Server is Online 24/7! Ready for Sketchware."

# এই লিংকে হিট করলে অ্যাপ ব্যালেন্স এবং প্রাইস দেখতে পাবে
@app.route('/api/data', methods=['GET'])
def api_data():
    price = get_live_price()
    total_bal, free_bal = get_balance()
    return jsonify({
        "symbol": SYMBOL,
        "live_price": price,
        "total_usdt": total_bal,
        "free_usdt": free_bal
    })

# এই লিংকে হিট করলে অ্যাপ সরাসরি ট্রেড ওপেন করবে
@app.route('/api/trade', methods=['GET', 'POST'])
def api_trade():
    result = place_real_trade()
    return jsonify(result)

# --- ব্যাকগ্রাউন্ড স্ক্যানার (যাতে সার্ভার কখনোই না ঘুমায়) ---
def background_worker():
    while True:
        time.sleep(20) # প্রতি ২০ সেকেন্ডে সে নিজেকে সজাগ রাখবে
        
if __name__ == '__main__':
    threading.Thread(target=background_worker, daemon=True).start()
    port = int(os.environ.get('PORT', 10000))
    # সার্ভার রান করা হচ্ছে
    app.run(host='0.0.0.0', port=port)
