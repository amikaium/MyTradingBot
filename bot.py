import os
import time
import requests
import hmac
import hashlib
from urllib.parse import urlencode
from flask import Flask, jsonify
import threading

API_KEY = 'XAQj4j52q11U0cGBY1UTSta8SOAFAiBefCQeEpNVp0MqRgUElKkbqC87h1PFsbuc'
API_SECRET = 'Fplq9Q5MlHZ6CID31zNhUWZICiA8mumyrqu1dmdshOCZmOJFtXuimVMf2R2xVJVn'
BASE_URL = 'https://fapi.binance.com'

SYMBOLS = ['XRPUSDT', 'DOGEUSDT', 'TRXUSDT', 'ADAUSDT', 'MATICUSDT', 'LINKUSDT'] 
TAKE_PROFIT_USDT = 0.30  
TRADE_AMOUNT_USDT = 6.0 

app = Flask(__name__)

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

# 🧠 অ্যাডভান্সড প্রাইস অ্যাকশন ও RSI অ্যালগরিদম (Reversal Strategy)
def get_market_trend(symbol):
    try:
        # ১৫ মিনিটের ক্যান্ডেলস্টিক ডেটা নিবে (বেশি একুরেট)
        klines = requests.get(f"{BASE_URL}/fapi/v1/klines?symbol={symbol}&interval=15m&limit=15").json()
        
        # RSI ক্যালকুলেশন
        gains, losses = 0, 0
        for i in range(1, 14):
            change = float(klines[i][4]) - float(klines[i-1][4])
            if change > 0: gains += change
            else: losses -= change
        rs = gains / losses if losses > 0 else 100
        rsi = 100 - (100 / (1 + rs))
        
        # রিভার্সাল কনফার্মেশন (শেষ ক্লোজ হওয়া ক্যান্ডেল কি সবুজ না লাল?)
        last_open = float(klines[13][1])
        last_close = float(klines[13][4])
        is_green_candle = last_close > last_open # মার্কেট ঘুরে ওপরের দিকে উঠছে
        is_red_candle = last_close < last_open # মার্কেট ঘুরে নিচের দিকে নামছে
        
        return rsi, is_green_candle, is_red_candle
    except: return 50, False, False

active_trades = {} 

def auto_trading_loop():
    print("🚀 Pro AI Reversal Engine Started...")
    while True:
        try:
            acc_info = binance_request('GET', '/fapi/v2/account')
            if not acc_info:
                time.sleep(1)
                continue
                
            total_bal = float(acc_info['totalMarginBalance'])
            free_bal = float(acc_info['availableBalance'])
            positions = acc_info['positions']
            live_orders = []
            
            for pos in positions:
                sym = pos['symbol']
                if sym in SYMBOLS:
                    amt = float(pos['positionAmt'])
                    if amt != 0:
                        entry_price = float(pos['entryPrice'])
                        unrealized_pnl = float(pos['unrealizedProfit'])
                        estimated_fee = (abs(amt) * entry_price) * 0.001 
                        net_profit = unrealized_pnl - estimated_fee 
                        side = "LONG" if amt > 0 else "SHORT"
                        
                        live_orders.append({
                            "symbol": sym,
                            "side": side,
                            "net_profit": round(net_profit, 4)
                        })
                        
                        if net_profit >= TAKE_PROFIT_USDT:
                            print(f"💰 {sym} প্রফিট হিট! ফি বাদে রিয়েল লাভ: {net_profit} USDT.")
                            # binance_request('POST', '/fapi/v1/order', {'symbol': sym, 'side': 'SELL' if amt > 0 else 'BUY', 'type': 'MARKET', 'quantity': abs(amt)})
                            
                    elif free_bal > TRADE_AMOUNT_USDT:
                        rsi, is_green, is_red = get_market_trend(sym)
                        price = get_live_price(sym)
                        
                        if price > 0:
                            qty = round(TRADE_AMOUNT_USDT / price, 1)
                            
                            # 🟢 লজিক: মার্কেট নিচে নেমেছে (RSI < 35) + ঘুরে দাঁড়িয়েছে (Green Candle)
                            if rsi < 35 and is_green:
                                print(f"✅ {sym} Reversal Confirmed! Opening LONG...")
                                # binance_request('POST', '/fapi/v1/order', {'symbol': sym, 'side': 'BUY', 'type': 'MARKET', 'quantity': qty})
                                
                            # 🔴 লজিক: মার্কেট অনেক ওপরে (RSI > 65) + নিচে নামা শুরু করেছে (Red Candle)
                            elif rsi > 65 and is_red:
                                print(f"✅ {sym} Reversal Confirmed! Opening SHORT...")
                                # binance_request('POST', '/fapi/v1/order', {'symbol': sym, 'side': 'SELL', 'type': 'MARKET', 'quantity': qty})

            global active_trades
            active_trades = {
                "total_usdt": round(total_bal, 2),
                "free_usdt": round(free_bal, 2),
                "orders": live_orders
            }
            time.sleep(1)
            
        except Exception as e:
            time.sleep(1)

@app.route('/api/data')
def api_data():
    return jsonify(active_trades if active_trades else {"total_usdt": 0, "free_usdt": 0, "orders": []})

if __name__ == '__main__':
    threading.Thread(target=auto_trading_loop, daemon=True).start()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))
