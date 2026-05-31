import time
import requests
import hmac
import hashlib
from urllib.parse import urlencode
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import os

# ---------------------------------------------------------
# ১. ফেক ওয়েব সার্ভার (Render-কে খুশি করার জন্য!)
# ---------------------------------------------------------
class DummyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"Bot is running successfully 24/7!")

def run_dummy_server():
    port = int(os.environ.get('PORT', 10000))
    server = HTTPServer(('0.0.0.0', port), DummyHandler)
    server.serve_forever()

# সার্ভারটি একটি আলাদা ব্যাকগ্রাউন্ড থ্রেডে চালু করে দেওয়া হলো
threading.Thread(target=run_dummy_server, daemon=True).start()

# ---------------------------------------------------------
# ২. আপনার অরিজিনাল বটের কোড 
# ---------------------------------------------------------
API_KEY = 'XAQj4j52q11U0cGBY1UTSta8SOAFAiBefCQeEpNVp0MqRgUElKkbqC87h1PFsbuc'
API_SECRET = 'Fplq9Q5MlHZ6CID31zNhUWZICiA8mumyrqu1dmdshOCZmOJFtXuimVMf2R2xVJVn'
BASE_URL = 'https://fapi.binance.com'
SYMBOL = 'XRPUSDT'

print("🚀 24/7 Smart Trading Bot Started on Render Server!\n")

def get_live_price():
    try:
        url = f"{BASE_URL}/fapi/v1/ticker/price?symbol={SYMBOL}"
        res = requests.get(url).json()
        return float(res['price'])
    except Exception as e:
        print(f"প্রাইস ফেচ এরর: {e}")
        return None

def check_balance():
    endpoint = '/fapi/v2/balance'
    timestamp = int(time.time() * 1000)
    params = {'timestamp': timestamp, 'recvWindow': 10000}
    
    query_string = urlencode(params)
    signature = hmac.new(API_SECRET.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()
    params['signature'] = signature
    headers = {'X-MBX-APIKEY': API_KEY}
    
    try:
        res = requests.get(BASE_URL + endpoint, headers=headers, params=params)
        if res.status_code == 200:
            return True
        else:
            print(f"❌ Connection Error (IP Issue?): {res.text}")
            return False
    except:
        return False

# কানেকশন টেস্ট
is_connected = check_balance()

if is_connected:
    print("✅ Binance Futures কানেকশন সফল! বট মার্কেট মনিটরিং শুরু করেছে...\n")
    while True:
        try:
            price = get_live_price()
            if price:
                current_time = time.strftime('%Y-%m-%d %H:%M:%S')
                print(f"[{current_time}] 🟢 {SYMBOL} লাইভ প্রাইস: {price} USDT | স্ক্যানিং চলছে...")
            time.sleep(10)
        except Exception as e:
            print(f"❌ Error: {e}")
            time.sleep(10)
else:
    print("\n⚠️ বট থেমে গেছে। বাইনান্সে গিয়ে Render-এর নতুন IP আপডেট করুন।")
