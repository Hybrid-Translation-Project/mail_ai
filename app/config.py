import os
from dotenv import load_dotenv

load_dotenv()

# Değişken isimlerini .env ile birebir aynı yapıyoruz
EMAIL_USER = os.getenv("EMAIL") # setup.py EMAIL yazar
EMAIL_PASS = os.getenv("EMAIL_PASSWORD") # setup.py EMAIL_PASSWORD yazar
OLLAMA_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
DB_NAME = os.getenv("DB_NAME", "mail_asistani_db")
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")