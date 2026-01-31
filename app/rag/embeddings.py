import os

# Modelin diskteki yolu (download_model.py ile buraya indirdik)
MODEL_PATH = os.path.join("models", "embedding_model")

# Modeli bellekte tutmak için global değişken (Singleton Pattern)
# Böylece her seferinde tekrar tekrar yükleyip zaman kaybetmeyiz.
_embedding_model = None

def get_model():
    """
    Modeli yükler ve döner. Eğer zaten yüklüyse hafızadakini kullanır.
    """
    global _embedding_model
    
    # Varsayılan: embeddings AÇIK.
    # Login gecikmesini önlemek için model import'u ve yükleme lazy (ilk kullanımda) yapılır.
    # İstersen kapatmak için: .env içine EMBEDDINGS_ENABLED=0
    if os.getenv("EMBEDDINGS_ENABLED", "1").strip() != "1":
        raise RuntimeError("Embeddings disabled (set EMBEDDINGS_ENABLED=1 to enable).")

    if _embedding_model is None:
        if not os.path.exists(MODEL_PATH):
            raise FileNotFoundError(
                f"❌ Model bulunamadı: {MODEL_PATH}\n"
                "Lütfen önce ana dizindeki 'download_model.py' dosyasını çalıştırın."
            )
        
        print(f"🧠 Embedding modeli yükleniyor... ({MODEL_PATH})")
        # Local modeli yükle
        from sentence_transformers import SentenceTransformer  # lazy import (startup hızlansın)
        _embedding_model = SentenceTransformer(MODEL_PATH)
        print("✅ Model belleğe yüklendi.")
    
    return _embedding_model

def get_embedding(text: str) -> list[float]:
    """
    Verilen metni vektöre (sayı listesine) çevirir.
    MongoDB Vector Search için bu format gereklidir.
    """
    if not text or not isinstance(text, str):
        return []

    # Embeddings kapalıysa veya model yüklenemiyorsa sessizce boş dön (fallback)
    try:
        model = get_model()
    except Exception:
        return []
    
    # Metni temizle (Yeni satırları boşlukla değiştir - önerilen pratik)
    text = text.replace("\n", " ")
    
    # Vektörü oluştur
    # normalize_embeddings=True -> Cosine Similarity için vektörleri normalize eder (0-1 arası denge)
    embedding = model.encode(text, normalize_embeddings=True)
    
    # Numpy array'i Python listesine çevirip döndür (MongoDB list ister)
    return embedding.tolist()

# Test Bloğu (Dosya doğrudan çalıştırılırsa test yapar)
if __name__ == "__main__":
    try:
        test_text = "Yapay zeka ile mail analizi"
        vector = get_embedding(test_text)
        print(f"Test Metni: {test_text}")
        print(f"Vektör Boyutu: {len(vector)}") # 384 olmalı
        print(f"Örnek Veri: {vector[:5]}...")
    except Exception as e:
        print(f"Hata: {e}")