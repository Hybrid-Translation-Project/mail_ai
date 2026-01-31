import imaplib
import email
from email.header import decode_header
from email.utils import parseaddr
from datetime import datetime, timedelta
import os
import re
import base64
import uuid
from dotenv import load_dotenv

# Veritabanı Bağlantıları
from app.database import mails_col, accounts_col, users_col

# Güvenlik
from app.core.security import decrypt_password

# Yardımcı Fonksiyonlar (mail_listener'dan kopyalandı/import edilebilir ama bağımsız olması için buraya da ekliyoruz veya ortak bir utils'e taşımalıyız. Şimdilik buraya ekliyorum)
def decode_mime_words(s):
    return u''.join(
        word.decode(encoding or 'utf-8') if isinstance(word, bytes) else word
        for word, encoding in decode_header(s)
    )

def normalize_subject(subject):
    if not subject: return ""
    s = subject.lower()
    clean_pattern = r'^\s*(?:re|fw|fwd)\s*:\s*'
    while re.match(clean_pattern, s):
        s = re.sub(clean_pattern, '', s)
    return s.strip()

# Embeddings (Opsiyonel)
try:
    from app.rag.embeddings import get_embedding
except ImportError:
    def get_embedding(text): return []

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
    refs = references or []
    if isinstance(refs, str):
        refs = refs.split()

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
    return []


