from cryptography.fernet import Fernet
import os
import hashlib
from dotenv import load_dotenv

def get_cipher():
    """Dosya yolunu tam vererek .env'yi her seferinde doğru yerden okur."""
    # Proje kök dizinini (mail_ai) buluyoruz
    # Bu dosya app/core/ içinde olduğu için 3 üst dizine çıkıyoruz
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    env_path = os.path.join(base_dir, ".env")
    
    # .env dosyasını tam yoluyla zorla yüklüyoruz
    load_dotenv(env_path, override=True)
    
    env_key = os.getenv("ENCRYPTION_KEY")
    
    if not env_key:
        return None
    
    try:
        return Fernet(env_key.encode())
    except Exception as e:
        print(f"🚨 Anahtar formatı hatalı: {e}")
        return None

# --- GMAIL UYGULAMA ŞİFRESİ İŞLEMLERİ ---

def encrypt_password(password: str) -> str:
    """Gmail Uygulama şifresini güncel anahtarla şifreler."""
    cipher = get_cipher()
    if not cipher:
        # Eğer kurulum anındaysak cipher None döner
        # Bu durumda ui.py içindeki run_setup hata fırlatabilir
        raise ValueError("ENCRYPTION_KEY bulunamadı! Lütfen önce anahtar üretin.")
    
    return cipher.encrypt(password.encode()).decode()

def decrypt_password(encrypted_password: str) -> str:
    """Veritabanındaki şifreyi güncel anahtarla çözer."""
    cipher = get_cipher()
    if not cipher:
        raise ValueError("ENCRYPTION_KEY bulunamadı! Lütfen sistemi kurun.")
    
    try:
        return cipher.decrypt(encrypted_password.encode()).decode()
    except Exception as e:
        # Hata detayını terminalde görelim
        raise ValueError(f"Şifre çözülemedi (Anahtar uyuşmazlığı): {str(e)}")

# --- PANEL GİRİŞ ŞİFRESİ İŞLEMLERİ ---
def hash_master_password(password: str) -> str:
    if not password: return ""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_master_password(plain_password: str, hashed_password: str) -> bool:
    return hash_master_password(plain_password) == hashed_password