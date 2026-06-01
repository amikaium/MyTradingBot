import os, time, requests, hmac, hashlib
from urllib.parse import urlencode
from flask import Flask, jsonify
import threading

# ================= কনফিগারেশন =================
API_KEY = 'XAQj4j52q11U0cGBY1UTSta8SOAFAiBefCQeEpNVp0MqRgUElKkbqC87h1PFsbuc'
API_SECRET = 'Fplq9Q5MlHZ6CID31zNhUWZICiA8mumyrqu1dmdshOCZmOJFtXuimVMf2R2xVJVn'
BASE_URL = 'https://fapi.binance.com'

# বটের ট্রেডিং পেয়ার
SYMBOLS = ['XRPUSDT', 'DOGEUSDT', 'TRXUSDT', 'ADAUSDT', 'MATICUSDT', 'LINKUSDT'] 
TARGET_PROFIT = 0.10  # ১০ সেন্ট লাভ হলেই ক্লোজ করবে
STOP_LOSS_PCT = 0.008 # ০.৮% লস হলে ব্যালেন্স বাঁচাতে ক্লোজ করবে

app = Flask(__name__)

def binance_request(method, endpoint, params=None):
    if params is None: params = {}
    params['timestamp'] = int(time.time() * 1000)
    query_string = urlencode(params)
    signature = hmac.new(API_SECRET.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()
    url = f"{BASE_URL}{endpoint}?{query_string}&signature={signature}"
    headers = {'X-MBX-APIKEY': API_KEY}
    try:
        return requests.post(url, headers=headers).json() if method == 'POST' else requests.get(url, headers=headers).json()
    except: return None

active_trades = {}

def auto_trading_loop():
    print("🚀 Pro 10-Cent Scalping Engine Started...")
    while True:
        try:
            acc = binance_request('GET', '/fapi/v2/account')
            if not acc:
                time.sleep(1)
                continue
                
            total_bal = float(acc['totalMarginBalance'])
            free_bal = float(acc['availableBalance'])
            positions = acc['positions']
            live_orders = []
            
            for sym in SYMBOLS:
                # সব কয়েনে ২০x লেভারেজ সেট করা
                binance_request('POST', '/fapi/v1/leverage', {'symbol': sym, 'leverage': 20})
                
                # পজিশন চেক এবং ক্লোজ লজিক
                for pos in positions:
                    if pos['symbol'] == sym and float(pos['positionAmt']) != 0:
                        amt = float(pos['positionAmt'])
                        pnl = float(pos['unrealizedProfit'])
                        entry = float(pos['entryPrice'])
                        side = "LONG" if amt > 0 else "SHORT"
                        
                        live_orders.append({
                            "symbol": sym,
                            "side": side,
                            "net_profit": round(pnl, 4)
                        })
                        
                        # ১০ সেন্ট লাভ বা নির্দিষ্ট লস হলে সাথে সাথে ক্লোজ
                        if pnl >= TARGET_PROFIT or pnl <= -(abs(amt) * entry * STOP_LOSS_PCT):
                            print(f"⚡ {sym} Closing Trade! PNL: {pnl}")
                            close_side = 'SELL' if amt > 0 else 'BUY'
                            binance_request('POST', '/fapi/v1/order', {'symbol': sym, 'side': close_side, 'type': 'MARKET', 'quantity': abs(amt)})
                
                # নতুন ট্রেড ধরার লজিক (ব্যালেন্সের ওপর ডিপেন্ড করে)
                if free_bal > 3.0:
                    try:
                        price = float(requests.get(f"{BASE_URL}/fapi/v1/ticker/price?symbol={sym}").json()['price'])
                        # ব্যালেন্সের ৯০% ব্যবহার করে ২০x লেভারেজে ট্রেড ধরবে
                        qty = round((free_bal * 0.9 * 20) / price, 1) 
                        if qty > 0:
                            binance_request('POST', '/fapi/v1/order', {'symbol': sym, 'side': 'BUY', 'type': 'MARKET', 'quantity': qty})
                            time.sleep(1) # একসাথে অনেকগুলো না ধরে একটা ধরার পর ওয়েট করবে
                    except: pass
            
            global active_trades
            active_trades = {
                "total_usdt": round(total_bal, 2),
                "free_usdt": round(free_bal, 2),
                "orders": live_orders
            }
            time.sleep(0.5) # সুপার ফাস্ট আপডেট
            
        except Exception as e:
            time.sleep(2)

@app.route('/api/data')
def api_data():
    return jsonify(active_trades if active_trades else {"total_usdt": 0, "free_usdt": 0, "orders": []})

if __name__ == '__main__':
    threading.Thread(target=auto_trading_loop, daemon=True).start()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))
