import os
import requests
import json
from dotenv import load_dotenv


# .env dosyasını yükle 
load_dotenv()

# Önce .env'e bakar, bulamazsa ikinci parametreyi (varsayılanı) kullanır.
# Bu sayede "URL is not set" hatası almazsın.
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2") # Veya qwen2.5

def ask_llama(prompt: str) -> str:
    """
    Ollama LLM'e prompt gönderir.
    SADECE model cevabını string olarak döndürür.
    """

    
    # Prompt boşsa veya çok kısaysa boş dön
    if not prompt or len(prompt.strip()) < 2:
        return ""

    # Base URL temizleme (Sonunda / varsa siler, /api/generate varsa siler)
    # Amacımız temiz bir "http://localhost:11434" elde etmek
    base_url = OLLAMA_BASE_URL.rstrip("/")
    if base_url.endswith("/api/generate"):
        base_url = base_url.replace("/api/generate", "")

    # İstek atılacak tam adres
    url = f"{base_url}/api/generate"


    try:
        response = requests.post(
            url,
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                # Temperature 0: Modelin halüsinasyon görmesini engeller, mantıklı cevap verir.
                "options": {
                    "temperature": 0.0
                }
            },
            timeout=60  # 60 saniye içinde cevap gelmezse iptal et
        )
    except requests.RequestException as e:
        print(f" Ollama Bağlantı Hatası: {e}")
        # Bağlantı hatasında boş dön ki sistem çökmesin
        return ""
  
    # HTTP Hatası varsa (Örn: 404, 500)
    if response.status_code != 200:
        print(f"Ollama HTTP Hatası: {response.status_code}")
        print("Detay:", response.text)
        return ""

    # JSON Parse
    try:
        data = response.json()
    except json.JSONDecodeError:
        print("Ollama cevabı JSON formatında değil.")
        return ""

    # Cevabı al
    result = data.get("response", "")
    
    if not isinstance(result, str):
        return ""

    return result.strip()