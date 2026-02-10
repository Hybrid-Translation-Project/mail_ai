import imaplib
import email
from email.header import decode_header
from email.utils import parseaddr
from datetime import datetime, timedelta
import os
import base64
import re
import time
from dotenv import load_dotenv

# Veritabanı Bağlantıları
from app.database import mails_col, contacts_col, users_col, accounts_col, tasks_col, tags_col

# Modeller
from app.models.contact_model import create_contact

# AI Servisleri
from app.services.mail_classifier import should_reply
from app.services.reply_generator import generate_reply
from app.services.extractor import extract_insights_and_tasks

# --- ÖZELLİK 1: OCR (DOSYA OKUMA) SERVİSİ ---
try:
    from app.services.ocr_service import analyze_attachment
except ImportError:
    # Eğer ocr_service.py yoksa veya hata verirse sistem çökmesin, boş dönsün.
    def analyze_attachment(filename, file_bytes): return ""
# --------------------------------------------

# --- ÖZELLİK 2: VEKTÖR (RAG) ---
try:
    from app.rag.embeddings import get_embedding
except ImportError:
    def get_embedding(text): return []
# -------------------------------

# Güvenlik
from app.core.security import decrypt_password

# --- ÖZELLİK 3: İLİŞKİ PUANI HESAPLAYICI ---
def calculate_new_score(current_score, mail_body, last_contact_date=None):
    """
    Kişiyle olan ilişki puanını (0-100) hesaplar.
    Sıklık (Frequency) ve İçerik (Sentiment) analizi yapar.
    """
    score_change = 0
    text = mail_body.lower()
    
    # 1. SIKLIK ANALİZİ
    if last_contact_date:
        delta = datetime.utcnow() - last_contact_date
        if delta.days < 2:
            score_change += 5  # Sıcak Temas
        elif delta.days < 7:
            score_change += 3  # Haftalık Rutin
        else:
            score_change += 1  # Standart
    else:
        score_change += 2 # Başlangıç

    # 2. İÇERİK ANALİZİ
    positive_keywords = ["teşekkür", "sağol", "onay", "tamamdır", "thanks", "great", "ok", "yes", "süper"]
    if any(word in text for word in positive_keywords):
        score_change += 2 
        
    negative_keywords = ["iptal", "hata", "sorun", "yanlış", "cancel", "error", "bad", "fail"]
    if any(word in text for word in negative_keywords):
        score_change -= 2

    # Yeni skoru hesapla ve sınırları koru (0-100)
    return max(0, min(100, current_score + score_change))
# ---------------------------------------------

def _normalize_mid(value: str) -> str:
    return (value or "").strip().strip("<>").strip()

def _mid_variants(value: str) -> list:
    clean = _normalize_mid(value)
    if not clean: return []
    variants = {value.strip(), clean, f"<{clean}>"}
    return [v for v in variants if v]

def _find_mail_by_message_id(message_id: str):
    mids = _mid_variants(message_id)
    if not mids: return None
    return mails_col.find_one({"message_id": {"$in": mids}})

def _find_thread_tags(in_reply_to: str, references: list) -> list:
    refs = references or []
    if isinstance(refs, str): refs = refs.split()
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
            continue
    return []

def decode_mime_words(s):
    return u''.join(
        word.decode(encoding or 'utf-8') if isinstance(word, bytes) else word
        for word, encoding in decode_header(s)
    )

