import os
import time
import hmac
import hashlib
import requests
from urllib.parse import urlencode
import threading
from flask import Flask, jsonify

# আপনার API Keys (ডেমো)
API_KEY = 'XAQj4j52q11U0cGBY1UTSta8SOAFAiBefCQeEpNVp0MqRgUElKkbqC87h1PFsbuc'
API_SECRET = 'Fplq9Q5MlHZ6CID31zNhUWZICiA8mumyrqu1dmdshOCZmOJFtXuimVMf2R2xVJVn'
BASE_URL = 'https://fapi.binance.com'

app = Flask(__name__)
exchange_info = {}

# বাইনান্স থেকে কয়েনের ডেসিমাল প্রিসিশন (Decimal Precision) বের করা
def update_exchange_info():
    global exchange_info
    try:
        res = requests.get(f"{BASE_URL}/fapi/v1/exchangeInfo").json()
        for s in res['symbols']:
            if s['contractType'] == 'PERPETUAL':
                exchange_info[s['symbol']] = s['quantityPrecision']
    except:
        pass

# সার্ভার রান হওয়ার সাথে সাথেই একবার প্রিসিশন আপডেট করে নিবে
update_exchange_info()

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

# 🤖 বটের ব্রেইন: অটোমেটিক লাভজনক কয়েন খুঁজে বের করবে
def get_auto_best_coins():
    try:
        url = f"{BASE_URL}/fapi/v1/ticker/24hr"
        res = requests.get(url).json()
        valid_coins = []
        
        for item in res:
            symbol = item['symbol']
            # শুধুমাত্র USDT পেয়ার নিবে
            if symbol.endswith('USDT') and '_' not in symbol:
                change = float(item['priceChangePercent'])
                vol = float(item['quoteVolume'])
                
                # লজিক: ভলিউম ১০ মিলিয়নের বেশি এবং প্রাইস ১% থেকে ১২% আপ আছে (মানে পজিশন ভালো)
                if vol > 10000000 and 1.0 < change < 12.0:
                    valid_coins.append({
                        'symbol': symbol,
                        'change': change,
                        'price': float(item['lastPrice'])
                    })
        
        # সবচেয়ে বেশি পারসেন্টেজ লাভ থাকা কয়েনগুলো আগে আনবে (Sorting)
        valid_coins.sort(key=lambda x: x['change'], reverse=True)
        return valid_coins[:4] # সর্বোচ্চ ৪টি কয়েন সিলেক্ট করবে
    except:
        return []

def place_auto_trades():
    _, free_bal = get_balance()
    
    # ব্যালেন্স ৫ ডলারের কম হলে ট্রেড করবে না
    if free_bal < 5: 
        return [{"symbol": "ALL", "status": "error", "msg": "Low Balance! Need at least 5 USDT."}]

    best_coins = get_auto_best_coins()
    if not best_coins: 
        return [{"symbol": "ALL", "status": "error", "msg": "No good coins found in market right now."}]

    # ব্যালেন্স অটো-ক্যালকুলেশন (ফ্রি ব্যালেন্সের ৯৫% ব্যবহার করবে)
    trading_budget = free_bal * 0.95 
    
    # বাইনান্সে মিনিমাম ৫ ডলার না হলে ট্রেড হয় না, তাই কয়েন সংখ্যা ব্যালেন্স অনুযায়ী ঠিক করবে
    max_possible_coins = int(trading_budget // 6) 
    coins_to_trade = min(len(best_coins), max_possible_coins)
    
    if coins_to_trade == 0:
        return [{"symbol": "ALL", "status": "error", "msg": "Balance too low for multiple pairs."}]
        
    budget_per_coin = trading_budget / coins_to_trade
    results = []
    endpoint = '/fapi/v1/order'
    
    for i in range(coins_to_trade):
        coin = best_coins[i]
        symbol = coin['symbol']
        price = coin['price']
        
        # অটোমেটিক Quantity বের করা (Budget / Live Price)
        raw_qty = budget_per_coin / price
        precision = exchange_info.get(symbol, 0)
        
        if precision == 0:
            qty = int(raw_qty)
        else:
            qty = round(raw_qty, precision)
            
        if qty <= 0: continue

        timestamp = int(time.time() * 1000)
        params = {
            'symbol': symbol,
            'side': 'BUY',
            'type': 'MARKET',
            'quantity': qty,
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
                results.append({"symbol": symbol, "qty": qty, "side": "BUY", "status": "success", "orderId": data.get('orderId')})
            else:
                results.append({"symbol": symbol, "qty": qty, "side": "BUY", "status": "error", "msg": data.get('msg')})
        except Exception as e:
            results.append({"symbol": symbol, "status": "error", "msg": str(e)})
            
    return results

@app.route('/')
def home():
    return "✅ Auto AI Trading Bot Server is Online!"

@app.route('/api/data', methods=['GET'])
def api_data():
    best_coins = get_auto_best_coins()
    prices = {coin['symbol']: coin['price'] for coin in best_coins}
    total_bal, free_bal = get_balance()
    return jsonify({
        "prices": prices, # বট যে কয়েনগুলোকে এখন টার্গেট করেছে, সেগুলোর প্রাইস দেখাবে
        "total_usdt": total_bal,
        "free_usdt": free_bal
    })

@app.route('/api/trade', methods=['GET', 'POST'])
def api_trade():
    trade_results = place_auto_trades()
    return jsonify({"status": "completed", "trades": trade_results})

def background_worker():
    while True:
        time.sleep(20) 
        
if __name__ == '__main__':
    threading.Thread(target=background_worker, daemon=True).start()
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
