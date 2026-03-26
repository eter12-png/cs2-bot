import os
import requests
import time
import threading
from flask import Flask, request
from urllib.parse import quote

app = Flask(__name__)

# --- AYARLAR (Render Environment kısmından okunur) ---
API_KEY = os.environ.get("CSFLOAT_API")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

ITEMS = [
    "Prisma Case", "Prisma 2 Case", "Danger Zone Case", "Fracture Case", 
    "Recoil Case", "Dreams & Nightmares Case", "Revolution Case", 
    "Snakebite Case", "Clutch Case", "Horizon Case", "Chroma 3 Case",
    "Kilowatt Case"
]

# Steam'e kendimizi gerçek bir tarayıcı gibi tanıtmak için:
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

def send_msg(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"}, timeout=10)
    except:
        pass

def scan_worker(mod):
    mod_text = "CSFloat -> Steam" if mod == "1" else "Steam -> CSFloat"
    send_msg(f"🔍 *{mod_text}* taraması başladı...")
    
    best_item = {"name": "Veri Yok", "roi": -100, "alis": 0, "satis": 0}
    profitable_list = []

    for item in ITEMS:
        try:
            # 1. STEAM VERİSİ
            s_url = f"https://steamcommunity.com/market/priceoverview/?appid=730&currency=1&market_hash_name={quote(item)}"
            s_res = requests.get(s_url, headers=HEADERS, timeout=15)
            
            if s_res.status_code != 200:
                print(f"Steam Hatası ({item}): {s_res.status_code}")
                continue
                
            s_data = s_res.json()
            if not s_data.get('lowest_price'): continue
            s_price = float(s_data['lowest_price'].replace('$', '').replace(',', ''))
            
            time.sleep(2) # Steam engeli yememek için süreyi artırdık

            # 2. CSFLOAT VERİSİ
            f_url = f"https://csfloat.com/api/v1/listings?market_hash_name={quote(item)}&limit=1&sort_by=lowest_price&type=buy_now"
            f_res = requests.get(f_url, headers={"Authorization": API_KEY}, timeout=15)
            
            if f_res.status_code != 200:
                print(f"CSFloat Hatası ({item}): {f_res.status_code}")
                continue
                
            f_data = f_res.json()
            listings = f_data if isinstance(f_data, list) else f_data.get('data', [])
            
            if not listings: continue
            f_price = listings[0]['price'] / 100
            
            # 3. HESAPLAMA
            if mod == "1":
                alis, satis = f_price, round(s_price * 0.87, 2)
            else:
                alis, satis = s_price, round(f_price * 0.98, 2)

            roi = round(((satis - alis) / alis) * 100, 2)
            
            if roi > best_item["roi"]:
                best_item = {"name": item, "roi": roi, "alis": alis, "satis": satis}
            
            if roi >= 15:
                profitable_list.append(f"✅ *{item}*\nROI: %{roi} | Al: ${alis} | Sat: ${satis}")

        except Exception as e:
            print(f"Detaylı Hata ({item}): {str(e)}")
            continue

    # SONUÇ GÖNDERME
    if profitable_list:
        report = "🚀 *FIRSATLAR BULUNDU!*\n\n" + "\n\n".join(profitable_list)
        send_msg(report)
    else:
        info = (f"ℹ️ *%15* kâr bulunamadı.\n\n"
                f"💡 *En iyisi:* {best_item['name']}\n"
                f"📈 ROI: %{best_item['roi']}\n"
                f"💰 Al: ${best_item['alis']} | Sat: ${best_item['satis']}")
        send_msg(info)

@app.route('/', methods=['POST', 'GET'])
def webhook():
    if request.method == 'POST':
        data = request.get_json()
        if data and "message" in data:
            text = data["message"].get("text", "")
            
            if "/start" in text:
                send_msg("🎮 *CS2 Arbitraj Botu Aktif!*\n\nButonları kullanarak tarama yapabilirsin.")
            elif "1 -" in text:
                # Arka planda çalıştır (Thread)
                threading.Thread(target=scan_worker, args=("1",)).start()
            elif "2 -" in text:
                threading.Thread(target=scan_worker, args=("2",)).start()
                
        return "OK", 200
    return "Bot is alive!", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
