import os
import requests
import time
import threading
from flask import Flask, request
from urllib.parse import quote

app = Flask(__name__)

API_KEY = os.environ.get("CSFLOAT_API")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

ITEMS = ["Prisma Case", "Prisma 2 Case", "Danger Zone Case", "Fracture Case", "Recoil Case", "Dreams & Nightmares Case", "Revolution Case", "Snakebite Case", "Clutch Case", "Horizon Case", "Chroma 3 Case", "Kilowatt Case"]

# Daha gerçekçi bir tarayıcı kimliği
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.9',
    'Referer': 'https://steamcommunity.com/market/'
}

def send_msg(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"})

def get_steam_price(item_name):
    # Farklı bir Steam endpoint'i deniyoruz
    url = f"https://steamcommunity.com/market/priceoverview/?appid=730&currency=1&market_hash_name={quote(item_name)}"
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        if response.status_code == 429:
            print(f"!!! Steam Engeli (429) - IP Banlanmış !!!")
            return None
        data = response.json()
        if data.get('success') and data.get('lowest_price'):
            return float(data['lowest_price'].replace('$', '').replace(',', ''))
    except Exception as e:
        print(f"Steam Parse Hatası: {e}")
    return None

def scan_worker(mod):
    send_msg("🔍 Tarama başlatıldı, Steam kontrol ediliyor...")
    best = {"name": "Yok", "roi": -100}
    
    for item in ITEMS:
        s_price = get_steam_price(item)
        if s_price is None:
            time.sleep(3) # Engel varsa biraz daha uzun bekle
            continue
            
        time.sleep(2.5) # Güvenli aralık

        try:
            f_url = f"https://csfloat.com/api/v1/listings?market_hash_name={quote(item)}&limit=1&sort_by=lowest_price&type=buy_now"
            f_res = requests.get(f_url, headers={"Authorization": API_KEY}, timeout=10).json()
            listings = f_res if isinstance(f_res, list) else f_res.get('data', [])
            
            if listings:
                f_price = listings[0]['price'] / 100
                alis = f_price if mod == "1" else s_price
                satis = (s_price * 0.87) if mod == "1" else (f_price * 0.98)
                roi = round(((satis - alis) / alis) * 100, 2)
                
                if roi > best['roi']: best = {"name": item, "roi": roi}
                if roi >= 15: send_msg(f"✅ *{item}*\nROI: %{roi}")
        except: continue
    
    send_msg(f"ℹ️ Tarama bitti. En yüksek: {best['name']} (%{best['roi']})")

@app.route('/', methods=['POST', 'GET'])
def webhook():
    if request.method == 'POST':
        data = request.get_json()
        if data and "message" in data:
            text = data["message"].get("text", "")
            if "1 -" in text: threading.Thread(target=scan_worker, args=("1",)).start()
            elif "2 -" in text: threading.Thread(target=scan_worker, args=("2",)).start()
        return "OK", 200
    return "Bot is alive!", 200

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))
