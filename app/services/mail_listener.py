import imaplib
import email
from email.header import decode_header
from email.utils import parseaddr
from datetime import datetime
import os
import time
from dotenv import load_dotenv

# Veritabanı Bağlantıları
from app.database import mails_col, contacts_col, users_col, tasks_col

# AI Servisleri
from app.services.mail_classifier import should_reply
from app.services.reply_generator import generate_reply
from app.services.extractor import extract_insights_and_tasks
from app.models.contact_model import create_contact

def process_user_inbox(user):
    """Tek bir kullanıcının gelen kutusunu kontrol eder ve AI ile analiz yapar"""
    
    # 1. KRİTİK: .env dosyasını her döngüde zorla tazele
    load_dotenv(override=True) 
    
    # 2. KRİTİK: Güvenlik modülünü burada çağırıyoruz ki taze anahtarı görsün
    from app.core.security import decrypt_password 
    
    email_user = user.get("email")
    print(f"🔍 {email_user} için akıllı kontrol başladı...")
    
    try:
        # Şifre çekme
        enc_pass = user.get("app_password")
        
        if not enc_pass: 
            print(f"❌ {email_user} için veritabanında şifrelenmiş şifre bulunamadı.")
            return
        
        # Şifreyi çözüyoruz
        try:
            if not os.getenv("ENCRYPTION_KEY"):
                print("🚨 KRİTİK HATA: .env dosyasında ENCRYPTION_KEY hala eksik!")
                return
            
            email_pass = decrypt_password(enc_pass)
        except Exception as e:
            print(f"❌ Şifre çözme hatası ({email_user}): Anahtar uyuşmazlığı. {e}")
            return
        
        # IMAP Bağlantısı
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(email_user, email_pass)
        mail.select("inbox")

        # Sadece OKUNMAMIŞ mailler (UNSEEN)
        status, messages = mail.search(None, "UNSEEN")
        mail_ids = messages[0].split()

        if not mail_ids:
            print(f"📭 Yeni mail yok: {email_user}")
            mail.logout()
            return 

        for mail_id in mail_ids:
            try:
                _, msg_data = mail.fetch(mail_id, "(RFC822)")
                msg = email.message_from_bytes(msg_data[0][1])

                # Başlık ve Gönderen Bilgileri
                subject_header = decode_header(msg["Subject"])[0]
                subject = subject_header[0]
                if isinstance(subject, bytes):
                    subject = subject.decode(subject_header[1] if subject_header[1] else "utf-8")
                
                sender_name, sender_email = parseaddr(msg.get("From"))

                # Mail Gövdesini Çekme
                body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            body = part.get_payload(decode=True).decode(errors="ignore")
                            break
                else:
                    body = msg.get_payload(decode=True).decode(errors="ignore")

                # 1. AI Sınıflandırma (Cevap verilmeli mi?)
                classify_result = should_reply(body)
                
                # 2. Rehber Kontrolü
                contact = contacts_col.find_one({"email": sender_email})
                tone = contact.get("default_tone", "formal") if contact else "formal"
                
                if not contact:
                    contacts_col.insert_one(create_contact({
                        "email": sender_email, 
                        "name": sender_name if sender_name else sender_email.split("@")[0]
                    }))

                # 3. AI Analizi (Görev ve İçgörü Çıkarımı)
                print(f"🤖 AI Analizi Yapılıyor: {subject}")
                analysis = extract_insights_and_tasks(body)

                # --- Şirket Hafızası Güncelleme ---
                if analysis.get('insight'):
                    contacts_col.update_one(
                        {"email": sender_email},
                        {"$push": {"ai_notes": analysis['insight']}}
                    )

                # 4. Ana Mail Kaydı [DÜZENLENDİ: Görev direkt eklenmiyor, buraya saklanıyor]
                mail_doc = {
                    "user_email": email_user,
                    "from": sender_email,
                    "subject": subject,
                    "body": body,
                    "category": analysis.get('category', 'Diğer'),
                    "urgency_score": analysis.get('urgency_score', 0),
                    "status": "WAITING_APPROVAL", # Onay mekanizması için statik başlattık
                    "classifier": classify_result,
                    # ÖNEMLİ: AI'nın bulduğu görev bilgisini buraya gömdük
                    "extracted_task": analysis.get('task') if analysis.get('task') else None,
                    "created_at": datetime.utcnow()
                }

                # Taslak cevabı oluştur
                if classify_result["should_reply"]:
                    mail_doc["reply_draft"] = generate_reply(body, tone=tone)
                else:
                    # Cevap gerekmese bile AI'dan bir taslak üretilebilir veya boş bırakılabilir
                    mail_doc["reply_draft"] = "AI bu mail için otomatik cevap gerekmediğini düşündü."
                
                mails_col.insert_one(mail_doc)
                print(f"📥 Mail Gelen Kutusu'na Düştü (Onay Bekliyor): {subject}")

            except Exception as e:
                print(f"⚠️ Tekil mail işleme hatası: {e}")
        
        mail.logout()
    except Exception as e:
        print(f"🚨 IMAP Bağlantı Hatası ({email_user}): {e}")

def check_all_inboxes():
    """Tüm aktif kullanıcıların kutularını tarar"""
    load_dotenv(override=True)
    
    active_users = list(users_col.find({"is_active": True}))
    if not active_users:
        print("ℹ️ Aktif kullanıcı bulunamadı, kurulum bekleniyor...")
        return

    for user in active_users:
        process_user_inbox(user)