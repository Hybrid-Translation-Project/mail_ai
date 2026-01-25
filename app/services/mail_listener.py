import imaplib
import email
from email.header import decode_header
from email.utils import parseaddr
from datetime import datetime
import os
import time
from dotenv import load_dotenv

# Veritabanı Bağlantıları
from app.database import mails_col, contacts_col, users_col, accounts_col, tasks_col

# AI Servisleri
from app.services.mail_classifier import should_reply
from app.services.reply_generator import generate_reply
from app.services.extractor import extract_insights_and_tasks
from app.models.contact_model import create_contact

# Güvenlik
from app.core.security import decrypt_password

def decode_mime_words(s):
    return u''.join(
        word.decode(encoding or 'utf-8') if isinstance(word, bytes) else word
        for word, encoding in decode_header(s)
    )

def process_account_inbox(account):
    """Tek bir HESABIN (Account) gelen kutusunu kontrol eder ve AI ile analiz yapar"""
    
    # 1. KRİTİK: .env dosyasını her döngüde zorla tazele
    load_dotenv(override=True) 
    
    email_user = account.get("email")
    print(f"🔍 {email_user} hesabı kontrol ediliyor...")
    
    try:
        # Şifre çekme (Accounts tablosundan)
        enc_pass = account.get("password")
        
        if not enc_pass: 
            print(f"❌ {email_user} için veritabanında şifre bulunamadı.")
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
        
        # IMAP Bağlantısı (Şimdilik Gmail - İleride Provider'a göre değişebilir)
        host = "imap.gmail.com" # Varsayılan
        if account.get("provider") == "outlook": host = "outlook.office365.com" # Örnek
        
        mail = imaplib.IMAP4_SSL(host)
        try:
            mail.login(email_user, email_pass)
        except imaplib.IMAPAuthenticationError:
            print(f"⛔ Giriş Başarısız: {email_user} (Şifre Yanlış veya İzin Yok)")
            return

        mail.select("inbox")

        # Sadece OKUNMAMIŞ mailler (UNSEEN)
        status, messages = mail.search(None, "UNSEEN")
        mail_ids = messages[0].split()

        if not mail_ids:
            # print(f"📭 Yeni mail yok: {email_user}") # Log kirliliği yapmasın diye kapalı
            mail.logout()
            return 

        print(f"📬 {email_user}: {len(mail_ids)} Yeni Mail Bulundu!")

        for mail_id in mail_ids:
            try:
                _, msg_data = mail.fetch(mail_id, "(RFC822)")
                msg = email.message_from_bytes(msg_data[0][1])

                # Başlık ve Gönderen Bilgileri
                subject = decode_mime_words(msg["Subject"] or "")
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

                # Çifte Kayıt Kontrolü (Aynı mail tekrar işlenmesin)
                exists = mails_col.find_one({
                    "subject": subject, 
                    "user_email": email_user, 
                    "created_at": {"$gte": datetime.now().replace(hour=0, minute=0, second=0)}
                })
                
                if exists:
                    continue

                # 1. AI Sınıflandırma (Cevap verilmeli mi?)
                classify_result = should_reply(body)
                
                # 2. Rehber Kontrolü
                contact = contacts_col.find_one({"email": sender_email})
                tone = contact.get("default_tone", "formal") if contact else "formal"
                
                if not contact:
                    # GÜNCELLEME BURADA YAPILDI: owner_account eklendi
                    contacts_col.insert_one(create_contact({
                        "email": sender_email, 
                        "name": sender_name if sender_name else sender_email.split("@")[0],
                        "owner_account": email_user  # <-- KİŞİ HANGİ HESABA BAĞLI?
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

                # 4. Ana Mail Kaydı
                mail_doc = {
                    "user_email": email_user, # Hangi hesaba geldi? (ÇOK ÖNEMLİ)
                    "account_id": str(account["_id"]), # Hesabın ID'si
                    "from": sender_email,
                    "subject": subject,
                    "body": body,
                    "category": analysis.get('category', 'Diğer'),
                    "urgency_score": analysis.get('urgency_score', 0),
                    "status": "WAITING_APPROVAL", 
                    "classifier": classify_result,
                    "extracted_task": analysis.get('task') if analysis.get('task') else None,
                    "created_at": datetime.utcnow()
                }

                # Taslak cevabı oluştur
                if classify_result["should_reply"]:
                    mail_doc["reply_draft"] = generate_reply(body, tone=tone)
                else:
                    mail_doc["reply_draft"] = "AI bu mail için otomatik cevap gerekmediğini düşündü."
                
                mails_col.insert_one(mail_doc)
                print(f"📥 Mail Kaydedildi: {subject} -> {email_user}")

            except Exception as e:
                print(f"⚠️ Mail işleme hatası: {e}")
        
        mail.logout()
    except Exception as e:
        print(f"🚨 IMAP Genel Hata ({email_user}): {e}")

def check_all_inboxes():
    """Veritabanındaki TÜM aktif hesapları (Accounts) tarar"""
    load_dotenv(override=True)
    
    # 1. Accounts tablosundaki aktif hesapları çek
    active_accounts = list(accounts_col.find({"is_active": True}))
    
    # 2. Eğer hiç hesap yoksa ama Users tablosunda eski kullanıcı varsa (Migration Desteği)
    if not active_accounts:
        active_users = list(users_col.find({"is_active": True}))
        if active_users:
            print("ℹ️ Accounts tablosu boş, eski User tablosuna bakılıyor...")
            for user in active_users:
                # Eski kullanıcı yapısını geçici olarak 'account' objesine çevirip işliyoruz
                temp_account = {
                    "_id": user["_id"],
                    "email": user["email"],
                    "password": user["app_password"],
                    "provider": "gmail"
                }
                process_account_inbox(temp_account)
            return

    if not active_accounts:
        print("ℹ️ Hiç aktif hesap bulunamadı, kurulum bekleniyor...")
        return

    # 3. Her hesabı tek tek işle
    print(f"🔄 Toplam {len(active_accounts)} hesap taranıyor...")
    for account in active_accounts:
        process_account_inbox(account)