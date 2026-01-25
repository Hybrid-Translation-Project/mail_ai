import os
import sys
import time

try:
    from faster_whisper import WhisperModel
except ImportError:
    print("❌ HATA: Gerekli kütüphaneler yüklü değil!")
    print("Lütfen önce terminalde 'pip install -r requirements.txt' komutunu çalıştırın.")
    sys.exit(1)

# --- AYARLAR ---
# Buradaki model boyutu, voice_service.py içindekiyle AYNI olmalı.
# Seçenekler: "tiny", "base", "small", "medium", "large-v3"
MODEL_SIZE = "medium" 

def download_voice_model():
    print("\n" + "="*60)
    print(f"⬇️  AI SES MODELİ İNDİRİCİSİ ({MODEL_SIZE})")
    print("="*60)
    print("📡 HuggingFace sunucularına bağlanılıyor...")
    print(f"📦 '{MODEL_SIZE}' modeli bilgisayarınıza indiriliyor (Yaklaşık 1.5 GB)...")
    print("☕ Bu işlem internet hızınıza göre 2-10 dakika sürebilir.")
    print("⚠️  LÜTFEN PROGRAMI KAPATMAYIN!")
    print("-" * 60)

    start_time = time.time()

    try:
        # Modeli indirir ve varsayılan Cache klasörüne kaydeder.
        # voice_service.py çalıştığında direkt buradan okuyacaktır.
        model = WhisperModel(MODEL_SIZE, device="cpu", compute_type="int8")
        
        elapsed_time = time.time() - start_time
        print("\n" + "="*60)
        print(f"✅ İŞLEM BAŞARIYLA TAMAMLANDI! ({int(elapsed_time)} saniye sürdü)")
        print("📂 Model dosyaları bilgisayarınıza kaydedildi.")
        print("🚀 Artık 'run.py' dosyasını çalıştırıp sistemi ışık hızında açabilirsin.")
        print("="*60 + "\n")

    except Exception as e:
        print("\n❌ İNDİRME SIRASINDA HATA OLUŞTU:")
        print(f"Hata Detayı: {e}")
        print("Lütfen internet bağlantınızı kontrol edip tekrar deneyin.")

if __name__ == "__main__":
    download_voice_model()