import os
import sys
import webbrowser # Tarayıcıyı otomatik açmak için
from fastapi import FastAPI
from contextlib import asynccontextmanager
from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv
from fastapi.staticfiles import StaticFiles

# Bu satır, app/main.py içindeyken bir üst klasörü (ana dizini) Python yoluna ekler.
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
if root_dir not in sys.path:
    sys.path.append(root_dir)

# .env dosyasının yolunu ana dizin olarak belirliyoruz
ENV_PATH = os.path.join(root_dir, ".env")

# --- KURULUM KONTROLÜ ---
if not os.path.exists(ENV_PATH):
    print("Yapılandırma dosyası (.env) bulunamadı. Kurulum başlatılıyor...")
    try:
        import setup  # Artık ana dizindeki setup.py'yi bulabilir
        setup.run_setup()
    except Exception as e:
        print(f"Hata: Kurulum başlatılamadı! Detay: {e}")
        sys.exit(1)

# .env dosyasını ana dizinden yükle
load_dotenv(ENV_PATH)

# --- İTHALATLAR (load_dotenv'den sonra yapılmalı) ---
try:
    from app.routes import ui 
    from app.services.mail_listener import check_all_inboxes
except ImportError as e:
    print(f"Modül yükleme hatası: {e}")
    sys.exit(1)

# --- Zamanlayıcı (Scheduler) Kurulumu ---
scheduler = BackgroundScheduler()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- SUNUCU BAŞLARKEN ---
    print("AI Mail Asistanı Başlatılıyor...")
    
    # Mail kontrol görevini başlat
    scheduler.add_job(check_all_inboxes, 'interval', seconds=60)
    scheduler.start()
    print("Mail Dinleyicisi Aktif! (Periyot: 60 saniye)")
    
    # Uygulama başladığında tarayıcıda Dashboard'u otomatik aç
    webbrowser.open("http://127.0.0.1:8000/login")
    
    yield
    
    # --- SUNUCU KAPANIRKEN ---
    print("Sistem Kapanıyor...")
    scheduler.shutdown()

# FastAPI Uygulaması
app = FastAPI(
    title="AI Mail Assistant",
    lifespan=lifespan
)

# Statik Dosyalar (Yolu ana dizine göre düzelttik)
static_path = os.path.join(current_dir, "static")
app.mount("/static", StaticFiles(directory=static_path), name="static")

# UI Router'ını sisteme dahil ediyoruz
app.include_router(ui.router)

@app.get("/")
def health():
    return {
        "status": "OK", 
        "message": "AI Mail Asistanı Aktif",
        "env_loaded": os.path.exists(ENV_PATH)
    }

if __name__ == "__main__":
    import uvicorn
    # Uygulamayı ana dizinden çalıştırıyormuş gibi başlatıyoruz
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)