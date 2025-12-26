import os
import tkinter as tk
from tkinter import messagebox
from cryptography.fernet import Fernet
from pymongo import MongoClient

ENV_FILE = ".env"
MONGO_URI = "mongodb://localhost:27017/"  # Varsayılan yerel bağlantı
DB_NAME = "mail_asistani_db"

class SetupWizard:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("AI Mail Asistanı - Akıllı Kurulum")
        self.root.geometry("500x550")
        self.root.resizable(False, False)
        self.root.eval('tk::PlaceWindow . center')

    def setup_mongodb(self):
        """MongoDB veritabanını ve koleksiyonları otomatik oluşturur"""
        try:
            # Bağlantıyı test et (2 saniye zaman aşımı)
            client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=2000)
            client.server_info() 
            
            db = client[DB_NAME]
            
            # Oluşturulacak koleksiyon listesi
            collections = ["mails", "users", "settings"]
            
            for col in collections:
                if col not in db.list_collection_names():
                    db.create_collection(col)
            
            # İlk ayarı ekle
            if db.settings.count_documents({}) == 0:
                db.settings.insert_one({"check_interval": 60, "is_active": True})
            
            return True
        except Exception as e:
            print(f"MongoDB Hatası: {e}")
            return False

    def create_readme(self):
        """Profesyonel README dosyasını otomatik oluşturur"""
        readme_content = """# 📧 AI Mail Asistanı: Akıllı Yönetim Sistemi

Bu proje, gelen e-postaları AI ile analiz eden ve onay mekanizması sunan hibrit bir sistemdir.

---

## 📊 Proje Durumu
| Bileşen | Durum | Açıklama |
| :--- | :--- | :--- |
| **Setup Wizard** | ✅ Tamamlandı | Otomatik yapılandırma aktif |
| **MongoDB** | ✅ Hazır | Koleksiyonlar otomatik oluşturuldu |
| **FastAPI Backend** | ✅ Aktif | Mail trafiği yönetiliyor |

## 🗄️ MongoDB Koleksiyonları
- **mails:** Gelen mailler ve AI taslakları.
- **settings:** Sistem çalışma parametreleri.
- **users:** Yetkili kullanıcı bilgileri.

## 🛠 Kurulum Notu
Sistem ilk çalıştırıldığında `.env` ve bu `README.md` dosyasını otomatik olarak oluşturur. Gmail için **Uygulama Şifresi** kullanılması zorunludur.

---
**Son Güncelleme:** 2025-12-25
"""
        with open("README.md", "w", encoding="utf-8") as f:
            f.write(readme_content)

    def create_env(self, email, password):
        """Şifreli .env dosyasını oluşturur"""
        try:
            key = Fernet.generate_key().decode()
            content = (
                f"ENCRYPTION_KEY={key}\n"
                f"EMAIL={email}\n"
                f"EMAIL_PASSWORD={password}\n"
                f"MONGO_URI={MONGO_URI}\n"
                f"DB_NAME={DB_NAME}\n"
            )
            with open(ENV_FILE, "w", encoding="utf-8") as f:
                f.write(content)
            return True
        except Exception as e:
            messagebox.showerror("Hata", f"Dosya yazılırken hata oluştu: {e}")
            return False

    def on_submit(self):
        email = self.entry_email.get().strip()
        pwd = self.entry_pass.get().strip()

        if not email or not pwd or email == "örnek: adiniz@gmail.com":
            messagebox.showwarning("Eksik Bilgi", "Lütfen tüm alanları doldurun!")
            return

        if "@" not in email:
            messagebox.showwarning("Geçersiz Email", "Lütfen geçerli bir e-posta adresi girin.")
            return

        # 1. Önce MongoDB'yi hazırla
        if not self.setup_mongodb():
            messagebox.showerror("Bağlantı Hatası", "MongoDB'ye bağlanılamadı! Lütfen MongoDB servisinin çalıştığından emin olun.")
            return

        # 2. Env ve README oluştur
        if self.create_env(email, pwd):
            self.create_readme()
            messagebox.showinfo("Başarılı", "Her Şey Hazır!\n\n- .env oluşturuldu.\n- MongoDB koleksiyonları hazırlandı.\n- README.md oluşturuldu.")
            self.root.destroy()

    def launch(self):
        # Tasarım ve Başlık
        tk.Label(self.root, text="🚀 AI Mail Asistanı Kurulumu", font=("Arial", 16, "bold"), fg="#2c3e50").pack(pady=25)
        
        # Email
        tk.Label(self.root, text="Gmail Adresiniz:", font=("Arial", 10, "bold")).pack()
        self.entry_email = tk.Entry(self.root, width=45, font=("Arial", 10), justify="center")
        self.entry_email.pack(pady=5)
        self.entry_email.insert(0, "örnek: adiniz@gmail.com")

        # Şifre
        tk.Label(self.root, text="Gmail Uygulama Şifresi:", font=("Arial", 10, "bold")).pack(pady=(15, 0))
        self.entry_pass = tk.Entry(self.root, width=45, font=("Arial", 10), show="*", justify="center")
        self.entry_pass.pack(pady=5)

        # Bilgi Kutusu
        info_frame = tk.Frame(self.root, bg="#ecf0f1", padx=10, pady=10)
        info_frame.pack(pady=20)
        info_text = (
            "📌 SİSTEM OTOMATİK OLARAK:\n"
            "1. MongoDB Veritabanını yapılandırır.\n"
            "2. Güvenli Şifreleme Anahtarını üretir.\n"
            "3. Teknik dokümantasyonu (README) hazırlar."
        )
        tk.Label(info_frame, text=info_text, font=("Arial", 8), bg="#ecf0f1", justify="left").pack()

        # Buton
        btn_save = tk.Button(
            self.root, text="KURULUMU TAMAMLA VE BAŞLAT", command=self.on_submit,
            bg="#27ae60", fg="white", font=("Arial", 10, "bold"), padx=25, pady=12, cursor="hand2"
        )
        btn_save.pack(pady=20)

        self.root.mainloop()

def run_setup():
    wizard = SetupWizard()
    wizard.launch()

if __name__ == "__main__":
    run_setup()