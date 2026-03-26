import os
import requests
import time
from flask import Flask, request
from urllib.parse import quote

app = Flask(__name__)

# --- GÜVENLİ AYARLAR (Render Panelinden Çekilecek) ---
# Render Panelinde: Environment -> Add Variable kısmından bunları eklemeyi unutma!
API_KEY = os.environ.get("CSFLOAT_API")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

ITEMS = [
    "Prisma Case", "Prisma 2 Case", "Danger Zone Case", "Fracture Case", 
    "Recoil Case", "Dreams & Nightmares Case", "Revolution Case", 
    "Snakebite Case", "Clutch Case", "Horizon Case", "Chroma 3 Case",
    "Kilowatt Case"
]

def send_msg(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"})
    except Exception as e:
        print(f"Telegram Hatası: {e}")

def scan_arbitrage(mod):
    mod_text = "CSFloat -> Steam" if mod == "1" else "Steam -> CSFloat"
    send_msg(f"🔍 *{mod_text}* taraması başladı, lütfen bekleyin...")
    
    best_item = {"name": "Veri Yok", "roi": -100, "alis": 0, "satis": 0}
    profitable_list = []

    for item in ITEMS:
        try:
            # 1. Steam Verisi
            s_url = f"https://steamcommunity.com/market/priceoverview/?appid=730&currency=1&market_hash_name={quote(item)}"
            s_res = requests.get(s_url, timeout=10).json()
            if not s_res.get('success'): continue
            s_price = float(s_res.get('lowest_price', '$0').replace('$', '').replace(',', ''))
            
            # Steam Ban Yememek İçin Bekleme
            time.sleep(1.5)

            # 2. CSFloat Verisi
            f_url = f"https://csfloat.com/api/v1/listings?market_hash_name={quote(item)}&limit=5&sort_by=lowest_price&type=buy_now"
            f_res = requests.get(f_url, headers={"Authorization": API_KEY}, timeout=10).json()
            listings = f_res if isinstance(f_res, list) else f_res.get('data', [])
            
            if not listings: continue
            f_price = listings[0]['price'] / 100
            
            # Hesaplama
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
            print(f"Hata ({item}): {e}")
            continue

    # Final Raporu
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
        data = request.json
        if "message" in data and "text" in data["message"]:
            text = data["message"]["text"]
            if "1 -" in text:
                scan_arbitrage("1")
            elif "2 -" in text:
                scan_arbitrage("2")
            elif "/start" in text:
                send_msg("🎮 *CS2 Arbitraj Botu Hazır!*\nButonları kullanarak tarama yapabilirsin.")
        return "OK", 200
    return "Bot is alive!", 200

if __name__ == "__main__":
    # Render portu otomatik ayarlar
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
