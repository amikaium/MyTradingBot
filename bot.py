import time
import requests
import hmac
import hashlib
from urllib.parse import urlencode

# আপনার Binance API Key এবং Secret Key
API_KEY = 'XAQj4j52q11U0cGBY1UTSta8SOAFAiBefCQeEpNVp0MqRgUElKkbqC87h1PFsbuc'
API_SECRET = 'Fplq9Q5MlHZ6CID31zNhUWZICiA8mumyrqu1dmdshOCZmOJFtXuimVMf2R2xVJVn'
BASE_URL = 'https://fapi.binance.com'
SYMBOL = 'XRPUSDT'

print("🚀 24/7 Smart Trading Bot Started on PythonAnywhere Server!\n")

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

# ইনফিনিট লুপ (যাতে বট কখনোই বন্ধ না হয়)
if is_connected:
    print("✅ Binance Futures কানেকশন সফল! বট মার্কেট মনিটরিং শুরু করেছে...\n")
    while True:
        try:
            price = get_live_price()
            if price:
                # বর্তমান সময় এবং প্রাইস প্রিন্ট করবে
                current_time = time.strftime('%Y-%m-%d %H:%M:%S')
                print(f"[{current_time}] 🟢 {SYMBOL} লাইভ প্রাইস: {price} USDT | স্ক্যানিং চলছে...")
                
                # (পরবর্তী ধাপে এখানে Sketchware থেকে সিগন্যাল রিসিভ করার কোড বসবে)
                
            # প্রতি ১০ সেকেন্ড পরপর মার্কেট চেক করবে
            time.sleep(10)
            
        except Exception as e:
            print(f"❌ Error: {e}")
            time.sleep(10)
else:
    print("\n⚠️ বট থেমে গেছে। আইপি (IP) ঠিক করুন।")
