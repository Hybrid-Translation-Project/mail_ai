# AI Mail Asistanı - Kullanıcı El Kitabı

**AI Mail Asistanı**, e-posta süreçlerinizi yapay zeka, sesli komutlar ve otomasyon ile yönetmenizi sağlayan yeni nesil bir masaüstü asistanıdır.

Bu kılavuz, sol menüde yer alan tüm sayfaların ve özelliklerin ne işe yaradığını anlatır.

---

## 1. Kurulum ve Teknik Ayarlar
Bu doküman **sistemin kullanımı** hakkındadır.

Eğer sistemi henüz kurmadıysanız; Python kütüphanelerinin yüklenmesi, `.env` dosyasının oluşturulması ve veritabanı bağlantıları için lütfen teknik kurulum dosyamıza göz atın:

**[Kurulum için: README.md](README.md)**

---

## 2. Menü ve Sayfa Rehberi

Uygulamanın sol menüsünde yer alan bölümlerin detaylı açıklamaları aşağıdadır:

###  ANA MENÜ

#### **Komuta Merkezi **
Burası sistemin ana kontrol panelidir.
* **Genel Durum:** Toplam mail, okunmamış mail ve bekleyen görev sayılarını görürsünüz.
* **Sistem Sağlığı:** İnternet bağlantısı, Veritabanı ve AI Motorunun (Ollama) çalışma durumunu anlık takip edersiniz.
* **Hızlı Bakış:** Son gelen mailler ve AI'nın yaptığı son işlemlerin özet akışıdır.

#### ** Gelen Kutusu**
Tüm bağlı hesaplarınızdan gelen e-postaların toplandığı yerdir.
* **AI Analizi:** Bir maili açtığınızda, AI içeriği çoktan okumuş ve **taslak bir cevap** hazırlamış olur.
* **Aksiyonlar:** Hazırlanan cevabı "Onayla" diyerek gönderebilir, "Reddet" diyerek negatife çevirebilir veya "Yenile" diyerek baştan yazdırabilirsiniz.

#### **Taslaklar**
Henüz gönderilmemiş, üzerinde çalışılan maillerin tutulduğu alandır.
* **Otomatik Kayıt:** Sistemde yazı yazarken elektrik kesilse bile çalışmalarınız buraya kaydedilir.
* **AI Taslakları:** Yapay zekaya yazdırıp henüz onaylamadığınız mailler burada bekler.

#### **History Geçmiş / Arşiv**
Sistem üzerinden gönderilen tüm e-postaların kaydıdır. Hangi mailin, hangi hesaptan, ne zaman ve kime gönderildiğini buradan raporlayabilirsiniz.

---

### AI YÖNETİM

#### **Rehber & Şirketler**
Yapay zekanın "bağlamı" anlaması için kullanılan veritabanıdır.
* **Kişiler:** Sık mailleştiğiniz kişileri buraya eklerseniz, AI mail yazarken "Ahmet Bey" diye hitap etmesi gerektiğini bilir.
* **Şirket Bilgisi:** Kendi şirket bilgilerini buraya girerek AI'nın maillerde imza kullanmasını veya şirket adınıza konuşmasını sağlarsınız.

#### **Görevler & Ajanda**
Yapay zeka, gelen mailleri okurken içindeki tarihleri ve işleri yakalar.
* *Örn: "Yarın 14:00'te toplantı yapalım"* diyen bir mail gelirse, sistem bunu otomatik olarak buraya **Görev** olarak ekler.
* Bu sayfadan görevlerinizi takip edebilir ve tamamlandı olarak işaretleyebilirsiniz.

#### **AI Mail Yazarı (Writer)**
Sıfırdan mail oluşturmak için kullanılan en gelişmiş modüldür.
* **Mikrofon** Sağ alttaki butona basarak konuşarak mail yazabilirsiniz.
* **Odaklanma:** Konu satırına tıklayıp konuşursanız konu yazar, içeriğe tıklayıp konuşursanız metin yazar.
* **AI Talimatı:** "Müşteriye nazikçe reddetmemiz gerektiğini söyle" gibi bir emir vererek maili baştan sona AI'ya yazdırabilirsiniz.

---

### SİSTEM

#### **Bağlı Hesaplar**
Uygulamaya birden fazla Gmail hesabı eklemenizi sağlar.
* İş ve kişisel maillerinizi aynı anda yönetebilirsiniz.
* Mail atarken "Gönderen" kısmından istediğiniz hesabı seçebilirsiniz.

#### ** Genel Ayarlar**
Uygulamanın tema (Karanlık/Aydınlık mod), dil ve varsayılan yapay zeka davranışlarını özelleştirebileceğiniz alandır.

#### ** Güvenli Çıkış**
Oturumu sonlandırır ve giriş ekranına yönlendirir.

---

##  İpuçları: Sesli Komutlar
**AI Mail Yazarı** sayfasında mikrofonu kullanırken şu sihirli kelimeleri söyleyerek klavyesiz işlem yapabilirsiniz:

* **"Maili Gönder":** Gönderim onay penceresini açar.
* **"Onayla":** Açılan penceredeki işlemi onaylar.
* **"Temizle":** Yazı alanını komple siler.
* **"Oluştur":** AI talimatını çalıştırır ve taslak üretir.

---

 **Not:** Sistemin verimli çalışması için `application_run.py` dosyası çalışırken terminal penceresini kapatmayın.