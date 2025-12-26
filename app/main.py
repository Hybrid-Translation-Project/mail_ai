import os
import sys
from fastapi import FastAPI
from contextlib import asynccontextmanager
from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv
from fastapi.staticfiles import StaticFiles

# --- KURULUM KONTROLÜ ---
# .env dosyası yoksa kurulum modülünü çalıştır
if not os.path.exists(".env"):
    print("Yapılandırma dosyası (.env) bulunamadı. Kurulum başlatılıyor...")
    try:
        import setup  # setup.py dosyanızın aynı dizinde olduğundan emin olun
        setup.run_setup()
    except ImportError:
        print(" Hata: 'setup.py' dosyası bulunamadı! Lütfen dosyayı kontrol edin.")
        sys.exit(1) # Kurulum yapılamazsa uygulamayı durdur

# .env oluşturulduktan sonra yükle
load_dotenv()

# Router'lar ve Servisler (Yüklemeden sonra import etmek bazen daha güvenlidir)
from app.routes import ui 
from app.services.mail_listener import check_all_inboxes

# --- Zamanlayıcı (Scheduler) Kurulumu ---
scheduler = BackgroundScheduler()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- SUNUCU BAŞLARKEN ---
    print("🚀 Sistem Başlatılıyor...")
    
    # Her 60 saniyede bir tüm kullanıcıların maillerini kontrol et
    # Not: Fonksiyonun içinde env verilerini okuduğunuzdan emin olun
    scheduler.add_job(check_all_inboxes, 'interval', seconds=60)
    
    scheduler.start()
    print("👂 Mail Dinleyicisi Aktif! (Her 60 saniyede bir kontrol eder)")
    
    yield
    
    # --- SUNUCU KAPANIRKEN ---
    print(" Sistem Kapanıyor...")
    scheduler.shutdown()

# FastAPI uygulamasını başlatıyoruz
app = FastAPI(lifespan=lifespan)

# Statik dosyalar (CSS, JS, Resimler)
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# UI Router'ını sisteme dahil ediyoruz
app.include_router(ui.router)

@app.get("/")
def health():
    """
    Sistem sağlık kontrolü
    """
    return {
        "status": "OK", 
        "mode": "Standalone Python", 
        "message": "AI Mail Asistanı Arka Planda Çalışıyor",
        "env_status": "Loaded" if os.path.exists(".env") else "Missing"
    }