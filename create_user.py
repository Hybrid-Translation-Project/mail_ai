import os
from cryptography.fernet import Fernet
from dotenv import load_dotenv, set_key
from app.database import users_col
# Buraya dikkat: Kendi güvenlik modülünü kullanıyoruz
from app.core.security import encrypt_password 

def create_admin_user():
    env_path = ".env"
    load_dotenv(env_path)
    
    # 1. Key yoksa üret ve .env'ye YAZ
    key = os.getenv("ENCRYPTION_KEY")
    if not key:
        new_key = Fernet.generate_key().decode()
        set_key(env_path, "ENCRYPTION_KEY", new_key)
        os.environ["ENCRYPTION_KEY"] = new_key
        key = new_key

    print("\n--- KULLANICI KURULUM SİHİRBAZI ---")
    email = input("Gmail Adresiniz: ").strip()
    password = input("Gmail Uygulama Şifreniz (16 hane): ").strip()
    
    if not email or not password:
        print("❌ Hata: Email veya şifre boş olamaz!")
        return

    # 2. Şifreyi şifrele
    encrypted_pwd = encrypt_password(password)
    
    # 3. .env DOSYASINI GÜNCELLE (Login ekranı buradan okuyor)
    # ui.py'nin beklediği isimlerle kaydediyoruz
    set_key(env_path, "EMAIL", email)
    set_key(env_path, "EMAIL_PASSWORD", encrypted_pwd)

    # 4. MONGODB'Yİ GÜNCELLE (Database buradan okuyor)
    user_data = {
        "email": email,
        "username": email, # Bazı yerlerde username diye geçer, ikisini de dolduralım
        "password": encrypted_pwd,
        "is_active": True
    }
    
    users_col.update_one(
        {"email": email}, 
        {"$set": user_data}, 
        upsert=True
    )
    
    print(f"\n✅ Başarılı! Bilgiler hem .env dosyasına hem de MongoDB'ye işlendi.")
    print("🚀 Şimdi 'python -m app.main' yazarak sistemi açabilirsin.")

if __name__ == "__main__":
    create_admin_user()