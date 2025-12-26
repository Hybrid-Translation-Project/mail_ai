# MongoDB istemcisi
from pymongo import MongoClient

# Bağlantı bilgilerini config dosyasından alıyoruz
from app.config import MONGO_URI, DB_NAME

# MongoDB’ye bağlantı açılır
# Bu bağlantı uygulama boyunca kullanılır
client = MongoClient(MONGO_URI)

# Kullanılacak database seçilir
db = client[DB_NAME]

#Gelen maillerin tutulduğu collection
mails_col = db.mails

#Kişi profillerinin tutulacağı collection
contacts_col = db.contacts

#Kullanıcıların (şifreli parolalarının) tutulacağı collection
# Mail listener ve sender servisleri şifreyi buradan okuyacak.
users_col = db.users