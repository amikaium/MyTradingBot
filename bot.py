import os, time, requests, hmac, hashlib
from urllib.parse import urlencode
from flask import Flask, jsonify
import threading

# ================= কনফিগারেশন =================
API_KEY = 'XAQj4j52q11U0cGBY1UTSta8SOAFAiBefCQeEpNVp0MqRgUElKkbqC87h1PFsbuc'
API_SECRET = 'Fplq9Q5MlHZ6CID31zNhUWZICiA8mumyrqu1dmdshOCZmOJFtXuimVMf2R2xVJVn'
BASE_URL = 'https://fapi.binance.com'

SYMBOLS = ['XRPUSDT', 'DOGEUSDT', 'TRXUSDT', 'ADAUSDT', 'MATICUSDT', 'LINKUSDT'] 
TARGET_PROFIT = 0.10  # ফি কাটার পর একদম পকেটে ১০ সেন্ট ঢুকলে তবেই ক্লোজ করবে
STOP_LOSS_PCT = 0.008 # ০.৮% লস লিমিট

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

# 🧠 মার্কেট এনালাইসিস ফাংশন (RSI + Price Action)
def get_market_trend(symbol):
    try:
        klines = requests.get(f"{BASE_URL}/fapi/v1/klines?symbol={symbol}&interval=1m&limit=15").json()
        gains, losses = 0, 0
        for i in range(1, 14):
            change = float(klines[i][4]) - float(klines[i-1][4])
            if change > 0: gains += change
            else: losses -= change
        rs = gains / losses if losses > 0 else 100
        rsi = 100 - (100 / (1 + rs))
        
        last_open = float(klines[13][1])
        last_close = float(klines[13][4])
        is_green_candle = last_close > last_open 
        is_red_candle = last_close < last_open 
        
        return rsi, is_green_candle, is_red_candle
    except: return 50, False, False

active_trades = {}

def auto_trading_loop():
    print("🚀 Pro AI Analysis + Net-Profit Engine Started...")
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
                        gross_pnl = float(pos['unrealizedProfit'])
                        entry = float(pos['entryPrice'])
                        
                        # 💡 বাইনান্সের ফি ক্যালকুলেশন
                        position_value = abs(amt) * entry
                        estimated_fee = position_value * 0.001 
                        
                        # আসল লাভ (Net Profit)
                        net_pnl = gross_pnl - estimated_fee
                        side = "LONG" if amt > 0 else "SHORT"
                        
                        live_orders.append({
                            "symbol": sym,
                            "side": side,
                            "net_profit": round(net_pnl, 4)
                        })
                        
                        # ১০ সেন্ট আসল লাভ হলে ক্লোজ
                        if net_pnl >= TARGET_PROFIT or net_pnl <= -(position_value * STOP_LOSS_PCT):
                            print(f"⚡ {sym} Closing Trade! Net PNL: {net_pnl}")
                            close_side = 'SELL' if amt > 0 else 'BUY'
                            binance_request('POST', '/fapi/v1/order', {'symbol': sym, 'side': close_side, 'type': 'MARKET', 'quantity': abs(amt)})
                
                # 🧠 নতুন ট্রেড ধরার লজিক (মার্কেট এনালাইসিস করে)
                if free_bal > 3.0:
                    try:
                        rsi, is_green, is_red = get_market_trend(sym)
                        price = float(requests.get(f"{BASE_URL}/fapi/v1/ticker/price?symbol={sym}").json()['price'])
                        qty = round((free_bal * 0.9 * 20) / price, 1) 
                        
                        if qty > 0:
                            # 🟢 RSI নিচে নামলে এবং সবুজ ক্যান্ডেল হলে LONG
                            if rsi < 45 and is_green:
                                binance_request('POST', '/fapi/v1/order', {'symbol': sym, 'side': 'BUY', 'type': 'MARKET', 'quantity': qty})
                                time.sleep(1) 
                            # 🔴 RSI উপরে উঠলে এবং লাল ক্যান্ডেল হলে SHORT
                            elif rsi > 55 and is_red:
                                binance_request('POST', '/fapi/v1/order', {'symbol': sym, 'side': 'SELL', 'type': 'MARKET', 'quantity': qty})
                                time.sleep(1)
                    except: pass
            
            global active_trades
            active_trades = {
                "total_usdt": round(total_bal, 2),
                "free_usdt": round(free_bal, 2),
                "orders": live_orders
            }
            time.sleep(0.5) 
            
        except Exception as e:
            time.sleep(2)

@app.route('/api/data')
def api_data():
    return jsonify(active_trades if active_trades else {"total_usdt": 0, "free_usdt": 0, "orders": []})

if __name__ == '__main__':
    threading.Thread(target=auto_trading_loop, daemon=True).start()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))
