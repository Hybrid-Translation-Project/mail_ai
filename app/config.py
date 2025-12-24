# .env dosyasını okumak için
from dotenv import load_dotenv

# Ortam değişkenlerine erişmek için
import os

# .env dosyasını belleğe yükler
# Bu satır olmazsa os.getenv() None döner
load_dotenv()

# Gmail adresi (ileride SMTP / gönderme için)
EMAIL_USER = os.getenv("EMAIL_USER")

# Gmail App Password (normal şifre DEĞİL)
EMAIL_PASS = os.getenv("EMAIL_PASS")

# Ollama servisinin çalıştığı adres
# Örnek: http://localhost:11434
OLLAMA_URL = os.getenv("OLLAMA_URL")

# Kullanılacak model adı
# Örnek: llama3.2
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL")

# MongoDB bağlantı adresi
MONGO_URI = os.getenv("MONGO_URI")

# Kullanılacak database adı
DB_NAME = os.getenv("DB_NAME")
