# app/database.py
# MongoDB istemcisi
from pymongo import MongoClient
from pymongo.operations import SearchIndexModel # İndeks oluşturmak için gerekli
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

    # Kişi profillerinin tutulacağı collection
    contacts_col = db.contacts

    # Panel giriş yetkisi olan ana kullanıcıların tutulacağı collection
    users_col = db.users

    # Bağlı olan mail hesaplarının tutulacağı collection
    accounts_col = db.accounts
    
    # Kullanıcı tanımlı etiketlerin (Tags) tutulduğu collection
    # {name, slug, color, description, user_id}
    tags_col = db.tags

    # AI görevlerinin tutulduğu collection
    tasks_col = db.tasks

    print("✅ MongoDB bağlantısı başarıyla kuruldu.")

    # --- OTOMATİK INDEX KURULUMU (INIT_DB) ---
    def init_db():
        """
        Veritabanı başlatıldığında çalışır.
        Eğer Atlas Vektör Arama indeksi yoksa, otomatik olarak oluşturur.
        Manuel ayar yapma derdini ortadan kaldırır.
        """
        print("⏳ Veritabanı arama indeksleri kontrol ediliyor...")
        
        try:
            # Mevcut arama indekslerini listele
            # Not: Bu özellik sadece MongoDB Atlas'ta çalışır.
            existing_indexes = list(mails_col.list_search_indexes())
            index_names = [index.get("name") for index in existing_indexes]
            
            if "vector_index" not in index_names:
                print("⚙️ 'vector_index' bulunamadı, otomatik oluşturuluyor... (1-2 dk sürebilir)")
                
                # Atlas Vector Search İndeks Tanımı
                # Local model (MiniLM) kullandığımız için boyut 384 olarak ayarlandı.
                index_model = SearchIndexModel(
                    definition={
                        "fields": [
                            {
                                "type": "vector",
                                "path": "embedding",
                                "numDimensions": 384, # all-MiniLM-L6-v2 modelinin vektör boyutu
                                "similarity": "cosine"
                            }
                        ]
                    },
                    name="vector_index",
                    type="vectorSearch"
                )
                
                # İndeksi oluştur
                mails_col.create_search_index(model=index_model)
                print("✅ 'vector_index' oluşturma komutu gönderildi. Atlas arka planda hazırlıyor.")
            else:
                print("✅ 'vector_index' zaten mevcut, her şey hazır.")
                
        except Exception as e:
            # Eğer yerel MongoDB (Community Edition) kullanılıyorsa bu özellik çalışmaz, uyarı verip geçeriz.
            print(f"⚠️ İndeks kontrolü uyarısı: {e}")
            print("Bilgi: Bu özellik sadece MongoDB Atlas (Bulut) üzerinde çalışır. Yerel DB'de bu adımı atlayabilirsiniz.")

    # Başlangıç fonksiyonunu çalıştır
    init_db()

except Exception as e:
    print(f"❌ MongoDB Bağlantı Hatası: {e}")
    print("İpucu: MongoDB servisinin çalıştığından veya URI bilgisinin doğru olduğundan emin ol.")
    sys.exit(1)