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

def send_msg(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"})

def get_steam_price_v2(item_name):
    # Alternatif bir Steam fiyat sağlayıcısı deniyoruz
    # Steam'in ana API'si yerine fiyat geçmişi endpoint'ini veya aracı bir siteyi simüle ediyoruz
    try:
        url = f"https://steamcommunity.com/market/priceoverview/?appid=730&currency=1&market_hash_name={quote(item_name)}"
        # Daha agresif bir Header (Kimlik)
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
            'Accept': 'application/json'
        }
        r = requests.get(url, headers=headers, timeout=10)
        
        # Eğer 429 alırsak (Çok fazla istek), biraz bekleyip tekrar deneme mantığı
        if r.status_code == 429:
            print(f"!!! Steam IP Banı Var (429) !!!")
            return None
            
        data = r.json()
        if data.get('success') and 'lowest_price' in data:
            return float(data['lowest_price'].replace('$', '').replace(',', ''))
    except:
        return None
    return None

def scan_worker(mod):
    send_msg("🔍 *Render üzerinden tarama başlatıldı...*")
    best = {"name": "Yok", "roi": -100}
    
    for item in ITEMS:
        s_price = get_steam_price_v2(item)
        
        if s_price is None:
            print(f"Hata: {item} Steam'den çekilemedi.")
            time.sleep(3) # Ban riskine karşı uzun bekleme
            continue
            
        time.sleep(2) # Güvenli aralık

        try:
            f_url = f"https://csfloat.com/api/v1/listings?market_hash_name={quote(item)}&limit=1&sort_by=lowest_price&type=buy_now"
            f_res = requests.get(f_url, headers={"Authorization": API_KEY}, timeout=10).json()
            listings = f_res if isinstance(f_res, list) else f_res.get('data', [])
            
            if listings:
                f_price = listings[0]['price'] / 100
                # Arbitraj Hesabı
                alis = f_price if mod == "1" else s_price
                satis = (s_price * 0.87) if mod == "1" else (f_price * 0.98)
                roi = round(((satis - alis) / alis) * 100, 2)
                
                if roi > best['roi']: best = {"name": item, "roi": roi}
                if roi >= 15: send_msg(f"✅ *{item}*\nROI: %{roi} | Al: ${alis}")
        except: continue
    
    send_msg(f"ℹ️ Tarama bitti.\nEn iyi: {best['name']} (%{best['roi']})")

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
