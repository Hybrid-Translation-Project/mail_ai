import imaplib
import email
from email.header import decode_header
from email.utils import parseaddr
from datetime import datetime
from app.core.security import decrypt_password
from app.database import mails_col, contacts_col, users_col
from app.services.mail_classifier import should_reply
from app.services.reply_generator import generate_reply
from app.models.contact_model import create_contact

def process_user_inbox(user):
    email_user = user["email"]
    print(f"🔍 {email_user} için kontrol ediliyor...")
    
    try:
        # Şifreyi al ve çöz
        enc_pass = user.get("password") or user.get("encrypted_password")
        if not enc_pass: return
        
        email_pass = decrypt_password(enc_pass)
        
        # Bağlantı
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(email_user, email_pass)
        mail.select("inbox")

        # Sadece OKUNMAMIŞLAR
        status, messages = mail.search(None, "UNSEEN")
        mail_ids = messages[0].split()

        if not mail_ids:
            print(f"📭 Yeni mail yok: {email_user}")
            return 

        for mail_id in mail_ids:
            try:
                _, msg_data = mail.fetch(mail_id, "(RFC822)")
                msg = email.message_from_bytes(msg_data[0][1])

                # Konu ve Gönderen
                subject = decode_header(msg["Subject"])[0][0]
                if isinstance(subject, bytes): subject = subject.decode()
                sender_name, sender_email = parseaddr(msg.get("From"))

                # Body Çekme
                body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            body = part.get_payload(decode=True).decode(errors="ignore")
                            break
                else:
                    body = msg.get_payload(decode=True).decode(errors="ignore")

                # Kayıt ve Analiz
                classify_result = should_reply(body)
                
                # Rehber Kontrolü
                contact = contacts_col.find_one({"email": sender_email})
                tone = contact.get("default_tone", "formal") if contact else "formal"
                if not contact:
                    contacts_col.insert_one(create_contact({"email": sender_email, "name": sender_name}))

                # MongoDB'ye Ekle
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
                print(f"İşlendi: {subject}")

            except Exception as e:
                print(f"Mail hatası: {e}")
        
        mail.logout()
    except Exception as e:
        print(f"IMAP Hatası: {e}")

def check_all_inboxes():
    for user in users_col.find({"is_active": True}):
        process_user_inbox(user)