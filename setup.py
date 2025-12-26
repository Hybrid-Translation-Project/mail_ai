import os
import sys
import tkinter as tk
from tkinter import messagebox
from cryptography.fernet import Fernet
from pymongo import MongoClient
from dotenv import load_dotenv, set_key
from datetime import datetime

# --- DİZİN AYARLARINI SABİTLE ---
# Bu kod, setup.py hangi klasörden çalıştırılırsa çalıştırılsın
# .env dosyasını her zaman bu dosyanın tam yanına koyar.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_FILE = os.path.join(BASE_DIR, ".env")

# Mevcut ayarları yükle
load_dotenv(ENV_FILE)

class SetupWizard:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("AI Mail Asistanı - Master Kurulum")
        self.root.geometry("500x570")
        self.root.resizable(False, False)
        self.root.eval('tk::PlaceWindow . center')

    def setup_system(self, email, password):
        """Mevcut .env'yi korur, eksikleri tamamlar ve DB'ye kullanıcıyı yazar"""
        # .env'den veya varsayılan değerlerden ayarları al
        uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
        db_name = os.getenv("DB_NAME", "mail_asistani_db")
        
        try:
            # 1. ŞİFRELEME ANAHTARI KONTROLÜ
            key = os.getenv("ENCRYPTION_KEY")
            if not key:
                key = Fernet.generate_key().decode()
                set_key(ENV_FILE, "ENCRYPTION_KEY", key)
            
            f = Fernet(key.encode())
            encrypted_pass = f.encrypt(password.encode()).decode()

            # 2. .ENV DOSYASINI GÜNCELLE (Kodun beklediği isimlerle)
            set_key(ENV_FILE, "EMAIL", email)
            set_key(ENV_FILE, "EMAIL_PASSWORD", encrypted_pass)
            
            # URL'ler yoksa onları da ekle (Burası kritik!)
            if not os.getenv("MONGO_URI"):
                set_key(ENV_FILE, "MONGO_URI", uri)
            if not os.getenv("DB_NAME"):
                set_key(ENV_FILE, "DB_NAME", db_name)
            if not os.getenv("OLLAMA_BASE_URL"):
                set_key(ENV_FILE, "OLLAMA_BASE_URL", "http://localhost:11434")
            if not os.getenv("OLLAMA_MODEL"):
                set_key(ENV_FILE, "OLLAMA_MODEL", "llama3.2")

            # 3. MONGODB BAĞLANTISI VE KULLANICI KAYDI
            client = MongoClient(uri, serverSelectionTimeoutMS=2000)
            db = client[db_name]
            
            user_data = {
                "email": email,
                "username": email,
                "password": encrypted_pass,
                "is_active": True,
                "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S") if 'datetime' in globals() else "2025-12-26"
            }
            
            if "users" not in db.list_collection_names():
                db.create_collection("users")
            
            db.users.update_one({"email": email}, {"$set": user_data}, upsert=True)
            
            for col in ["mails", "settings"]:
                if col not in db.list_collection_names():
                    db.create_collection(col)

            return True
        except Exception as e:
            print(f"Hata detayı: {e}")
            return False

    def on_submit(self):
        email = self.entry_email.get().strip()
        pwd = self.entry_pass.get().strip()

        if not email or not pwd or "@" not in email:
            messagebox.showwarning("Eksik Bilgi", "Lütfen geçerli bir email ve şifre girin!")
            return

        if self.setup_system(email, pwd):
            messagebox.showinfo("Başarılı", f"✅ Kurulum Tamamlandı!\n\nDosya Yolu: {ENV_FILE}\n\nUygulamayı başlatabilirsiniz.")
            self.root.destroy()
        else:
            messagebox.showerror("Hata", "MongoDB bağlantısı başarısız! Servis açık mı?")

    def launch(self):
        tk.Label(self.root, text="📧 AI Mail Asistanı Yapılandırma", font=("Arial", 14, "bold")).pack(pady=20)
        
        tk.Label(self.root, text="Giriş Mail Adresiniz:").pack()
        self.entry_email = tk.Entry(self.root, width=40, justify="center")
        self.entry_email.pack(pady=5)
        
        current_mail = os.getenv("EMAIL") or os.getenv("EMAIL_USER")
        if current_mail: self.entry_email.insert(0, current_mail)

        tk.Label(self.root, text="Gmail Uygulama Şifreniz (16 Hane):").pack(pady=(15,0))
        self.entry_pass = tk.Entry(self.root, width=40, show="*", justify="center")
        self.entry_pass.pack(pady=5)

        info_box = tk.Label(self.root, text=f"DOSYA KONUMU:\n{BASE_DIR}", 
                           bg="#fff9c4", padx=10, pady=10, font=("Consolas", 8), wraplength=400)
        info_box.pack(pady=20)

        tk.Button(self.root, text="AYARLARI VE KULLANICIYI KAYDET", command=self.on_submit, 
                  bg="#2ecc71", fg="white", font=("Arial", 10, "bold"), padx=20, pady=12).pack()

        self.root.mainloop()

# --- DIŞARIDAN ÇAĞRILABİLMESİ İÇİN ---
def run_setup():
    wizard = SetupWizard()
    wizard.launch()

if __name__ == "__main__":
    run_setup()