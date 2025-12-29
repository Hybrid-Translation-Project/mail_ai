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

### Akıllı Kurulum & Güvenlik Sihirbazı (setup.py)

- **Kullanıcının teknik dosya işlemleriyle uğraşmasını engeller**
  - Otomatik Şifreleme: cryptography kullanarak sisteme özel ENCRYPTION_KEY üretir ve hassas uygulama şifrelerini AES-256 ile korur.
  - Görsel Arayüz: Tkinter tabanlı modern ve kullanıcı dostu yapılandırma ekranı.
  - Sıfır Konfigürasyon: İlk çalıştırmada .env dosyasını otomatik oluşturur, veritabanı ve AI motoru bağlantılarını hazırlar.
  - Master Password: Panelinize erişimi korumak için kurulum anında kişisel bir giriş şifresi (Panel Şifresi) belirleme imkanı.

### 2. Gelişmiş Yönetim Paneli
  - Komuta Merkezi (Dashboard): Onay bekleyen mailleri, acil görevleri ve sistem istatistiklerini anlık olarak takip edebileceğiniz modern arayüz.
  - Akıllı Editör: AI tarafından hazırlanan taslakları gerçek zamanlı inceleme, düzenleme veya farklı tonlarda (resmi/samimi) yeniden oluşturma özelliği.
  - Karar Merkezi: AI'nın maillerden çıkardığı toplantı, randevu veya iş teklifi önerilerini tek tıkla onaylayıp "Görevler" listesine ekleme.
  - Gelişmiş Arşiv: Gönderilen veya iptal edilen tüm işlemleri tarih bazlı saklayan ve yönetilebilen (silme/temizleme destekli) geçmiş sistemi.

  ### 3. Akıllı Hesap & Sistem Yönetimi
  - Dinamik Ayarlar: Terminale dokunmadan panel üzerinden bağlı mail adresini, panel giriş şifresini veya Google API anahtarını güncelleme yeteneği.
  - Güvenli Doğrulama: Kritik sistem değişiklikleri ve API anahtarı güncellemeleri için çift katmanlı (Panel şifresi onaylı) doğrulama mekanizması.
  - Ollama Entegrasyonu: Kullanılan AI modelini ve API adresini arayüz üzerinden anlık olarak değiştirebilme esnekliği.

## 🗺️ Eksikler ve Hedefler (Roadmap)

### 🔴 Kritik (Yüksek Öncelik)
1. **Dinamik Kontrol Sıklığı**: 60 saniyelik mail tarama süresini settings.html üzerinden anlık olarak değiştirebilme altyapısı.
2. **Session Yönetimi:** Kullanıcı giriş yaptıktan sonra tarayıcıyı kapatsa bile oturumun güvenli şekilde (Cookie/JWT) korunması ve "Çıkış Yap" butonu aktivasyonu.

### 🟡 Orta Öncelikli
3. **Ayarlar Sayfası:**
   - **İmza Ayarı:** Her mailin sonuna otomatik imza ekleme.
   - **Kontrol Sıklığı:** 60 saniyelik süreyi arayüzden değiştirebilme.
   - **Çoklu Dil Desteği:** AI'nın sadece Türkçe değil, gelen mailin diline göre (İngilizce, Almanca vb.) otomatik dilde cevap taslağı hazırlayabilmesi.
   - **Gelişmiş Filtreleme:** Gelen kutusunda "Sadece Onay Bekleyenler" veya "Sadece Belirli Şirketler" bazlı gelişmiş arama ve filtreleme seçenekleri.

### 🟢 Gelecek Özellikler
4. **Manuel Mail Oluşturma:** Sıfırdan yeni e-posta yazma butonu.
5. **İstatistikler:** Cevaplanan mail sayısı ve kazanılan zaman grafikleri.
6. **Performans Analitiği:** Yanıtlanan mail sayıları, AI'nın kurtardığı toplam süre ve şirket bazlı etkileşim yoğunluğunu gösteren görsel grafikler (Chart.js entegrasyonu).
7. **Sesli Komut Entegrasyonu (Voice-to-Mail):** Taslakları sesli komutla onaylama, reddetme veya sesle not ekleyerek taslağı revize etme.

---

### Kurulum ve .env Yapılandırması
  ## 1. Virtual environment oluştur

  ```bash
  python -m venv .venv
  ```

  ## 2. Aktive Et
  ```bash
  .venv\Scripts\activate
  ```

  ## 3. Paketleri yükle
  ```bash
  pip install requirements.txt
  ```
---

### Otomatik Yapılandırma (İlk Çalıştırma)
  - .env dosyası yoksa karşınıza Sistem Yapılandırması penceresi gelir.
  - Email: Gmail adresinizi girin..
  - Uygulama Şifresi: Google hesabınızdan aldığınız 16 haneli kodu girin.
  - Onay: "Kaydet" dediğinizde sistem .env dosyasını oluşturur ve ana uygulamayı başlatır.

