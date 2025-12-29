import imaplib
import email
from email.header import decode_header
from email.utils import parseaddr
from datetime import datetime

# Güvenlik ve Veritabanı
from app.core.security import decrypt_password
from app.database import mails_col, contacts_col, users_col, tasks_col

# AI Servisleri
from app.services.mail_classifier import should_reply
from app.services.reply_generator import generate_reply
from app.services.extractor import extract_insights_and_tasks
from app.models.contact_model import create_contact

def process_user_inbox(user):
    """Tek bir kullanıcının gelen kutusunu kontrol eder ve AI ile akıllı analiz yapar"""
    email_user = user["email"]
    print(f"🔍 {email_user} için akıllı kontrol başladı...")
    
    try:
        # Şifre çözme işlemi
        enc_pass = user.get("password") or user.get("encrypted_password")
        if not enc_pass: 
            print(f"{email_user} için şifre bulunamadı.")
            return
        
        email_pass = decrypt_password(enc_pass)
        
        # IMAP Bağlantısı
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(email_user, email_pass)
        mail.select("inbox")

        # Sadece OKUNMAMIŞ mailler (UNSEEN)
        status, messages = mail.search(None, "UNSEEN")
        mail_ids = messages[0].split()

        if not mail_ids:
            print(f"📭 Yeni mail yok: {email_user}")
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

                # Mail Gövdesini (Body) Çekme
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
                
                # 2. Rehber/Branch Kontrolü ve Otomatik Kayıt
                contact = contacts_col.find_one({"email": sender_email})
                tone = contact.get("default_tone", "formal") if contact else "formal"
                
                if not contact:
                    contacts_col.insert_one(create_contact({
                        "email": sender_email, 
                        "name": sender_name if sender_name else sender_email.split("@")[0]
                    }))

                # 3. AI EXTRACTION (Akıllı Analiz)
                print(f"AI Analizi Yapılıyor: {subject}")
                analysis = extract_insights_and_tasks(body)

                # --- Görev Varsa 'tasks' Tablosuna Akıllı Kayıt ---
                if analysis.get('task') and analysis['task'].get('title'):
                    # Eğer AI 'is_proposal' (Teklif/Soru) dediyse WAITING_APPROVAL, 
                    # Kesin bir bilgi dediyse doğrudan CONFIRMED olarak kaydediyoruz.
                    status = "WAITING_APPROVAL" if analysis.get('is_proposal') else "CONFIRMED"
                    
                    tasks_col.insert_one({
                        "user_email": email_user,
                        "title": analysis['task']['title'],
                        "due_date": analysis['task'].get('date'),
                        "sender": sender_email,
                        "status": status,
                        "is_approved": not analysis.get('is_proposal'),
                        "created_at": datetime.utcnow()
                    })
                    print(f"Yeni İş/Teklif Kaydedildi ({status}): {analysis['task']['title']}")

                # --- Yeni Bilgi Varsa 'contacts' Notlarına Yaz ---
                if analysis.get('insight'):
                    contacts_col.update_one(
                        {"email": sender_email},
                        {"$push": {"ai_notes": analysis['insight']}}
                    )
                    print(f"Şirket Hafızası Güncellendi: {sender_email}")

                # 4. Ana Mail Kaydı
                mail_doc = {
                    "user_email": email_user,
                    "from": sender_email,
                    "subject": subject,
                    "body": body,
                    "status": "WAITING_APPROVAL" if classify_result["should_reply"] else "IGNORED",
                    "classifier": classify_result,
                    "created_at": datetime.utcnow()
                }

                if classify_result["should_reply"]:
                    mail_doc["reply_draft"] = generate_reply(body, tone=tone)
                
                mails_col.insert_one(mail_doc)
                print(f"Mail Arşivlendi: {subject}")

            except Exception as e:
                print(f"Mail işleme hatası: {e}")
        
        mail.logout()
    except Exception as e:
        print(f" IMAP Bağlantı Hatası: {e}")

def check_all_inboxes():
    """Tüm aktif kullanıcıların kutularını tarar"""
    for user in users_col.find({"is_active": True}):
        process_user_inbox(user)