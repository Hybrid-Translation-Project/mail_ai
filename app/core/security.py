from cryptography.fernet import Fernet
import os
from dotenv import load_dotenv

# .env dosyasını yükle
# Bu satır çok kritiktir; create_user.py gibi harici script'ler 
# çalıştırıldığında .env içindeki anahtarı okuyabilmesini sağlar.
load_dotenv()

# Anahtarı .env dosyasından al
# EĞER .env İÇİNDE YOKSA GEÇİCİ ANAHTAR ÜRETİR (Bu sadece test içindir, veriler kaybolabilir!)
env_key = os.getenv("ENCRYPTION_KEY")

if not env_key:
    print(" UYARI: ENCRYPTION_KEY bulunamadı! Geçici anahtar kullanılıyor. Sunucu kapanırsa şifreler çözülemez.")
    key = Fernet.generate_key().decode()
else:
    key = env_key

cipher_suite = Fernet(key.encode())

def encrypt_password(password: str) -> str:
    """Şifreyi veritabanına kaydetmeden önce şifreler (Encryption)"""
    return cipher_suite.encrypt(password.encode()).decode()

def decrypt_password(encrypted_password: str) -> str:
    """Veritabanındaki şifreli veriyi tekrar okunabilir hale getirir (Decryption)"""
    return cipher_suite.decrypt(encrypted_password.encode()).decode()