---

### Kullanım
**1.setup py dosyasını çalıştırın**  
```bash
setup.py
```
**2.gerekli alanları doldurun**
**3. main dosyasına gelip dosyayı çalıştırın**
```bash
main.py
```
**4. mail ve şifreniz ile giriş yapınız**
  

---

### MongoDB Veri Yapısı ve Koleksiyonlar

| Koleksiyon Adı | Kayıt Türü | Anahtar Alanlar (Fields) | Açıklama |
|---------|-------|----------|----------|
| mails| Dinamik | subject, body, reply_draft, status, from | Gelen mailler, AI taslakları ve işlem geçmişi burada tutulur. |
| users | Sabit | email, master_password, app_password, is_active | Sisteme giriş yapabilecek yetkili kullanıcı bilgileri. |
| settings| Yapılandırma | check_interval, signature, ai_model | Uygulama çalışma parametreleri (kontrol sıklığı vb.). |
| tasks | Dinamik | title, due_date, status, sender | AI'nın maillerden ayıkladığı, onay bekleyen veya kesinleşmiş görev/ajanda kayıtlarıdır.|
| contacts | İlişkisel | email, name, ai_notes, default_tone | Şirket hafızasını oluşturan rehber verileri; AI'nın branch/kişi özelinde aldığı kritik notları saklar.|


---
📁 Dosya Yapısı

```
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
|   |   ├── 📄 extractor.py       # Görev Çıkarımı
│   │   ├── 📄 mail_listener.py   # IMAP Dinleyici (Mail Yakalama)
│   │   ├── 📄 mail_sender.py     # SMTP Gönderici
│   │   ├── 📄 ollama_service.py  # Yerel LLM/Ollama Entegrasyonu
│   │   └── 📄 reply_generator.py # AI Yanıt Taslağı Oluşturucu
│   ├── 📂 static/              # CSS ve JS Dosyaları
│   │   ├── 📂 css/     # 
|   |   |    ├──📄 contacts.css
|   |   |    ├──📄 dashboard.css
|   |   |    ├──📄 home.css
|   |   |    ├──📄 login.css
|   |   |    ├──📄 settings.css
|   |   |    ├──📄 styles.css
|   |   |    ├──📄 tasks.css
|   |   |    └──📄 writer.css
│   │   ├── 📂 static/         # Giriş Sayfası Tasarımı
│   │   |    ├──📄 dashboard.js
|   |   |    ├──📄 editor.js
|   |   |    ├──📄 home.js
|   |   |    └──📄 sear.js
│   ├── 📂 templates/           # HTML Şablonları (Jinja2)
│   │   ├── 📄 dashboard.html   # Ana Kontrol Paneli
│   │   ├── 📄 editor.html      # Mail Düzenleme Ekranı
│   │   ├── 📄 history.html     # İşlem Geçmişi (Arşiv)
│   │   ├── 📄 tasks.html       # Göreb Sayfa Yapısı 
|   |   ├── 📄 base.html        # Ana Sayfa Yapısı 
|   |   ├── 📄 writer.html      # Mail Yazdırma Sayfa Yapısı
|   |   ├── 📄 settings.html    # Ayarlar Sayfa Yapısı
|   |   ├── 📄 Home.html        # Giriş Sayfası
|   |   ├── 📄 contacts.html    # Şirketler ve Rehber Sayfa Yapısı
|   |   ├── 📄 contacts.html    # Şirketler ve Rehber Detay Sayfa Yapısı
│   │   └── 📄 login.html       # Giriş Ekranı
|   |
|   |
│   ├── 📂 utils/               # Yardımcı Modüller
│   │    └── 📄 prompt_templates.py # AI İçin Prompt Şablonları
|   │
│   ├──📄 main.py                  # Uygulama Giriş Noktası (FastAPI & Scheduler)
|   ├──📄 config.py        # Genel Yapılandırma
│   └──📄 database.py      # MongoDB Bağlantı Yönetimi
|
├── 📂 venv/                    # Python Sanal Ortamı
├── 📄 .env                     # (Otomatik) Yapılandırma ve Keyler
├── 📄 .gitignore               # Git Dışı Bırakılacaklar
├── 📄 create_user.py           # Manuel Kullanıcı Oluşturma Scripti
├── 📄 README.md                # (Otomatik) Proje Dokümantasyonu
├── 📄 requirements.txt         # Gerekli Kütüphaneler Listesi
└── 📄 setup.py                 # Otomatik Kurulum Sihirbazı

```
---

# 🏗️ Mimari
```
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
```

---
# 📜 Lisans
Bu proje eğitim amaçlı geliştirilmiştir.