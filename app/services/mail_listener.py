import imaplib
import email
from email.header import decode_header
from email.utils import parseaddr, parsedate_to_datetime
from datetime import datetime, timezone, timedelta  # timedelta eklendi

# Güvenlik modülü
from app.core.security import decrypt_password

# Veritabanı bağlantıları
from app.database import mails_col, contacts_col, users_col

# AI Servisleri
from app.services.mail_classifier import should_reply
from app.services.reply_generator import generate_reply
from app.models.contact_model import create_contact

def process_user_inbox(user):
    """Tek bir kullanıcının gelen kutusunu kontrol eder"""
    email_user = user["email"]
    
    try:
        #  Şifreyi Çöz
        encrypted_pass = user.get("encrypted_password")
        if not encrypted_pass:
            return

        email_pass = decrypt_password(encrypted_pass)
        
        # IMAP Bağlantısı (Gmail)
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(email_user, email_pass)
        mail.select("inbox")

        #Sadece Okunmamış (UNSEEN) Mailleri Al
        status, messages = mail.search(None, "UNSEEN")
        mail_ids = messages[0].split()

        if not mail_ids:
            return 

        print(f"[{email_user}] {len(mail_ids)} adet okunmamış mail bulundu, tarihleri kontrol ediliyor...")

        for mail_id in mail_ids:
            try:
                # Sadece Başlıkları (Header) Çek 
                _, msg_data = mail.fetch(mail_id, "(BODY.PEEK[HEADER])")
                raw_email = msg_data[0][1]
                msg = email.message_from_bytes(raw_email)

                # Tarih Kontrolü (SON 3 GÜN KURALI) 
                mail_date_header = msg.get("Date")
                should_process = True # Varsayılan olarak işle

                if mail_date_header:
                    try:
                        mail_dt = parsedate_to_datetime(mail_date_header)
                        
                        # Zaman dilimi yoksa UTC kabul et
                        if mail_dt.tzinfo is None:
                            mail_dt = mail_dt.replace(tzinfo=timezone.utc)
                        
                        # Şu anki zaman 
                        now_utc = datetime.now(timezone.utc)
                        
                        # Bugünden 3 gün öncesi
                        cutoff_date = now_utc - timedelta(days=3)

                        # Eğer mail eşik tarihten daha eskiyse -> ESKİDİR
                        if mail_dt < cutoff_date:  
                            # Bunu okundu işaretle (Seen) ki tekrar karşıma çıkmasın
                            mail.store(mail_id, '+FLAGS', '\\Seen')
                            should_process = False
                    except Exception as e_date:
                        print(f" Tarih okuma hatası: {e_date}, mail işleniyor...")

                if not should_process:
                    continue


                _, msg_data = mail.fetch(mail_id, "(RFC822)")
                raw_email = msg_data[0][1]
                msg = email.message_from_bytes(raw_email)

                # Konuyu (Subject) Çöz
                subject_bytes, encoding = decode_header(msg["Subject"])[0]
                if isinstance(subject_bytes, bytes):
                    subject = subject_bytes.decode(encoding if encoding else "utf-8")
                else:
                    subject = subject_bytes
                
                sender_header = msg.get("From")
                sender_name, sender_email = parseaddr(sender_header)

                # Mail Gövdesini (Body) Al
                body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            body = part.get_payload(decode=True).decode(errors="ignore")
                            break
                else:
                    body = msg.get_payload(decode=True).decode(errors="ignore")

                #Kişi Tanıma
                contact = contacts_col.find_one({"email": sender_email})
                if contact:
                    user_tone = contact.get("default_tone", "formal")
                else:
                    contacts_col.insert_one(create_contact({
                        "email": sender_email,
                        "name": sender_name if sender_name else sender_email.split("@")[0],
                        "default_tone": "formal"
                    }))
                    user_tone = "formal"

                # AI Analizi
                classify_result = should_reply(body)

                if not classify_result["should_reply"]:
                    mails_col.insert_one({
                        "user_email": email_user,
                        "from": sender_email,
                        "subject": subject,
                        "body": body,
                        "status": "IGNORED",
                        "classifier": classify_result,
                        "created_at": datetime.utcnow()
                    })
                    print(f"IGNORED: {subject}")
                    continue

                draft_reply = generate_reply(body, tone=user_tone)
                
                mails_col.insert_one({
                    "user_email": email_user,
                    "from": sender_email,
                    "subject": subject,
                    "body": body,
                    "reply_draft": draft_reply,
                    "status": "WAITING_APPROVAL",
                    "classifier": classify_result,
                    "created_at": datetime.utcnow()
                })
                print(f"ONAY BEKLİYOR: {subject}")

            except Exception as e_inner:
                print(f"Mail işleme hatası: {e_inner}")

        mail.logout()
    except Exception as e:
        print(f"IMAP Hatası ({email_user}): {e}")

def check_all_inboxes():
    try:
        active_users = list(users_col.find({"is_active": True}))
        if not active_users:
            return
        for user in active_users:
            process_user_inbox(user)     
    except Exception as e:
        print(f"Döngü hatası: {e}")