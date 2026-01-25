from fastapi import APIRouter, UploadFile, File, HTTPException
import shutil
import os
import uuid
from app.services import voice_service

router = APIRouter()

@router.post("/api/voice-command")
async def voice_command_handler(file: UploadFile = File(...)):
    """
    Frontend'den gelen ses dosyasını işler ve sonucu döner.
    """
    # Her istek için benzersiz bir geçici dosya adı oluştur (Çakışmayı önler)
    unique_filename = f"temp_voice_{uuid.uuid4()}.wav"
    
    try:
        # 1. Gelen sesi diske kaydet
        with open(unique_filename, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # 2. Servise gönder (Transcribe)
        transcribed_text = voice_service.transcode_audio(unique_filename)
        print(f"🗣️ Algılanan Ses: {transcribed_text}")
        
        # 3. Analiz Et (Komut vs Yazı)
        result = voice_service.analyze_command(transcribed_text)
        
        return result

    except Exception as e:
        print(f"⚠️ Ses İşleme Hatası: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
        
    finally:
        # 4. Temizlik: Geçici dosyayı sil
        if os.path.exists(unique_filename):
            try:
                os.remove(unique_filename)
            except:
                pass