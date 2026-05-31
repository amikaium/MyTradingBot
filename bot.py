import os
import time
import requests
from flask import Flask, jsonify
import threading

# --- কনফিগারেশন ---
API_KEY = 'XAQj4j52q11U0cGBY1UTSta8SOAFAiBefCQeEpNVp0MqRgUElKkbqC87h1PFsbuc'
API_SECRET = 'Fplq9Q5MlHZ6CID31zNhUWZICiA8mumyrqu1dmdshOCZmOJFtXuimVMf2R2xVJVn'
BASE_URL = 'https://fapi.binance.com'
SYMBOL = 'XRPUSDT'
TAKE_PROFIT_PERCENT = 2.0 

app = Flask(__name__)

# --- বাইনান্স ফাংশনসমূহ ---
def get_live_price():
    try:
        url = f"{BASE_URL}/fapi/v1/ticker/price?symbol={SYMBOL}"
        res = requests.get(url).json()
        return float(res.get('price', 0))
    except: return 0.0

# --- অটো-ট্রেডিং ইঞ্জিন ---
def auto_trading_loop():
    print("🤖 অটো-ট্রেডিং ইঞ্জিন চালু হয়েছে...")
    entry_price = 0
    has_position = False
    
    while True:
        try:
            current_price = get_live_price()
            if not has_position:
                # ট্রেড ওপেন করার লজিক এখানে বসবে
                has_position = True
                entry_price = current_price
                print(f"🟢 ট্রেড ওপেন হয়েছে। এন্ট্রি: {entry_price}")
            else:
                if entry_price > 0:
                    profit = ((current_price - entry_price) / entry_price) * 100
                    print(f"📊 বর্তমান প্রফিট: {profit:.2f}%")
                    if profit >= TAKE_PROFIT_PERCENT:
                        print("💰 প্রফিট টার্গেট হিট! ক্লোজ করা হচ্ছে...")
                        has_position = False
            time.sleep(30)
        except Exception as e:
            print(f"লুপ এরর: {e}")
            time.sleep(60)

# --- ওয়েব সার্ভার ---
@app.route('/api/data')
def api_data():
    return jsonify({"live_price": get_live_price(), "status": "Auto-Trading Active"})

if __name__ == '__main__':
    threading.Thread(target=auto_trading_loop, daemon=True).start()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))