def process_account_inbox(account):
    """Tek bir HESABIN (Account) gelen kutusunu kontrol eder"""
    
    load_dotenv(override=True) 
    
    email_user = account.get("email")
    print(f"🔍 {email_user} hesabı kontrol ediliyor...")
    
    try:
        # Şifre İşlemleri
        enc_pass = account.get("password")
        if not enc_pass: return
        try:
            if not os.getenv("ENCRYPTION_KEY"):
                print("🚨 KRİTİK: .env dosyasında ENCRYPTION_KEY eksik!")
                return
            email_pass = decrypt_password(enc_pass)
        except Exception as e:
            print(f"❌ Şifre çözme hatası ({email_user}): {e}")
            return
        
        # IMAP Bağlantısı
        host = "imap.gmail.com"
        if "outlook" in account.get("provider", ""): host = "outlook.office365.com"
        
        mail = imaplib.IMAP4_SSL(host)
        try:
            mail.login(email_user, email_pass)
        except imaplib.IMAPAuthenticationError:
            print(f"⛔ Giriş Başarısız: {email_user}")
            return

        mail.select("inbox")
        status, messages = mail.search(None, "UNSEEN")
        mail_ids = messages[0].split()

        if not mail_ids:
            mail.logout()
            return 

        print(f"📬 {email_user}: {len(mail_ids)} Yeni Mail Bulundu!")

        for mail_id in mail_ids:
            try:
                _, msg_data = mail.fetch(mail_id, "(RFC822)")
                msg = email.message_from_bytes(msg_data[0][1])

                subject = decode_mime_words(msg["Subject"] or "")
                sender_name, sender_email = parseaddr(msg.get("From"))
                
                # Kendine gönderilenleri atla
                if sender_email.lower() == email_user.lower(): continue
                
                message_id = msg.get("Message-ID", "").strip()
                if not message_id:
                      import uuid
                      message_id = f"gen-{uuid.uuid4()}"

                in_reply_to = (msg.get("In-Reply-To") or "").strip()
                references_header = msg.get("References") or ""
                references = references_header.split() if references_header else []

                # --- İÇERİK PARSE ETME & OCR ---
                body_text = ""
                body_html = ""
                cid_map = {} 
                attachments = []
                ocr_text_content = "" # Eklerden okunan metinler buraya

                if msg.is_multipart():
                    for part in msg.walk():
                        ctype = part.get_content_type()
                        cdisp = str(part.get("Content-Disposition"))
                        content_id = part.get("Content-ID")
                        filename = part.get_filename()
                        
                        try: part_data = part.get_payload(decode=True)
                        except: part_data = None
                        
                        if not part_data: continue

                        # 1. Metin Kısımları
                        if ctype == "text/plain" and "attachment" not in cdisp:
                            body_text += part_data.decode(errors="ignore")
                        elif ctype == "text/html" and "attachment" not in cdisp:
                            body_html += part_data.decode(errors="ignore")

                        # 2. Inline Resimler (CID)
                        if content_id and ctype.startswith("image/"):
                            clean_cid = content_id.strip("<> ")
                            if clean_cid:
                                stream_url = f"/ui/stream/{message_id}/{clean_cid}"
                                cid_map[clean_cid] = stream_url

                        # 3. Dosya Ekleri ve OCR
                        if "attachment" in cdisp or filename:
                            if filename:
                                try:
                                    filename = decode_mime_words(filename)
                                    
                                    # --- OCR İŞLEMİ ---
                                    # PDF veya Resim ise metni okumayı dene
                                    extracted_text = analyze_attachment(filename, part_data)
                                    if extracted_text:
                                        ocr_text_content += f"\n\n--- [EK DOSYA OKUNDU: {filename}] ---\n{extracted_text}\n---------------------------------------\n"
                                    # ------------------

                                    attachments.append({
                                        "filename": filename,
                                        "content_type": ctype,
                                        "size": len(part_data),
                                        "url": f"/ui/download/{message_id}/{filename}"
                                    })
                                except Exception as e:
                                    print(f"Attachment error: {e}")

                else:
                    try: 
                        payload = msg.get_payload(decode=True).decode(errors="ignore")
                        if msg.get_content_type() == "text/html": body_html = payload
                        else: body_text = payload
                    except: pass

                if body_html and cid_map:
                    for cid, stream_url in cid_map.items():
                        body_html = body_html.replace(f"cid:{cid}", stream_url)

                body = body_text.strip()
                if not body and body_html:
                    body = re.sub('<[^<]+?>', '', body_html).strip()

                # --- AI İÇİN TAM METİN (Gövde + OCR) ---
                full_body_for_ai = body + ocr_text_content
                # ---------------------------------------

                # Çifte Kayıt Kontrolü
                exists = mails_col.find_one({"message_id": message_id})
                if exists: continue

                # 1. AI Sınıflandırma
                classify_result = should_reply(full_body_for_ai)
                
                # 2. Rehber ve İlişki Puanı Güncelleme
                contact = contacts_col.find_one({"email": sender_email})
                now = datetime.utcnow()
                
                if not contact:
                    # Yeni Kişi
                    new_score = calculate_new_score(50, full_body_for_ai, None)
                    new_contact_doc = create_contact({
                        "email": sender_email, 
                        "name": sender_name if sender_name else sender_email.split("@")[0],
                        "owner_account": email_user,
                        "mail_count": 1,
                        "relationship_score": new_score
                    })
                    new_contact_doc["last_contact_at"] = now
                    contacts_col.insert_one(new_contact_doc)
                    tone = "formal"
                else:
                    # Eski Kişi
                    current_score = contact.get("relationship_score", 50)
                    last_date = contact.get("last_contact_at")
                    new_score = calculate_new_score(current_score, full_body_for_ai, last_date)
                    tone = contact.get("default_tone", "formal")
                    
                    contacts_col.update_one(
                        {"email": sender_email},
                        {
                            "$set": {"relationship_score": new_score, "last_contact_at": now},
                            "$inc": {"mail_count": 1}
                        }
                    )

                # 3. Detaylı AI Analizi
                print(f"🤖 AI Analizi (OCR Dahil): {subject}")
                available_tags = list(tags_col.find({}, {"_id": 0, "slug": 1, "description": 1}))
                analysis = extract_insights_and_tasks(full_body_for_ai, available_tags=available_tags)
                
                thread_tags = _find_thread_tags(in_reply_to, references)
                analysis_tags = analysis.get("tags", []) if isinstance(analysis.get("tags", []), list) else []
                tags_for_mail = thread_tags if thread_tags else analysis_tags

                if analysis.get('insight'):
                    contacts_col.update_one(
                        {"email": sender_email},
                        {"$push": {"ai_notes": analysis['insight']}}
                    )
                
                # 4. Vektör Oluşturma
                full_text_for_vector = f"{subject} {full_body_for_ai}"
                vector_embedding = get_embedding(full_text_for_vector)

                # 5. Ana Mail Kaydı
                mail_doc = {
                    "message_id": message_id,
                    "in_reply_to": in_reply_to,
                    "references": references,
                    "user_email": email_user,
                    "account_id": str(account["_id"]),
                    "from": sender_email,
                    "subject": subject,
                    "subject_normalized": subject.lower(),
                    "body": full_body_for_ai, # EKLER DAHİL KAYDEDİYORUZ
                    "body_html": body_html if body_html else body,
                    "category": analysis.get('category', 'Diğer'),
                    "urgency_score": analysis.get('urgency_score', 0),
                    "tags": tags_for_mail,
                    "status": "WAITING_APPROVAL", 
                    "classifier": classify_result,
                    "extracted_task": analysis.get('task') if analysis.get('task') else None,
                    "created_at": datetime.utcnow(),
                    "attachments": attachments,
                    "embedding": vector_embedding 
                }

                if classify_result["should_reply"]:
                    mail_doc["reply_draft"] = generate_reply(full_body_for_ai, tone=tone)
                else:
                    mail_doc["reply_draft"] = "AI bu mail için otomatik cevap gerekmediğini düşündü."
                
                mails_col.insert_one(mail_doc)
                print(f"📥 Mail Kaydedildi: {subject}")

                # --- ÖZELLİK 4: TAKİP SİSTEMİ (FOLLOW-UP) ---
                if in_reply_to:
                    clean_irt = _normalize_mid(in_reply_to)
                    if clean_irt:
                        mails_col.update_one(
                            {"message_id": {"$regex": re.escape(clean_irt)}, "type": "outbound"},
                            {"$set": {"has_reply": True, "last_reply_at": datetime.utcnow()}}
                        )
                # --------------------------------------------

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
        # User tablosuna fallback (Eski sürüm uyumluluğu)
        active_users = list(users_col.find({"is_active": True}))
        if active_users:
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