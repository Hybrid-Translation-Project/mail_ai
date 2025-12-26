import os
from cryptography.fernet import Fernet
from dotenv import load_dotenv
from app.database import users_col
from app.core.security import encrypt_password

def setup_environment():
    """
    .env dosyasını ve Encryption Key'i kontrol eder.
    Eksikse otomatik oluşturur.
    """
    env_path = ".env"
    
    # 1. .env dosyası yoksa oluştur
    if not os.path.exists(env_path):
        print("📄 .env dosyası bulunamadı, oluşturuluyor...")
        with open(env_path, "w", encoding="utf-8") as f:
            f.write("# Mail AI Asistanı Ayarları\n")
    
    # Mevcut ayarları yükle
    load_dotenv()
    
    # 2. Key kontrolü yap
    key = os.getenv("ENCRYPTION_KEY")
    
    if not key:
        print(" Şifreleme anahtarı eksik! Yeni bir tane üretiliyor...")
        # Yeni anahtar üret
        new_key = Fernet.generate_key().decode()
        
        # Dosyaya ekle
        with open(env_path, "a", encoding="utf-8") as f:
            f.write(f"\nENCRYPTION_KEY={new_key}\n")
        
        # Çalışan sisteme de yükle (Reload etmeye gerek kalmasın)
        os.environ["ENCRYPTION_KEY"] = new_key
        print(f" Yeni anahtar .env dosyasına kaydedildi.")
    else:
        print("Şifreleme anahtarı zaten mevcut, devam ediliyor.")

def create_admin_user():
    setup_environment()
    
    print("\n--- KULLANICI KURULUM SİHİRBAZI ---")
    email = input("Gmail Adresiniz: ").strip()
    password = input("Gmail Uygulama Şifreniz (16 hane): ").strip()
    
    if not email or not password:
        print(" Hata: Email veya şifre boş olamaz!")
        return

    # Şifreyi güvenli hale getir
    encrypted_pwd = encrypt_password(password)
    
    user_data = {
        "email": email,
        "password": encrypted_pwd, # Şifrelenmiş hali
        "is_active": True
    }
    
    # Veritabanına kaydet (Varsa güncelle, yoksa ekle)
    users_col.update_one(
        {"email": email}, 
        {"$set": user_data}, 
        upsert=True
    )
    
    print(f"\n Tebrikler! {email} kullanıcısı başarıyla tanımlandı.")
    print(" Artık 'baslat.bat' dosyasına tıklayarak sistemi açabilirsiniz.")

if __name__ == "__main__":
    create_admin_user()