import os
import time
import requests
import hmac
import hashlib
from urllib.parse import urlencode
from flask import Flask, jsonify
import threading

# ================= কনফিগারেশন =================
API_KEY = 'XAQj4j52q11U0cGBY1UTSta8SOAFAiBefCQeEpNVp0MqRgUElKkbqC87h1PFsbuc'
API_SECRET = 'Fplq9Q5MlHZ6CID31zNhUWZICiA8mumyrqu1dmdshOCZmOJFtXuimVMf2R2xVJVn'
BASE_URL = 'https://fapi.binance.com'

# বটের ট্রেডিং পেয়ার (একাধিক কয়েনে ট্রেড ধরবে)
SYMBOLS = ['XRPUSDT', 'DOGEUSDT', 'TRXUSDT'] 
TAKE_PROFIT_USDT = 0.50  # প্রতি ট্রেডে ৫০ সেন্ট (ফি বাদে) লাভ হলে ক্লোজ করবে
TRADE_AMOUNT_USDT = 15.0 # আপনার ব্যালেন্স থেকে প্রতি ট্রেডে ১৫ ডলার ব্যবহার করবে

app = Flask(__name__)

# ================= বাইনান্স API ফাংশন =================
def binance_request(method, endpoint, params=None):
    if params is None: params = {}
    params['timestamp'] = int(time.time() * 1000)
    params['recvWindow'] = 10000
    query_string = urlencode(params)
    signature = hmac.new(API_SECRET.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()
    url = f"{BASE_URL}{endpoint}?{query_string}&signature={signature}"
    headers = {'X-MBX-APIKEY': API_KEY}
    
    try:
        if method == 'GET': return requests.get(url, headers=headers).json()
        elif method == 'POST': return requests.post(url, headers=headers).json()
    except: return None

def get_live_price(symbol):
    try: return float(requests.get(f"{BASE_URL}/fapi/v1/ticker/price?symbol={symbol}").json()['price'])
    except: return 0.0

# ================= অটো-ট্রেডিং লজিক (২৪ ঘণ্টা চলবে) =================
active_trades = {} # লাইভ ট্রেড ডেটা অ্যাপে পাঠানোর জন্য

def auto_trading_loop():
    print("🚀 Pro Auto-Trading Engine Started...")
    while True:
        try:
            # ১. অ্যাকাউন্টের বর্তমান অবস্থা চেক করা
            acc_info = binance_request('GET', '/fapi/v2/account')
            if not acc_info:
                time.sleep(10)
                continue
                
            total_bal = float(acc_info['totalMarginBalance'])
            free_bal = float(acc_info['availableBalance'])
            
            # ২. চলমান পজিশনগুলোর হিসাব বের করা
            positions = acc_info['positions']
            live_orders = []
            
            for pos in positions:
                sym = pos['symbol']
                if sym in SYMBOLS:
                    amt = float(pos['positionAmt'])
                    if amt != 0:
                        entry_price = float(pos['entryPrice'])
                        unrealized_pnl = float(pos['unrealizedProfit'])
                        
                        # ফিস ক্যালকুলেশন (বাইনান্সের 0.05% Taker Fee অনুযায়ী)
                        # ওপেন + ক্লোজ মিলে আনুমানিক 0.1% ফি ধরা হলো
                        position_value = abs(amt) * entry_price
                        estimated_fee = position_value * 0.001 
                        net_profit = unrealized_pnl - estimated_fee # ফি বাদ দিয়ে আসল লাভ
                        
                        side = "BUY" if amt > 0 else "SELL"
                        
                        live_orders.append({
                            "symbol": sym,
                            "side": side,
                            "size": abs(amt),
                            "entry": entry_price,
                            "net_profit": round(net_profit, 4)
                        })
                        
                        # অটো প্রফিট বুকিং (Take Profit)
                        if net_profit >= TAKE_PROFIT_USDT:
                            print(f"💰 {sym} প্রফিট হিট! ফি বাদে লাভ: {net_profit} USDT. ক্লোজ করা হচ্ছে...")
                            # এখানে রিয়েল ক্লোজ অর্ডার বসবে
                            # binance_request('POST', '/fapi/v1/order', {'symbol': sym, 'side': 'SELL' if side=='BUY' else 'BUY', 'type': 'MARKET', 'quantity': abs(amt)})
                            
                    elif free_bal > TRADE_AMOUNT_USDT:
                        # যদি পজিশন না থাকে এবং ব্যালেন্স থাকে, নতুন ট্রেড ধরবে
                        price = get_live_price(sym)
                        if price > 0:
                            qty = round(TRADE_AMOUNT_USDT / price, 1)
                            print(f"🟢 {sym} এ নতুন {qty} সাইজের ট্রেড ওপেন করা হচ্ছে...")
                            # binance_request('POST', '/fapi/v1/order', {'symbol': sym, 'side': 'BUY', 'type': 'MARKET', 'quantity': qty})
            
            # ডেটা আপডেট (যাতে অ্যাপ দেখতে পারে)
            global active_trades
            active_trades = {
                "total_usdt": round(total_bal, 2),
                "free_usdt": round(free_bal, 2),
                "orders": live_orders
            }
            
            time.sleep(15) # প্রতি ১৫ সেকেন্ডে মার্কেট স্ক্যান করবে
            
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(30)

# ================= API রাউট (অ্যাপের জন্য) =================
@app.route('/api/data')
def api_data():
    return jsonify(active_trades if active_trades else {"total_usdt": 0, "free_usdt": 0, "orders": []})

if __name__ == '__main__':
    threading.Thread(target=auto_trading_loop, daemon=True).start()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))
