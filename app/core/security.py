from cryptography.fernet import Fernet
import os
from dotenv import load_dotenv

# .env dosyasını yükle
load_dotenv()

# Anahtarı .env dosyasından al
env_key = os.getenv("ENCRYPTION_KEY")

if not env_key:
    # UYARI: Üretim ortamında buranın boş gelmemesi gerekir.
    # setup.py zaten bunu oluşturuyor olmalı.
    print("⚠️ UYARI: ENCRYPTION_KEY bulunamadı! Geçici anahtar kullanılıyor.")
    key = Fernet.generate_key().decode()
else:
    key = env_key

cipher_suite = Fernet(key.encode())

# --- GMAIL UYGULAMA ŞİFRESİ İŞLEMLERİ (FERNET) ---

def encrypt_password(password: str) -> str:
    """Gmail Uygulama şifresini veritabanına kaydetmeden önce şifreler."""
    return cipher_suite.encrypt(password.encode()).decode()

def decrypt_password(encrypted_password: str) -> str:
    """Veritabanındaki şifreli Gmail şifresini tekrar okunabilir hale getirir."""
    return cipher_suite.decrypt(encrypted_password.encode()).decode()


# --- PANEL GİRİŞ ŞİFRESİ KONTROLÜ (YENİ) ---

def verify_master_password(plain_password: str, stored_password: str) -> bool:
    """
    Kullanıcının giriş ekranında yazdığı şifre ile 
    kayıtlı olan (setup'ta belirlenen) şifreyi karşılaştırır.
    """
    if not plain_password or not stored_password:
        return False
    return plain_password == stored_password