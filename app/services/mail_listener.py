import imaplib
import email
from email.header import decode_header
from email.utils import parseaddr
from datetime import datetime
import os
import base64
import re
import time
from dotenv import load_dotenv

# Veritabanı Bağlantıları
from app.database import mails_col, contacts_col, users_col, accounts_col, tasks_col, tags_col

# AI Servisleri
from app.services.mail_classifier import should_reply
from app.services.reply_generator import generate_reply
from app.services.extractor import extract_insights_and_tasks
from app.models.contact_model import create_contact

# YENİ EKLENEN: Semantik Arama İçin Vektör Motoru
try:
    from app.rag.embeddings import get_embedding
except ImportError:
    # Eğer model henüz inmemişse hata vermesin, boş liste dönsün
    def get_embedding(text): return []

# Güvenlik
from app.core.security import decrypt_password

def _normalize_mid(value: str) -> str:
    return (value or "").strip().strip("<>").strip()

def _mid_variants(value: str) -> list:
    clean = _normalize_mid(value)
    if not clean:
        return []
    variants = {value.strip(), clean, f"<{clean}>"}
    return [v for v in variants if v]

def _find_mail_by_message_id(message_id: str):
    mids = _mid_variants(message_id)
    if not mids:
        return None
    return mails_col.find_one({"message_id": {"$in": mids}})

