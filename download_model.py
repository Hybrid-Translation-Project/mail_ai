import os
import sys
import time

# Gerekli kütüphanelerin kontrolü
try:
    from faster_whisper import WhisperModel
    from sentence_transformers import SentenceTransformer
except ImportError as e:
    print("❌ HATA: Gerekli kütüphaneler yüklü değil!")
    print(f"Eksik kütüphane: {e.name}")
    print("Lütfen önce terminalde 'pip install -r requirements.txt' komutunu çalıştırın.")
    sys.exit(1)

# --- AYARLAR ---
# 1. Ses Modeli Ayarları
WHISPER_MODEL_SIZE = "medium"

# 2. Arama Modeli Ayarları (Semantik Arama)
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"

# 3. Modellerin Kaydedileceği Ana Klasör
MODELS_DIR = "models"
EMBEDDING_PATH = os.path.join(MODELS_DIR, "embedding_model")

# Ana klasör yoksa oluştur
if not os.path.exists(MODELS_DIR):
    os.makedirs(MODELS_DIR)

def download_voice_model():
    print("\n" + "="*60)
    print(f"🎤 ADIM 1: SES MODELİ İNDİRİLİYOR ({WHISPER_MODEL_SIZE})")
    print("="*60)
    print("📡 HuggingFace sunucularına bağlanılıyor...")
    print(f"📦 '{WHISPER_MODEL_SIZE}' modeli indiriliyor (Yaklaşık 1.5 GB)...")
    print("☕ Bu işlem internet hızınıza göre biraz sürebilir.")
    
    start_time = time.time()

    try:
        # Modeli indirir. (Faster-whisper varsayılan cache mekanizmasını kullanır)
        # Proje çalıştığında otomatik olarak cache'den okuyacaktır.
        model = WhisperModel(WHISPER_MODEL_SIZE, device="cpu", compute_type="int8")
        
        elapsed_time = time.time() - start_time
        print(f"✅ SES MODELİ HAZIR! ({int(elapsed_time)} saniye sürdü)")

    except Exception as e:
        print("\n❌ SES MODELİ İNDİRİLİRKEN HATA OLUŞTU:")
        print(f"Hata Detayı: {e}")

def download_embedding_model():
    print("\n" + "="*60)
    print(f"🧠 ADIM 2: SEMANTİK ARAMA MODELİ İNDİRİLİYOR")
    print(f"Model: {EMBEDDING_MODEL_NAME}")
    print("="*60)

    start_time = time.time()

    try:
        # Eğer model daha önce indirilmişse tekrar indirme
        if os.path.exists(EMBEDDING_PATH) and len(os.listdir(EMBEDDING_PATH)) > 0:
            print("✅ Arama modeli zaten 'models/embedding_model' klasöründe mevcut.")
            print("⏩ İndirme işlemi atlanıyor.")
        else:
            print(f"📦 Model '{EMBEDDING_PATH}' klasörüne indiriliyor (Yaklaşık 80 MB)...")
            # Modeli indir ve proje içine kaydet
            model = SentenceTransformer(EMBEDDING_MODEL_NAME)
            model.save(EMBEDDING_PATH)
            
            elapsed_time = time.time() - start_time
            print(f"✅ ARAMA MODELİ İNDİRİLDİ VE KAYDEDİLDİ! ({int(elapsed_time)} saniye sürdü)")

    except Exception as e:
        print("\n❌ ARAMA MODELİ İNDİRİLİRKEN HATA OLUŞTU:")
        print(f"Hata Detayı: {e}")

if __name__ == "__main__":
    print("🚀 MODEL KURULUM SİHİRBAZI BAŞLATILIYOR...\n")
    
    download_voice_model()
    download_embedding_model()
    
    print("\n" + "="*60)
    print("🎉 TÜM İŞLEMLER TAMAMLANDI!")
    print("📂 Modeller hazır, artık 'application_run.py' dosyasını çalıştırabilirsin.")
    print("="*60 + "\n")