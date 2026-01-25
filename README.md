AI Mail Asistanı
Automated AI Mail Handler 

Gelen e-postaları yapay zeka ile analiz eden, yanıt taslakları hazırlayan, sesli komutlarla yönetilebilen ve tüm bunları internet bağlantısı olmadan (Offline), verilerinizi dışarı çıkarmadan yapan Python tabanlı akıllı asistan.

---
## 📋 İçindekiler

- [🧠 Algoritma ve Çalışma Mantığı](#-algoritma-ve-çalışma-mantığı)
- [✨ Özellikler](#-özellikler)
  - [1. 🔒 Tamamen Yerel ve Güvenli](#1--tamamen-yerel-ve-güvenli-privacy-first)
  - [2. ⚙️ Web Tabanlı Akıllı Kurulum](#2-️-web-tabanlı-akıllı-kurulum)
  - [3. 🎙️ Sesli Asistan (Jarvis Modu)](#3-️-sesli-asistan-jarvis-modu)
  - [4. 📝 Akıllı Editör & Writer Ayrımı](#4--akıllı-editör--writer-ayrımı)
- [🛠️ Kurulum](#️-kurulum)
  - [Gereksinimler](#gereksinimler)
  - [Adım 1: Ortam Kurulumu](#adım-1-depoyu-klonlayın-ve-ortamı-kurun)
  - [Adım 2: Bağımlılıklar](#adım-2-bağımlılıkları-yükleyin)
  - [Adım 3: AI Model Kurulumu](#adım-3-ollama-ve-model-kurulumu)
  - [Adım 4: Başlatma](#adım-4-uygulamayı-başlatın-kurulum-burada-başlar)
  - [Adım 5: Web Kurulumu](#adım-5-web-kurulumunu-tamamlayın)
- [🗄️ MongoDB Yapısı](#-veritabanı-yapısı)
- [📂 Dosya Yapısı](#-dosya-yapısı)
- [📊 Proje Durumu](#-proje-durumu)
- [📜 Lisans](#-lisans)
---


## 🧠 Algoritma ve Çalışma Mantığı
- Proje, veritabanı kirliliğini önlemek ve kullanıcı deneyimini artırmak için İki Ana Akış ve bir Sesli Kontrol Katmanı üzerine kuruludur.
```mermaid
graph TD
    subgraph "Backend Core (Ana Sistem)"
        A[FastAPI Server] -->|Veri| DB[(MongoDB)]
        A -->|AI Metin| O[Ollama / Llama 3.2]
        A -->|AI Ses| W[Faster-Whisper]
        
        subgraph "Bağlantı Katmanı"
            A -->|Hesap 1| ACC1[Gmail 1 (SMTP/IMAP)]
            A -->|Hesap 2| ACC2[Gmail 2 (SMTP/IMAP)]
            ACC1 & ACC2 -.->|Birleştirilmiş| U_INBOX[Unified Inbox]
        end
    end

    subgraph "Akış 1: Gelen Kutusu & AI Analiz"
        M[Mail Gelir] --> DETECT{AI Analizi}
        DETECT -- "İş/Tarih Var" --> TASK[Görev Yöneticisine Ekle]
        DETECT -- "Normal Mail" --> DRAFT_GEN[Cevap Taslağı Üret]
        
        DRAFT_GEN --> UI_INBOX[Arayüz: Gelen Kutusu]
        UI_INBOX --> ACT1{Kullanıcı Kararı}
        ACT1 -- "Onayla" --> SEND1[Maili Gönder]
        ACT1 -- "Reddet/Yenile" --> REGEN[Yeniden Yaz]
    end

    subgraph "Akış 2: Writer (Yazar Modu)"
        NEW[Yeni Mail Başlat] --> INPUT{Giriş Yöntemi}
        INPUT -- "Klavye" --> TYPE[Elle Yaz]
        INPUT -- "Mikrofon" --> VOICE_FLOW
        INPUT -- "AI Prompt" --> OLLAMA_GEN[AI Taslak Üret]

        TYPE & VOICE_FLOW & OLLAMA_GEN --> MERGE[Editör Alanı]
        MERGE --> AS[Auto-Save (1 sn)]
        AS --> DB_DRAFT[Veritabanı: DRAFT]
        DB_DRAFT --> LIST((Taslaklar Sayfası))
        LIST --> PRE_SEND[Onay Modalı] --> SEND2[Maili Gönder]
    end

    subgraph "Akış 3: Sesli Komut Modülü"
        MIC[Mikrofon] -->|Ses Verisi| LOCK[Buton Kilitle (Processing)]
        LOCK --> W
        W -->|Metin Çıktısı| FILTER{Analiz & Filtre}
        
        FILTER -- "Halüsinasyon" --> IGNORE[Yoksay]
        FILTER -- "Komut (Gönder/Sil)" --> FUNC[Fonksiyonu Çalıştır]
        FILTER -- "Dikte (Yazı)" --> FOCUS[Odaklanılan Kutuya Yaz]
        
        FUNC & FOCUS --> UNLOCK[Kilidi Aç]
    end
```
---

## ✨ Özellikler
1. **🔒 Tamamen Yerel ve Güvenli (Privacy-First)** 
- **Yerel LLM:** Ollama kullanarak mail içerikleri asla OpenAI veya Google sunucularına gönderilmez.
- **Yerel Ses İşleme:** Faster-Whisper ile sesli komutlar bilgisayarınızda işlenir. 
- **Şifreli Veri:** Uygulama şifreleri ve hassas veriler Fernet (AES) ile şifrelenerek saklanır.

2. **🎙️ Sesli Asistan (Jarvis Modu)**
- **Bas-Konuş:** Writer arayüzünde konuşarak mail yazdırabilirsiniz (Dikte).
- **Komut Sistemi:** "Maili gönder", "Taslağı kaydet", "Yeniden yaz" gibi komutlarla klavyesiz yönetim.
- **Offline:** İnternet kesilse bile ses tanıma çalışmaya devam eder.

3. **📝 Akıllı Editör & Writer Ayrımı**
- **Inbox (Gelen Kutusu):** Yapay zeka her maile otomatik cevap taslağı hazırlar. Bu taslaklar, siz müdahale edene kadar "Taslaklar" sayfasını kirletmez.
- **Writer (Yazar):** Sıfırdan mail yazarken Auto-Save devreye girer. Elektrik kesilse bile yazdıklarınız anında kaydedilir ve Taslaklar sayfasında listelenir.

4. **🤖 Görev ve Karar Merkezi**
- AI, mailleri analiz eder ve içindeki toplantı, fatura ödeme gibi görevleri JSON formatında çıkararak Görevler paneline ekler.
- "Kabul Et" veya "Reddet" butonları ile AI, mailin içeriğini seçiminize göre (Resmi/Samimi) yeniden yazar.

---

## 🛠️ Kurulum
 ## Gereksinimler
- Python 3.10+
- MongoDB
- Ollama (Llama 3.2 Modeli)
- FFmpeg

## 1: Depoyu Klonlayın ve Ortamı Kurun
```bash
    git clone https://github.com/kullaniciadi/mail-ai.git
    cd mail-ai
    python -m venv venv
    # Windows için:
    venv\Scripts\activate
    # Mac/Linux için:
    source venv/bin/activate
```
## 2: Bağımlılıkları Yükleyin
    ```bash
    pip install -r requirements.txt
    ```

## 3: Ollama Kurulumu
- Yapay zeka modelini çalıştırabilmek için Ollama uygulamasının bilgisayarınızda kurulu olması gerekir.
- Ollama.com adresine gidin.
- İşletim sisteminize (Windows/Mac/Linux) uygun versiyonu indirip kurun.
- Kurulum bitince terminalden ollama --version yazarak kontrol edin.

## 4: AI Modelini Çekin
- Ollama kurulduktan sonra terminale şu komutu girerek modelin inmesini bekleyin
```bash
ollama pull llama3.2
```
## 5: Ses Modelini (Whisper) İndirin
- Sesli komut özelliklerinin hızlı çalışması için Whisper modelini önceden indirin. (Bu işlem yaklaşık 1.5 GB veri indirir, lütfen "İŞLEM TAMAMLANDI" yazısını görene kadar bekleyin):
```bash
python download_model.py
```

## 6: Otomatik Kurulumu Başlatın
- Sistemin .env dosyasını ve veritabanı ayarlarını yapması için main.py dosyasını çalıştırın:
```bash
python main.py
```
## 6: Sistemi Çalıştırma
- sistemi sürekli main dosyası ile çalıştırmaya gerek yok application_run dosyası ile direkt çalıştırabilirsiniz
```bash
python download_model.py
```


## 🗄️ Veritabanı Mimarisi (MongoDB)

Proje, verisel bütünlüğü korumak için NoSQL yapısını kullanır. Aşağıda koleksiyonların şeması ve kullanım amaçları detaylandırılmıştır.

| Koleksiyon | Kayıt Türü | Kritik Alanlar (Fields) | Açıklama |
| :--- | :--- | :--- | :--- |
| **mails** | `Dinamik` | `subject`, `body`, `type` ('inbox'/'outbound'), `status` ('WAITING'/'DRAFT'/'SENT'), `reply_draft`, `draft_history` | **Sistemin Kalbi.** Hem gelen kutusu maillerini hem de Writer ile yazılan yeni taslakları tutar. `type` alanı, mailin gelen kutusunda mı yoksa taslaklarda mı görüneceğini belirler. |
| **users** | `Sabit` | `email`, `master_password` (Hash), `full_name`, `company_name`, `created_at` | Panele giriş yapabilen ana yönetici kullanıcı bilgileri. |
| **accounts** | `Yapılandırma` | `email`, `password` (AES Şifreli), `provider`, `signature` | **Çoklu Hesap Desteği.** Mail göndermek için kullanılan SMTP hesapları ve her hesaba özel imza ayarları burada saklanır. |
| **contacts** | `İlişkisel` | `email`, `name`, `ai_summary`, `last_contacted`, `interaction_count` | **CRM Hafızası.** Kişilerle olan geçmiş yazışmaların AI tarafından çıkarılmış özetleri ve iletişim sıklığı burada tutulur. |
| **tasks** | `Dinamik` | `title`, `due_date`, `urgency_score` (1-10), `source_mail_id`, `status` | AI'nın maillerden ayıkladığı "Fatura Öde", "Toplantı Yap" gibi aksiyon öğeleri. |
| **settings** | `Config` | `ollama_model`, `voice_speed`, `theme`, `check_interval` | Uygulamanın genel davranış ayarları (Tema, AI Modeli, Tarama Sıklığı vb.). |

---

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
│   │   ├── 📄 ui.py            # Dashboard ve Web Arayüz Rotaları
│   │   └── 📄 voice.py         # Sesli Komutları yönlendirme
│   ├── 📂 services/              # Arka Plan Servisleri
│   │   ├── 📄 extractor.py       # Görev Çıkarımı
|   |   ├── 📄 mail_classifier.py # Mailleri Sınıflandırma (AI)
│   │   ├── 📄 mail_listener.py   # IMAP Dinleyici (Mail Yakalama)
│   │   ├── 📄 mail_sender.py     # SMTP Gönderici
│   │   ├── 📄 ollama_service.py  # Yerel LLM/Ollama Entegrasyonu
│   │   ├── 📄 reply_generator.py # AI Yanıt Taslağı Oluşturucu
│   │   └── 📄 voice_service.py   # Sesli Komut algılayıcı
│   ├── 📂 static/ # CSS ve JS Dosyaları
│   │   ├── 📂 css/    
|   |   |    ├──📄 base.css
|   |   |    ├──📄 contacts.css
|   |   |    ├──📄 dashboard.css
|   |   |    ├──📄 editor.css
|   |   |    ├──📄 history.css
|   |   |    ├──📄 home.css
|   |   |    ├──📄 login.css
|   |   |    ├──📄 settings.css
|   |   |    ├──📄 setup_web.css
|   |   |    ├──📄 styles.css
|   |   |    ├──📄 tasks.css
|   |   |    ├──📄 view_html.css
|   |   |    └──📄 writer.css
│   │   ├── 📂 js/         
│   │   |    ├──📄 contacts.js
│   │   |    ├──📄 dashboard.js
│   │   |    ├──📄 drafts.js
│   │   |    ├──📄 editor.js
│   │   |    ├──📄 home.js
│   │   |    ├──📄 script.js
|   |   |    ├──📄 search.js
|   |   |    ├──📄 tasks.js
|   |   |    ├──📄 voice.js
|   |   |    └──📄 writer.js
│   ├── 📂 templates/           
│   │   ├── 📄 accounts.html   
│   │   ├── 📄 base.html      
│   │   ├── 📄 contact_detail.html     
│   │   ├── 📄 contacts.html       
|   |   ├── 📄 dashboard.html        
|   |   ├── 📄 drafts.html      
|   |   ├── 📄 editor.html      
|   |   ├── 📄 history.html      
|   |   ├── 📄 home.html      
|   |   ├── 📄 login.html      
|   |   ├── 📄 settings.html    
|   |   ├── 📄 setup_web.html        
|   |   ├── 📄 tasks.html    
|   |   ├── 📄 view_mail.html    
│   │   └── 📄 writer.html       
│   ├── 📂 utils/               # Yardımcı Modüller
│   │    └── 📄 prompt_templates.py # AI İçin Prompt Şablonları
|   │
│   ├──📄 main.py          # Uygulama Giriş Noktası (FastAPI & Scheduler)
|   ├──📄 config.py        # Genel Yapılandırma
│   └──📄 database.py      # MongoDB Bağlantı Yönetimi
|
├── 📂 venv/                    # Python Sanal Ortamı
├── 📄 .env                     # (Otomatik) Yapılandırma ve Keyler
├── 📄 .gitignore               # Git Dışı Bırakılacaklar
├── 📄 application_run.py       # sistemi direkt olarak çalıştıran dosya
├── 📄 create_user.py           # Herhangi Bir Olumsuzlukta Manuel Kullanıcı Oluşturma Scripti
├── 📄 download_model.py        # Mikrofon için gerekli modeli indirme scripti
├── 📄 README.md                # Proje Dokümantasyonu
├── 📄 requirements.txt         # Gerekli Kütüphaneler Listesi
└── 📄 USER_MANUAL.txt          # Kullanım Kılavuzı
```
---
## 📜 Lisans
- Bu proje, kişisel verilerin korunması ve açık kaynak felsefesi gözetilerek eğitim amaçlı geliştirilmiştir. MIT License altında dağıtılabilir.
