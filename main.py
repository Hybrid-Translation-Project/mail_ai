import uvicorn
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
import threading
import time
import os
from dotenv import load_dotenv

# --- BİZİM YAZDIĞIMIZ MODÜLLER ---
# 1. Arayüz (UI) rotalarını alıyoruz
from app.routes import ui
# 2. Mail dinleme servisini alıyoruz
from app.services.mail_listener import check_all_inboxes

# .env dosyasını yükle (Şifreler için)
load_dotenv()

# Uygulamayı Yarat
app = FastAPI(title="Mail Asistanı AI", version="2.0")

# 1. Statik Dosyalar (CSS, JS, Resimler)
# app/static klasörünü "/static" adresine bağlıyoruz
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# 2. HTML Şablonları
templates = Jinja2Templates(directory="app/templates")

# 3. Router'ları (Sayfaları) Dahil Et
app.include_router(ui.router)

# --- ARKA PLAN İŞLEMLERİ (MAIL DİNLEME) ---
def background_mail_listener():
    """
    Bu fonksiyon arka planda sürekli çalışır.
    Her 60 saniyede bir mailleri, faturaları, PDF'leri kontrol eder.
    """
    print("✅ Mail Dinleme Servisi Başladı (Arka Plan)")
    while True:
        try:
            # Burası senin mail_listener.py dosyanı çalıştırır
            check_all_inboxes()
        except Exception as e:
            print(f"❌ Mail döngüsünde hata: {e}")
        
        # 1 dakika bekle, sonra tekrar bak
        time.sleep(60)

@app.on_event("startup")
async def startup_event():
    """Uygulama 'Start' verildiği an burası çalışır"""
    print("🚀 Sistem Ayağa Kalkıyor...")
    
    # Mail dinleyiciyi ayrı bir "Thread" (iş parçacığı) olarak başlat
    # Böylece site donmaz, arkada mailler akar.
    listener_thread = threading.Thread(target=background_mail_listener, daemon=True)
    listener_thread.start()

# --- ANA SAYFA ---
@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Siteye girince direkt Dashboard açılsın"""
    return templates.TemplateResponse("dashboard.html", {"request": request})

# --- BAŞLATMA KOMUTU ---
if __name__ == "__main__":
    # 127.0.0.1:8000 adresinde yayına başla
    print("🌍 Tarayıcıda şu adrese git: http://127.0.0.1:8000")
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)