def _find_thread_tags(in_reply_to: str, references: list) -> list:
    """
    Thread'e bağlı yeni bir mail gelirse, zincirin tag'lerini sabitlemek için
    daha önce kaydedilmiş bir parent/root mailin tag'lerini döndürür.
    """
    refs = references or []
    if isinstance(refs, str):
        refs = refs.split()

    # Öncelik: root (References[0]) -> son referans -> In-Reply-To
    candidates = []
    if refs:
        candidates.append(refs[0])
        candidates.append(refs[-1])
    if in_reply_to:
        candidates.append(in_reply_to)

    for mid in candidates:
        parent = _find_mail_by_message_id(str(mid))
        if parent and isinstance(parent.get("tags"), list) and parent["tags"]:
            return parent["tags"]
        if parent and "tags" in parent and isinstance(parent.get("tags"), list):
            # parent var ama tags boş ise, boş liste döndürmeyelim; aramaya devam edelim
            continue
    return []

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
                
                # KENDİNE GÖNDERİLEN MAİLLERİ ATLA
                if sender_email.lower() == email_user.lower():
                    print(f"⏭️ Kendine gönderilen mail, Sent Listener'a bırakılıyor: {subject}")
                    continue
                
                message_id = msg.get("Message-ID", "").strip() # Message-ID çekiyoruz

                # Eğer Message-ID yoksa (çok nadir), benzersiz bir ID üretelim
                if not message_id:
                     import uuid
                     message_id = f"gen-{uuid.uuid4()}"

                # Threading header'ları (Reply zinciri için kritik)
                in_reply_to = (msg.get("In-Reply-To") or "").strip()
                references_header = msg.get("References") or ""
                references = references_header.split() if references_header else []

                # --- Gelişmiş Parsing (Stream Destekli - HIZLI MOD) ---
                body_text = ""
                body_html = ""
                cid_map = {} # cid -> stream_url
                attachments = [] # Ek dosyalar (metadata)

                if msg.is_multipart():
                    for part in msg.walk():
                        ctype = part.get_content_type()
                        cdisp = str(part.get("Content-Disposition"))
                        content_id = part.get("Content-ID")
                        
                        # Payload decode (Sadece TEXT ise indir, dosya ise İNDİRME!)
                        try:
                            if ctype.startswith("text/"):
                                part_data = part.get_payload(decode=True)
                                payload = part_data.decode(errors="ignore")
                            else:
                                # HIZ İÇİN: Dosya içeriğini belleğe alma!
                                part_data = None 
                                payload = ""
                        except:
                            part_data = None
                            payload = ""

                        # 1. INLINE RESİMLER (CID) -> STREAM URL
                        # Base64 YERİNE sadece stream linki oluşturuyoruz
                        if content_id and ctype.startswith("image/"):
                            clean_cid = content_id.strip("<> ")
                            if clean_cid:
                                # Bu link, ui.py'de yapacağımız yönlendirme ile anlık çalışacak
                                stream_url = f"/ui/stream/{message_id}/{clean_cid}"
                                cid_map[clean_cid] = stream_url

                        # 2. ATTACHMENTS (EK DOSYALAR) -> DOWNLOAD LINK
                        # Dosyayı indirmiyoruz, sadece varlığını kaydediyoruz
                        if "attachment" in cdisp or part.get_filename():
                            filename = part.get_filename()
                            if filename:
                                try:
                                    filename = decode_mime_words(filename)
                                    # Buraya dikkat: Base64 yok! Dosya verisi yok!
                                    attachments.append({
                                        "filename": filename,
                                        "content_type": ctype,
                                        "size": 0, # Hız için 0 bırakıyoruz, istenirse headerdan okunabilir
                                        "url": f"/ui/download/{message_id}/{filename}" # İndirme linki
                                    })
                                except Exception as e:
                                    print(f"Attachment parse error: {e}")

                        if ctype == "text/plain" and "attachment" not in cdisp:
                            body_text += payload
                        elif ctype == "text/html" and "attachment" not in cdisp:
                            body_html += payload
                else:
                    # Tek parça
                    try: 
                        payload = msg.get_payload(decode=True).decode(errors="ignore")
                        if msg.get_content_type() == "text/html":
                            body_html = payload
                        else:
                            body_text = payload
                    except:
                        pass

                # HTML içindeki cid referanslarını Stream URL ile değiştir
                if body_html and cid_map:
                    for cid, stream_url in cid_map.items():
                        # src="cid:..." -> src="/ui/stream/..."
                        body_html = body_html.replace(f"cid:{cid}", stream_url)

                # AI ve Özet için temiz metin
                body = body_text.strip()
                if not body and body_html:
                    body = re.sub('<[^<]+?>', '', body_html).strip()

                # Çifte Kayıt Kontrolü
                exists = mails_col.find_one({"message_id": message_id})
                if exists:
                    print(f"⚠️ Mail zaten kayıtlı (ID: {message_id}), atlanıyor.")
                    continue

                # 1. AI Sınıflandırma
                classify_result = should_reply(body)
                
                # 2. Rehber Kontrolü
                contact = contacts_col.find_one({"email": sender_email})
                tone = contact.get("default_tone", "formal") if contact else "formal"
                
                if not contact:
                    contacts_col.insert_one(create_contact({
                        "email": sender_email, 
                        "name": sender_name if sender_name else sender_email.split("@")[0],
                        "owner_account": email_user
                    }))

                # 3. AI Analizi
                print(f"🤖 AI Analizi Yapılıyor: {subject}")
                available_tags = list(tags_col.find({}, {"_id": 0, "slug": 1, "description": 1}))
                analysis = extract_insights_and_tasks(body, available_tags=available_tags)
                
                thread_tags = _find_thread_tags(in_reply_to, references)
                analysis_tags = analysis.get("tags", []) if isinstance(analysis.get("tags", []), list) else []
                tags_for_mail = thread_tags if thread_tags else analysis_tags

                if analysis.get('insight'):
                    contacts_col.update_one(
                        {"email": sender_email},
                        {"$push": {"ai_notes": analysis['insight']}}
                    )
                
                # Vektör Oluşturma
                full_text_for_vector = f"{subject} {body}"
                vector_embedding = get_embedding(full_text_for_vector)

                # 4. Ana Mail Kaydı
                mail_doc = {
                    "message_id": message_id,
                    "in_reply_to": in_reply_to,
                    "references": references,
                    "user_email": email_user,
                    "account_id": str(account["_id"]),
                    "from": sender_email,
                    "subject": subject,
                    "subject_normalized": subject.lower(),
                    "body": body,
                    "body_html": body_html if body_html else body,
                    "category": analysis.get('category', 'Diğer'),
                    "urgency_score": analysis.get('urgency_score', 0),
                    "tags": tags_for_mail,
                    "status": "WAITING_APPROVAL", 
                    "classifier": classify_result,
                    "extracted_task": analysis.get('task') if analysis.get('task') else None,
                    "created_at": datetime.utcnow(),
                    
                    # Ekler (Base64 yok, sadece link var!)
                    "attachments": attachments,
                    
                    "embedding": vector_embedding 
                }

                if classify_result["should_reply"]:
                    mail_doc["reply_draft"] = generate_reply(body, tone=tone)
                else:
                    mail_doc["reply_draft"] = "AI bu mail için otomatik cevap gerekmediğini düşündü."
                
                mails_col.insert_one(mail_doc)
                print(f"📥 Mail Kaydedildi (Stream Modu): {subject} -> {email_user}")

            except Exception as e:
                print(f"⚠️ Mail işleme hatası: {e}")
        
        mail.logout()
    except Exception as e:
        print(f"🚨 IMAP Genel Hata ({email_user}): {e}")

def check_all_inboxes():
    """Veritabanındaki TÜM aktif hesapları (Accounts) tarar"""
    load_dotenv(override=True)
    
    active_accounts = list(accounts_col.find({"is_active": True}))
    
    if not active_accounts:
        active_users = list(users_col.find({"is_active": True}))
        if active_users:
            print("ℹ️ Accounts tablosu boş, eski User tablosuna bakılıyor...")
            for user in active_users:
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

    print(f"🔄 Toplam {len(active_accounts)} hesap taranıyor...")
    for account in active_accounts:
        process_account_inbox(account)