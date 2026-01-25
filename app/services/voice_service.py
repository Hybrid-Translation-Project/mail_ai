import os
import re
from faster_whisper import WhisperModel

# --- AYARLAR ---
MODEL_SIZE = "medium"  # 'small', 'medium', 'large-v3' (Bilgisayarın gücüne göre seç)
DEVICE = "cpu"         # GPU varsa "cuda", yoksa "cpu"
COMPUTE_TYPE = "int8"  # RAM tasarrufu için int8

model = None

def get_model():
    """
    Modeli belleğe bir kere yükler (Singleton Pattern).
    Her istekte tekrar yüklememesi için global değişken kullanıyoruz.
    """
    global model
    if model is None:
        print(f"🧠 Whisper Modeli ({MODEL_SIZE}) Yükleniyor... Lütfen bekleyin.")
        try:
            model = WhisperModel(MODEL_SIZE, device=DEVICE, compute_type=COMPUTE_TYPE)
            print("✅ Whisper Modeli Başarıyla Yüklendi!")
        except Exception as e:
            print(f"❌ Model yüklenirken hata: {e}")
            raise e
    return model

def transcode_audio(file_path):
    """
    Verilen ses dosyasını metne çevirir.
    """
    whisper = get_model()
    
    # Türkçe dilinde, beam_size=5 ile (daha kaliteli ama yavaş) çeviri yap
    segments, info = whisper.transcribe(file_path, language="tr", beam_size=5)
    
    full_text = ""
    for segment in segments:
        full_text += segment.text + " "
        
    return full_text.strip()

def analyze_command(text):
    """
    Metni analiz eder: Komut mu yoksa normal yazı mı?
    """
    text_lower = text.lower().strip()
    
    # --- KOMUT LİSTESİ ---
    
    # 1. GÖNDERME
    if re.search(r'\b(maili|bunu)?\s*gönder\b', text_lower):
        return {"type": "command", "action": "send_mail", "content": text}
    
    # 2. ONAYLAMA (Modal açıkken)
    if re.search(r'\b(onayla|evet gönder|tamam gönder)\b', text_lower):
        return {"type": "command", "action": "confirm_send", "content": text}

    # 3. İPTAL ETME
    if re.search(r'\b(iptal|vazgeç|kapat)\b', text_lower):
        return {"type": "command", "action": "cancel_send", "content": text}
        
    # 4. OLUŞTURMA (AI Prompt sonrası)
    if re.search(r'\b(oluştur|yaz|hazırla|üret)\b', text_lower):
        # Eğer çok kısa bir emir cümlesiyse komut say (Uzunsa promptun parçası olabilir)
        if len(text.split()) < 5:
            return {"type": "command", "action": "generate_ai", "content": text}

    # 5. TEMİZLEME
    if re.search(r'\b(temizle|sil|hepsini sil|içeriği sil|taslağı sil)\b', text_lower):
        return {"type": "command", "action": "clear_input", "content": text}

    # --- HİÇBİRİ DEĞİLSE ---
    return {"type": "text", "action": "write", "content": text}