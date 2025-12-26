📧 AI Mail Asistanı: Akıllı Onay & Yönetim Paneli
Automated AI Mail Handler v1.0

Gelen e-postaları yapay zeka ile analiz eden, yanıt taslakları hazırlayan ve kullanıcı onayından sonra SMTP üzerinden gönderen, Python tabanlı tam otomatik bir asistandır.

---

## 👥 Ekip

- **Serhat**
- **Görkem**
- **Samet**
- **Sadık**
---
## 📋 İçindekiler

- [Proje Durumu](#-proje-durumu)
- [Tamamlanan Özellikler](#-tamamlanan-özellikler)
- [Kurulum ve .env Yapılandırması](#-kurulum-ve-.env-Yapılandırması)
- [Kurulum](#-kurulum)
- [Kullanım](#-kullanım)
- [Dosya Yapısı](#-dosya-yapısı)
- [Mimari](#-mimari)

---

## 📊 Proje Durumu

| Bileşen | Durum | Açıklama |
|---------|-------|----------|
| Setup Wizard (Tkinter)| ✅ Tamamlandı | Otomatik .env ve Key oluşturucu |
| Mail Dinleyici Servisi | ✅ Tamamlandı | IMAP tabanlı 60sn periyotlu kontrolk |
| FastAPI Backend| ✅ Tamamlandı | Asenkron API ve Route yönetimi |
| Web Arayüzü (UI)| ✅ Tamamlandı | Dashboard, Editor ve Arşiv sayfaları |
| MongoDB Entegrasyonu | ✅ Tamamlandı | Mail statü takibi ve taslak saklama |
| AI Yanıt Motoru | 🔄 Geliştiriliyor| Taslak oluşturma algoritması|

---
## ✅ Tamamlanan Özellikler

### 1. Akıllı Kurulum Sihirbazı (`setup.py`)

- **Kullanıcının teknik dosya işlemleriyle uğraşmasını engeller**
  - Otomatik Şifreleme: cryptography kullanarak sisteme özel ENCRYPTION_KEY üretir.
  - Görsel Arayüz: Tkinter tabanlı modern giriş ekranı.
  - Sıfır Konfigürasyon: İlk çalıştırmada .env dosyasını kendisi yapılandırır.

### 2. Gelişmiş Yönetim Paneli
  -Dashboard: Onay bekleyen (WAITING_APPROVAL) mailleri anlık listeler.
  -Editör: AI'nın yazdığı taslağı beğenmezseniz üzerinde değişiklik yapmanıza olanak tanır.
  -Arşiv: Gönderilen (SENT) veya İptal edilen (CANCELED) mailleri geçmişe dönük saklar.

## 🗺️ Eksikler ve Hedefler (Roadmap)

### 🔴 Kritik (Yüksek Öncelik)
1. **Kayıt Ol (Register) Sayfası:** Kullanıcıların terminale gerek kalmadan UI üzerinden kayıt olabilmesi.
2. **Giriş (Login) Ekranı:** Dashboard'a erişimi şifre ile koruma altına almak.

### 🟡 Orta Öncelikli
3. **Ayarlar Sayfası:**
   - **İmza Ayarı:** Her mailin sonuna otomatik imza ekleme.
   - **Kontrol Sıklığı:** 60 saniyelik süreyi arayüzden değiştirebilme.
   - **Profil:** Gmail şifresini güncelleyebilme.

### 🟢 Gelecek Özellikler
4. **Manuel Mail Oluşturma:** Sıfırdan yeni e-posta yazma butonu.
5. **İstatistikler:** Cevaplanan mail sayısı ve kazanılan zaman grafikleri.

---

### Kurulum ve .env Yapılandırması
  **1. Virtual environment oluştur**
  `python -m venv .venv`
  **2. Aktive Et**
  `.venv\Scripts\activate`
  **3. Paketleri yükle**
  - `pip install requirements.txt`.
---

### Otomatik Yapılandırma (İlk Çalıştırma)
  - .env dosyası yoksa karşınıza Sistem Yapılandırması penceresi gelir.
  - Email: Gmail adresinizi girin..
  - Uygulama Şifresi: Google hesabınızdan aldığınız 16 haneli kodu girin.
  - Onay: "Kaydet" dediğinizde sistem .env dosyasını oluşturur ve ana uygulamayı başlatır.

---

### Kullanım
  **1. Sistemi Başlatın: Terminalde veya IDE'nizde main.py dosyasını çalıştırın.**
  `python main.py`

  **2.Giriş Yapın: Tarayıcınızda http://127.0.0.1:8000/login adresine gidin.** 
  **3.Kurulum aşamasında belirlediğiniz e-posta ve şifre ile giriş yapın.**
  **4. Mailleri İzleyin: Dashboard ekranında, arka planda çalışan servisin yakaladığı ve AI tarafından taslağı hazırlanan mailleri göreceksiniz.**
  **5.Onaylayın veya Düzenleyin**
  **Geçmişi Kontrol Edin: Arşiv sekmesinden daha önce işlem yaptığınız tüm maillere ve işlem zamanlarına ulaşabilirsiniz.**

---

### MongoDB Veri Yapısı ve Koleksiyonlar

| Koleksiyon Adı | Kayıt Türü | Açıklama |
|---------|-------|----------|
| mails| Dinamik | Gelen mailler, AI taslakları ve işlem geçmişi burada tutulur. |
| users | Sabit | Sisteme giriş yapabilecek yetkili kullanıcı bilgileri. |
| settings| Yapılandırma | Uygulama çalışma parametreleri (kontrol sıklığı vb.). |

---
📁 Dosya Yapısı

MAIL_AI/
├── 📂 app/                     # Uygulama Ana Dizini
│   ├── 📂 core/                # Çekirdek Sistem Bileşenleri
│   │   └── 📄 security.py      # Şifreleme ve Güvenlik İşlemleri
│   ├── 📂 models/              # Veri Modelleri (Şemalar)
│   │   ├── 📄 contact_model.py # Kişi/Rehber Modeli
│   │   └── 📄 mail_model.py    # Mail Veri Yapısı
│   ├── 📂 routes/              # API ve Web Yönlendirmeleri
│   │   ├── 📄 __init__.py
│   │   ├── 📄 approval.py      # Onay Mekanizması Rotaları
│   │   ├── 📄 force_reply.py   # Zorunlu Yanıtlama Rotaları
│   │   └── 📄 ui.py            # Dashboard ve Web Arayüz Rotaları
│   ├── 📂 services/            # Arka Plan Servisleri
│   │   ├── 📄 mail_classifier.py # Mailleri Sınıflandırma (AI)
│   │   ├── 📄 mail_listener.py   # IMAP Dinleyici (Mail Yakalama)
│   │   ├── 📄 mail_sender.py     # SMTP Gönderici
│   │   ├── 📄 ollama_service.py  # Yerel LLM/Ollama Entegrasyonu
│   │   └── 📄 reply_generator.py # AI Yanıt Taslağı Oluşturucu
│   ├── 📂 static/              # CSS ve JS Dosyaları
│   │   ├── 📄 dashboard.js     # Dashboard Etkileşimleri
│   │   ├── 📄 login.css        # Giriş Sayfası Tasarımı
│   │   └── 📄 styles.css       # Genel Uygulama Stili
│   ├── 📂 templates/           # HTML Şablonları (Jinja2)
│   │   ├── 📄 dashboard.html   # Ana Kontrol Paneli
│   │   ├── 📄 editor.html      # Mail Düzenleme Ekranı
│   │   ├── 📄 history.html     # İşlem Geçmişi (Arşiv)
│   │   ├── 📄 layout.html      # Ortak Sayfa Yapısı (Base)
│   │   └── 📄 login.html       # Giriş Ekranı
│   └── 📂 utils/               # Yardımcı Modüller
│       └── 📄 prompt_templates.py # AI İçin Prompt Şablonları
├── 📂 venv/                    # Python Sanal Ortamı
├── 📄 .env                     # (Otomatik) Yapılandırma ve Keyler
├── 📄 .gitignore               # Git Dışı Bırakılacaklar
├── 📄 create_user.py           # Manuel Kullanıcı Oluşturma Scripti
├── 📄 main.py                  # Uygulama Giriş Noktası (FastAPI & Scheduler)
├── 📄 README.md                # (Otomatik) Proje Dokümantasyonu
├── 📄 requirements.txt         # Gerekli Kütüphaneler Listesi
├── 📄 setup.py                 # Otomatik Kurulum Sihirbazı
├── 📄 config.py        # Genel Yapılandırma
└── 📄 database.py      # MongoDB Bağlantı Yönetimi



🏗️ Mimari
┌────────────────────────┐      ┌──────────────────────────┐
│   Kullanıcı Girişi     │      │    Otomatik Kurulum      │
│  (setup.py - Tkinter)  ├─────▶│  (.env & README & Mongo) │
└──────────┬─────────────┘      └────────────┬─────────────┘
           │                                 │
           ▼                                 ▼
┌────────────────────────┐      ┌──────────────────────────┐
│   FastAPI Sunucusu     │      │   Mail Dinleyici (Task)  │
│    (Uvicorn:8000)      │◀─────┤  (60 saniyelik periyot)  │
└──────────┬─────────────┘      └────────────┬─────────────┘
           │                                 │
           ▼                                 ▼
┌────────────────────────┐      ┌──────────────────────────┐
│  MongoDB Veritabanı    │◀─────┤   AI Yanıt Motoru        │
│  (mail_asistani_db)    │      │   (Taslak Üretimi)       │
└────────────────────────┘      └──────────────────────────┘

📜 Lisans
Bu proje eğitim amaçlı geliştirilmiştir.