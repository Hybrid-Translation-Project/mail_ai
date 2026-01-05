import os
import sys
import webbrowser
from fastapi import FastAPI
from contextlib import asynccontextmanager
from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv
from fastapi.staticfiles import StaticFiles

# --- DİZİN AYARLARI ---
# current_dir: /app klasörü
current_dir = os.path.dirname(os.path.abspath(__file__))
# root_dir: Projenin en ana dizini
root_dir = os.path.dirname(current_dir)

if root_dir not in sys.path:
    sys.path.append(root_dir)

ENV_PATH = os.path.join(root_dir, ".env")

# .env dosyasını ana dizinden yükle
load_dotenv(ENV_PATH)

# --- İTHALATLAR ---
from app.routes import ui 
from app.services.mail_listener import check_all_inboxes

# --- Zamanlayıcı (Scheduler) ---
scheduler = BackgroundScheduler()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- SUNUCU BAŞLARKEN ---
    print("🚀 AI Mail Asistanı Sunucusu Başlatılıyor...")
    
    # Sadece sistem kuruluysa mail dinleyiciyi başlat
    if os.path.exists(ENV_PATH):
        scheduler.add_job(check_all_inboxes, 'interval', seconds=60)
        scheduler.start()
        print("📥 Mail Dinleyicisi Aktif! (Periyot: 60 saniye)")
    else:
        print("⚠️ Yapılandırma bulunamadı. Web üzerinden kurulum bekleniyor...")
    
    # Uygulama başladığında tarayıcıyı aç
    webbrowser.open("http://127.0.0.1:8000/")
    
    yield
    
    # --- SUNUCU KAPANIRKEN ---
    if scheduler.running:
        scheduler.shutdown()
    print("🛑 Sistem Kapanıyor...")

# FastAPI Uygulaması
app = FastAPI(
    title="AI Mail Assistant",
    lifespan=lifespan
)

# --- STATİK DOSYALAR (DÜZELTİLDİ) ---
# Eğer static klasörün en dışarıdaysa (app klasörü dışında):
static_path = os.path.join(root_dir, "static")

# Eğer static klasörün app/ klasörü içindeyse (yukarıdaki çalışmazsa):
if not os.path.exists(static_path):
    static_path = os.path.join(current_dir, "static")

app.mount("/static", StaticFiles(directory=static_path), name="static")

# Rotaları dahil et
app.include_router(ui.router)

@app.get("/health")
def health():
    return {
        "status": "OK", 
        "configured": os.path.exists(ENV_PATH)
    }

if __name__ == "__main__":
    import uvicorn
    # uvicorn.run("app.main:app"...) yerine direkt app nesnesini veriyoruz
    uvicorn.run(app, host="127.0.0.1", port=8000)