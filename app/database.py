# app/database.py
# MongoDB istemcisi
from pymongo import MongoClient
import sys

# Bağlantı bilgilerini config dosyasından alıyoruz
from app.config import MONGO_URI, DB_NAME

try:
    # MongoDB’ye bağlantı açılır
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    
    # Bağlantıyı test et (Hata varsa hemen yakalayalım)
    client.server_info()
    
    # Kullanılacak database seçilir
    db = client[DB_NAME]

    # --- KOLEKSİYONLAR ---
    
    # Gelen maillerin tutulduğu collection
    mails_col = db.mails

    # Kişi profillerinin tutulacağı collection (Şirket Branch yapısının temeli)
    contacts_col = db.contacts

    # Panel giriş yetkisi olan ana kullanıcıların tutulacağı collection
    users_col = db.users

    # Bağlı olan mail hesaplarının (Gmail vb.) tutulacağı collection (YENİ EKLENDİ)
    # Bu koleksiyon; İş, Kişisel vb. tüm ek hesapları tutacak.
    accounts_col = db.accounts
    
    # Kullanıcı tanımlı etiketlerin (Tags) tutulduğu collection
    # {name, slug, color, description, user_id}
    tags_col = db.tags

    # AI tarafından maillerden çıkarılan görevlerin (To-Do) tutulduğu collection
    tasks_col = db.tasks

    print("MongoDB bağlantısı başarıyla kuruldu ve koleksiyonlar (Accounts dahil) hazır.")

except Exception as e:
    print(f" MongoDB Bağlantı Hatası: {e}")
    print("İpucu: MongoDB servisinin çalıştığından veya URI bilgisinin doğru olduğundan emin ol.")
    sys.exit(1)