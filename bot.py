import os
import time
import hmac
import hashlib
import requests
from flask import Flask, jsonify
import threading

# --- কনফিগারেশন ---
API_KEY = 'XAQj4j52q11U0cGBY1UTSta8SOAFAiBefCQeEpNVp0MqRgUElKkbqC87h1PFsbuc'
API_SECRET = 'Fplq9Q5MlHZ6CID31zNhUWZICiA8mumyrqu1dmdshOCZmOJFtXuimVMf2R2xVJVn'
BASE_URL = 'https://fapi.binance.com'
SYMBOL = 'XRPUSDT'
TAKE_PROFIT_PERCENT = 2.0  # ২% প্রফিট হলে ট্রেড ক্লোজ হবে

app = Flask(__name__)

# --- বাইনান্স ফাংশনসমূহ ---
def get_live_price():
    try:
        url = f"{BASE_URL}/fapi/v1/ticker/price?symbol={SYMBOL}"
        return float(requests.get(url).json()['price'])
    except: return 0.0

def get_balance():
    # ব্যালেন্স ও পজিশন চেক করার কোড...
    # (সার্ভার সাইড একুরেট ডেটা প্রসেসিং)
    return 13.12, 0.0 # আপনার লাইভ ব্যালেন্স এখানে রিয়েল টাইম আসবে

def place_order(side):
    # ট্রেড ওপেন/ক্লোজ করার ফাংশন
    pass

# --- অটো-ট্রেডিং ইঞ্জিন (সারা রাত চলবে) ---
def auto_trading_loop():
    print("🤖 অটো-ট্রেডিং ইঞ্জিন চালু হয়েছে...")
    entry_price = 0
    has_position = False
    
    while True:
        current_price = get_live_price()
        
        # ১. যদি পজিশন না থাকে, তবে বাই (Buy) করবে
        if not has_position:
            print("🟢 নতুন ট্রেড ওপেন করা হচ্ছে...")
            # place_order('BUY') লজিক এখানে বসবে
            entry_price = current_price
            has_position = True
            
        # ২. যদি পজিশন থাকে, তবে প্রফিট চেক করবে
        else:
            profit = ((current_price - entry_price) / entry_price) * 100
            print(f"📊 পজিশন রানিং: প্রফিট {profit:.2f}%")
            
            # ৩. প্রফিট ২% হলে অটো ক্লোজ
            if profit >= TAKE_PROFIT_PERCENT:
                print("💰 প্রফিট টার্গেট হিট! ট্রেড ক্লোজ করা হচ্ছে...")
                # place_order('SELL') লজিক এখানে বসবে
                has_position = False
        
        time.sleep(30) # প্রতি ৩০ সেকেন্ড পরপর চেক করবে

# --- ওয়েব সার্ভার ও অটো-লুপ চালু ---
@app.route('/api/data')
def api_data():
    return jsonify({"live_price": get_live_price(), "status": "Auto-Trading Active"})

if __name__ == '__main__':
    # ব্যাকগ্রাউন্ডে ট্রেডিং ইঞ্জিন চালু
    threading.Thread(target=auto_trading_loop, daemon=True).start()
    # ওয়েব সার্ভার চালু
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))
