import os
import sys
import webbrowser
from fastapi import FastAPI
from contextlib import asynccontextmanager
from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv
from fastapi.staticfiles import StaticFiles
from datetime import datetime, timedelta

# --- DİZİN AYARLARI ---
# Bu dosyanın bulunduğu dizin (Proje Kök Dizini)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Eğer proje kök dizini sistem yolunda yoksa ekle (Import hatalarını önler)
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

# .env dosyası projenin ana dizininde (app klasörünün bir üstünde)
ROOT_DIR = os.path.dirname(BASE_DIR)
ENV_PATH = os.path.join(ROOT_DIR, ".env")

# .env dosyasını yükle
load_dotenv(ENV_PATH)

# UI ve YENİ VOICE (Ses) Rotalarını içeri alıyoruz
from app.routes import ui, voice 
from app.services.mail_listener import check_all_inboxes
from app.services.sent_mail_listener import check_all_sent

# --- Zamanlayıcı (Scheduler) ---
scheduler = BackgroundScheduler()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- SUNUCU BAŞLARKEN ---
    print("🚀 AI Mail Asistanı Sunucusu Başlatılıyor...", flush=True)
    
    # .env kontrolü ve Mail Dinleyici Başlatma
    if os.path.exists(ENV_PATH):
        # Startup'ı BLOKLAMAMAK için ilk taramaları arka plana atıyoruz.
        # Böylece login sayfası hemen açılır; taramalar 1-2 sn sonra başlar.
        print("🕑 Mail kontrolü arka planda başlatılıyor...", flush=True)

        # Periyodik kontrolü başlat (15 saniyede bir)
        scheduler.add_job(check_all_inboxes, 'interval', seconds=15)
        # Sent kutusu biraz daha seyrek taransın (Gmail UI reply'leri buradan yakalanır)
        scheduler.add_job(check_all_sent, 'interval', seconds=20)

        # İlk taramaları scheduler'a "hemen çalıştır" olarak ekle (arka plan thread'inde)
        scheduler.add_job(check_all_inboxes, 'date', run_date=datetime.now() + timedelta(seconds=1))
        scheduler.add_job(check_all_sent, 'date', run_date=datetime.now() + timedelta(seconds=2))

        scheduler.start()
        print("📥 Multi-Account Mail Dinleyicisi Aktif! (Periyot: 15 sn)", flush=True)
        print("📤 Sent Mail Dinleyicisi Aktif! (Periyot: 20 sn)", flush=True)
    else:
        print("⚠️ Yapılandırma bulunamadı. Web üzerinden kurulum bekleniyor (/setup)...", flush=True)
    
    # Uygulama başladığında tarayıcıyı otomatik aç
    webbrowser.open("http://127.0.0.1:8000/")
    
    yield
    
    # --- SUNUCU KAPANIRKEN ---
    if scheduler.running:
        scheduler.shutdown()
    print("🛑 Sistem Kapanıyor...", flush=True)

# FastAPI Uygulaması
app = FastAPI(
    title="AI Mail Assistant",
    lifespan=lifespan
)

# --- STATİK DOSYALAR (CSS/JS) ---
# app/static klasörünü "/static" adıyla dışarı açıyoruz
# Bu sayede voice.js ve writer.js dosyalarına erişebiliyoruz.
static_path = os.path.join(BASE_DIR, "app", "static")
if not os.path.exists(static_path):
    # Yedek kontrol (Eğer app klasörü içinde değilse direkt root'ta arar)
    static_path = os.path.join(BASE_DIR, "static")

app.mount("/static", StaticFiles(directory=static_path), name="static")

# --- ROTALARI SİSTEME DAHİL ET ---
app.include_router(ui.router)    # Arayüz Rotaları
app.include_router(voice.router) # 🎙️ YENİ: Sesli Komut Rotaları

@app.get("/health")
def health():
    return {
        "status": "OK", 
        "configured": os.path.exists(ENV_PATH),
        "voice_module": "Active" # Ses modülünün aktif olduğunu belirtelim
    }

if __name__ == "__main__":
    import uvicorn
    # host="0.0.0.0" yaparak ağdaki diğer cihazlardan da erişebilirsin
    uvicorn.run(app, host="127.0.0.1", port=8000)
    