def process_account_sent(account):
    """Giden Kutusunu (Sent) son mailler için kontrol eder"""
    load_dotenv(override=True) 
    
    email_user = account.get("email")
    print(f"📤 {email_user} Sent kutusu kontrol ediliyor...")
    
    try:
        enc_pass = account.get("password")
        if not enc_pass: return
        
        try:
            email_pass = decrypt_password(enc_pass)
        except:
            return

        host = "imap.gmail.com"
        if account.get("provider") == "outlook": host = "outlook.office365.com"
        
        mail = imaplib.IMAP4_SSL(host)
        try:
            mail.login(email_user, email_pass)
        except:
            return

        # Sent Klasörünü Bulmaya Çalış
        selected_folder = None
        all_folders = mail.list()[1]
        
        for f in all_folders:
            f_decoded = f.decode()
            if "\\Sent" in f_decoded or "\\SENT" in f_decoded:
                parts = f_decoded.split(' "/" ')
                if len(parts) > 1:
                    selected_folder = parts[1].strip('"')
                    break
        
        if not selected_folder:
            sent_folders = [
                "[Gmail]/Sent Mail", 
                "Sent Items", "Sent", "Giden Kutusu", 
                "Gönderilmiş Postalar", "[Gmail]/Gönderilmiş Postalar",
                "[Gmail]/G&APY-nderilmi&AV8- Postalar", 
                "&APY-nderilmi&AV8- Postalar"
            ]
            for f in all_folders:
                f_decoded = f.decode()
                for sf in sent_folders:
                    if sf in f_decoded:
                        parts = f_decoded.split(' "/" ')
                        if len(parts) > 1:
                            folder_name = parts[1].strip('"')
                            if sf in folder_name:
                                selected_folder = folder_name
                                break
                if selected_folder: break

        if not selected_folder:
            selected_folder = "[Gmail]/Sent Mail"

        resp, _ = mail.select(f'"{selected_folder}"')
        if resp != 'OK':
            resp, _ = mail.select(selected_folder)
            if resp != 'OK':
                mail.logout()
                return

        # Sadece son 1 günün maillerini getir (Performans için kritik)
        since_date = (datetime.now() - timedelta(days=1)).strftime("%d-%b-%Y")
        status, messages = mail.search(None, f'(SINCE "{since_date}")')
        all_ids = messages[0].split()

        if not all_ids:
            mail.logout()
            return
            
        recent_ids = all_ids[-10:] if len(all_ids) > 10 else all_ids

        for mail_id in recent_ids:
            try:
                # Sadece Headerı çekip DB kontrolü
                _, msg_header = mail.fetch(mail_id, "(BODY.PEEK[HEADER.FIELDS (MESSAGE-ID)])")
                header_txt = msg_header[0][1].decode()
                
                msg_id_match = re.search(r'Message-ID:\s*(<.*?>)', header_txt, re.IGNORECASE)
                message_id = msg_id_match.group(1) if msg_id_match else None

                if message_id:
                     message_id = message_id.strip()
                     exist = mails_col.find_one({"message_id": message_id})
                     if exist:
                         continue 
                
                # Fetch Full
                _, msg_data = mail.fetch(mail_id, "(RFC822)")
                msg = email.message_from_bytes(msg_data[0][1])
                
                if not message_id:
                    message_id = msg.get("Message-ID", "").strip() or f"gen-{uuid.uuid4()}"

                if mails_col.find_one({"message_id": message_id}): continue

                subject = decode_mime_words(msg["Subject"] or "")
                print(f"📤 Sent Mail Eşleşti: {subject}")
                sender_name, sender_email = parseaddr(msg.get("From"))
                
                # --- Gelişmiş Parsing (Stream Destekli) ---
                body_text = ""
                body_html = ""
                cid_map = {}
                attachments = [] # Ek dosyalar (metadata)

                if msg.is_multipart():
                    for part in msg.walk():
                        ctype = part.get_content_type()
                        cdisp = str(part.get("Content-Disposition"))


                        # Content-ID Yakala
                        content_id = part.get("Content-ID")
                        
                        try:
                            part_data = part.get_payload(decode=True)
                            payload = part_data.decode(errors="ignore")
                        except:
                            part_data = None
                            payload = ""

                        # BASE64 EMBEDDING (HIZ İÇİN)
                        if content_id and part_data:
                            clean_cid = content_id.strip("<> ")
                            if clean_cid:
                                try:
                                    b64_str = base64.b64encode(part_data).decode('utf-8')
                                    # data:image/png;base64,....
                                    embed_src = f"data:{ctype};base64,{b64_str}"
                                    cid_map[clean_cid] = embed_src
                                except Exception as e:
                                    print(f"Base64 error: {e}")

                        # ATTACHMENT DETECTION (EK DOSYALAR)
                        if "attachment" in cdisp or part.get_filename():
                            filename = part.get_filename()
                            if filename:
                                try:
                                    filename = decode_mime_words(filename)
                                    file_size = len(part_data) if part_data else 0
                                    
                                    # BASE64 DATA URI (İndirme için)
                                    if part_data:
                                        b64_data = base64.b64encode(part_data).decode('utf-8')
                                        data_uri = f"data:{ctype};base64,{b64_data}"
                                    else:
                                        data_uri = "#"
                                    
                                    attachments.append({
                                        "filename": filename,
                                        "content_type": ctype,
                                        "size": file_size,
                                        "url": data_uri
                                    })
                                except Exception as e:
                                    print(f"Attachment parse error: {e}")

                        if ctype == "text/plain" and "attachment" not in cdisp:
                            body_text += payload
                        elif ctype == "text/html" and "attachment" not in cdisp:
                            body_html += payload
                else:
                    try: 
                        payload = msg.get_payload(decode=True).decode(errors="ignore")
                        if msg.get_content_type() == "text/html": body_html = payload
                        else: body_text = payload
                    except: pass
                
                # CID Replacement
                if body_html and cid_map:
                    for cid, url in cid_map.items():
                        body_html = body_html.replace(f"cid:{cid}", url)

                if not body_text and body_html:
                    body_text = re.sub('<[^<]+?>', '', body_html)
                
                vector_embedding = []
                try: 
                     vector_embedding = get_embedding(f"{subject} {body_text}")
                except: pass

                # Kaydet
                mail_doc = {
                    "message_id": message_id,
                    "type": "outbound",  
                    "user_email": email_user,
                    "account_id": str(account["_id"]),
                    "from": sender_email,
                    "to": msg.get("To", ""), 
                    "subject": subject,
                    "subject_normalized": normalize_subject(subject),
                    "body": body_text.strip(),
                    "body_html": body_html,
                    "created_at": datetime.utcnow(), 
                    "status": "SENT",
                    "is_owner": True,
                    "in_reply_to": msg.get("In-Reply-To", ""), 
                    "references": msg.get("References", "").split() if msg.get("References") else [],
                    "attachments": attachments,
                    "embedding": vector_embedding
                }

                # Thread'e bağlı giden mail ise tag'leri zincirden devral
                inherited_tags = _find_thread_tags(mail_doc.get("in_reply_to", ""), mail_doc.get("references", []))
                if inherited_tags:
                    mail_doc["tags"] = inherited_tags
                
                mails_col.insert_one(mail_doc)
                print(f"📤 Sent Mail Eşleşti: {subject}")

            except Exception:
                pass
        
        mail.logout()
    except Exception:
        pass


def check_all_sent():
    """Veritabanındaki TÜM aktif hesapların Sent kutusunu tarar"""
    load_dotenv(override=True)
    
    # 1) Accounts tablosundaki aktif hesaplar (Multi-Account)
    active_accounts = list(accounts_col.find({"is_active": True}))
    
    # 2) Migration/Fallback: Accounts boşsa eski Users tablosu
    if not active_accounts:
        active_users = list(users_col.find({"is_active": True}))
        if active_users:
            print("ℹ️ Sent Listener: Accounts boş, eski User tablosuna bakılıyor...")
            for user in active_users:
                temp_account = {
                    "_id": user["_id"],
                    "email": user["email"],
                    "password": user["app_password"],
                    "provider": "gmail"
                }
                process_account_sent(temp_account)
            return
    
    if not active_accounts:
        # Kurulum yoksa veya aktif hesap yoksa sessiz çık
        return
    
    print(f"🔄 Toplam {len(active_accounts)} hesabın Sent kutusu taranıyor...")
    for account in active_accounts:
        process_account_sent(account)
