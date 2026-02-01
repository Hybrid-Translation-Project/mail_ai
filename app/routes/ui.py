import os
import re
import uuid 
import io
import imaplib
import email
from email.header import decode_header
from typing import Optional, List
from fastapi import APIRouter, Request, Form, Depends, HTTPException, Body, Query
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, StreamingResponse, Response
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv 
from datetime import datetime
from bson import ObjectId
import json 
from pydantic import BaseModel

# Veritabanı ve Servisler
from app.database import mails_col, contacts_col, tasks_col, users_col, accounts_col, tags_col
from app.services.mail_sender import send_gmail_via_user
from app.services.reply_generator import generate_reply, generate_decision_reply
from app.core.security import encrypt_password, verify_master_password, hash_master_password, decrypt_password

# --- YENİ EKLENEN: Semantik Arama Modülü ---
try:
    from app.rag.embeddings import get_embedding
except ImportError:
    def get_embedding(text): return []

router = APIRouter()

# --- DİZİN VE ŞABLON AYARLARI ---
current_dir = os.path.dirname(os.path.abspath(__file__)) 
app_dir = os.path.dirname(current_dir) 
root_dir = os.path.dirname(app_dir) 
ENV_PATH = os.path.join(root_dir, ".env")

templates = Jinja2Templates(directory=os.path.join(app_dir, "templates"))

# Başlangıçta .env'yi oku
load_dotenv(ENV_PATH, override=True)

# --- VERİ MODELLERİ ---
class WriterDraftRequest(BaseModel):
    draft_id: Optional[str] = None
    sender_email: str
    to_email: str
    subject: str
    body: str

class ReplyDraftRequest(BaseModel):
    mail_id: str
    draft_content: str

# --- YARDIMCI FONKSİYONLAR ---

def is_configured():
    if not os.path.exists(ENV_PATH): return False
    return users_col.find_one({"is_active": True}) is not None

def clean_html(raw_html):
    if not raw_html: return ""
    cleanr = re.compile('<.*?>')
    cleantext = re.sub(cleanr, '', raw_html)
    return cleantext.replace('&nbsp;', ' ')

def add_draft_version(mail_id: str, content: str, source: str = "USER"):
    if not content: return
    version_entry = {
        "body": content,
        "source": source,
        "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    mails_col.update_one(
        {"_id": ObjectId(mail_id)},
        {"$push": {"draft_history": version_entry}}
    )

def mark_mail_read(mail_id: str):
    try:
        mails_col.update_one(
            {"_id": ObjectId(mail_id)},
            {"$set": {"is_read": True, "read_at": datetime.utcnow()}}
        )
    except Exception:
        pass

def normalize_subject(subject):
    if not subject: return ""
    s = subject.lower()
    clean_pattern = r'^\s*(?:re|fw|fwd)\s*:\s*'
    while re.match(clean_pattern, s):
        s = re.sub(clean_pattern, '', s)
    return s.strip()

def clean_reply_body(body):
    """Mail içeriğindeki alıntı satırlarını temizler."""
    if not body: return ""
    quote_patterns = [
        r'On\s+.*,\s+.*at\s+.*wrote:', 
        r'Le\s+.*à\s+.*a\s+écrit\s*:', 
        r'El\s+.*,\s+.*escribió:',    
        r'-----\s*Original Message\s*-----', 
        r'From:\s*.*Sent:\s*.*To:\s*.*Subject:', 
        r'________________________________',
    ]
    lines = body.split('\n')
    clean_lines = []
    for line in lines:
        is_quote_line = False
        for pattern in quote_patterns:
            if re.search(pattern, line, re.IGNORECASE):
                is_quote_line = True
                break
        if is_quote_line: break 
        clean_lines.append(line)
    
    cleaned_text = "\n".join(clean_lines).strip()
    return cleaned_text if cleaned_text else body

def filter_thread_chain(candidates, target_id):
    """Sadece birbirine bağlı mailleri filtreler."""
    if not candidates: return []
    id_map = {str(m["_id"]): m for m in candidates}
    msg_id_map = {}
    
    for m in candidates:
        raw_mid = m.get("message_id")
        if raw_mid:
            msg_id_map[raw_mid.strip().strip("<>")] = str(m["_id"])
            
    graph = {mid: set() for mid in id_map}
    for m in candidates:
        curr_id = str(m["_id"])
        irt = m.get("in_reply_to")
        if irt:
            pid = msg_id_map.get(irt.strip().strip("<>"))
            if pid:
                graph[curr_id].add(pid)
                graph[pid].add(curr_id)
        
        refs = m.get("references")
        if refs:
            if isinstance(refs, str): refs = refs.split()
            for ref in refs:
                rid = msg_id_map.get(ref.strip().strip("<>"))
                if rid:
                    graph[curr_id].add(rid)
                    graph[rid].add(curr_id)
    
    visited = set()
    queue = [target_id]
    while queue:
        node = queue.pop(0)
        if node in visited: continue
        visited.add(node)
        for neighbor in graph[node]:
            if neighbor not in visited: queue.append(neighbor)
            
    filtered = [id_map[mid] for mid in visited]
    filtered.sort(key=lambda x: x.get("created_at") or "")
    return filtered

# =========================================================================
# 🚀 STREAM VE DOWNLOAD ENDPOINTLERİ (ESKİ SİSTEM GERİ GELDİ)
# =========================================================================

def get_imap_content(mail_doc, target_id, mode="cid"):
    """
    IMAP'e bağlanır, maili bulur ve istenen içeriği (CID veya Filename) çeker.
    Veritabanını şişirmemek için anlık çalışır.
    """
    try:
        # 1. Hesap Bilgilerini Bul
        account_id = mail_doc.get("account_id")
        if not account_id: return None, None, None
        
        account = accounts_col.find_one({"_id": ObjectId(account_id)})
        if not account: return None, None, None

        # 2. Şifreyi Çöz
        email_user = account.get("email")
        try:
            email_pass = decrypt_password(account.get("password"))
        except: return None, None, None

        # 3. Bağlan
        host = "imap.gmail.com"
        if account.get("provider") == "outlook": host = "outlook.office365.com"
        
        mail = imaplib.IMAP4_SSL(host)
        mail.login(email_user, email_pass)
        
        # 4. Maili Bul (Sent veya Inbox)
        # Önce Inbox'a bak
        mail.select("inbox")
        typ, data = mail.search(None, f'(HEADER Message-ID "{mail_doc["message_id"]}")')
        
        if not data[0]:
            # Bulamazsa Sent'e bak
            mail.select('"[Gmail]/Sent Mail"')
            typ, data = mail.search(None, f'(HEADER Message-ID "{mail_doc["message_id"]}")')
        
        if not data[0]: 
            mail.logout()
            return None, None, None

        mail_id = data[0].split()[-1]
        _, msg_data = mail.fetch(mail_id, "(RFC822)")
        msg = email.message_from_bytes(msg_data[0][1])
        
        # 5. İçeriği Ara (Multipart Gezintisi)
        found_data = None
        found_type = None
        found_filename = "download"

        for part in msg.walk():
            # Moduna göre arama yap
            if mode == "cid":
                cid = part.get("Content-ID", "").strip("<> ")
                if cid == target_id:
                    found_data = part.get_payload(decode=True)
                    found_type = part.get_content_type()
                    break
            elif mode == "filename":
                fname = part.get_filename()
                if fname:
                    fname = decode_header(fname)[0][0]
                    if isinstance(fname, bytes): fname = fname.decode()
                    if fname == target_id:
                        found_data = part.get_payload(decode=True)
                        found_type = part.get_content_type()
                        found_filename = fname
                        break
        
        mail.logout()
        return found_data, found_type, found_filename

    except Exception as e:
        print(f"Stream Error: {e}")
        return None, None, None

@router.get("/ui/stream/{message_id}/{content_id}")
async def stream_mail_content(message_id: str, content_id: str):
    """Inline resimleri (CID) göstermek için endpoint"""
    # Mesaj ID'sinde <> varsa temizle (Url'den temiz gelmeyebilir)
    clean_mid = message_id.strip()
    if not clean_mid.startswith("<"): clean_mid = f"<{clean_mid}>"
    
    # DB'den maili bul (Hesap ID'si lazım)
    # message_id varyasyonlarını dene
    mail_doc = mails_col.find_one({"message_id": {"$in": [clean_mid, message_id, message_id.strip("<>")]}})
    
    if not mail_doc:
        return Response(status_code=404)

    data, ctype, _ = get_imap_content(mail_doc, content_id, mode="cid")
    
    if data:
        return StreamingResponse(io.BytesIO(data), media_type=ctype)
    else:
        # Bulunamazsa 1x1 şeffaf pixel dön (Kırık resim ikonu çıkmasın)
        return Response(status_code=404)

@router.get("/ui/download/{message_id}/{filename}")
async def download_attachment(message_id: str, filename: str):
    """Dosya indirmek için endpoint"""
    clean_mid = message_id.strip()
    if not clean_mid.startswith("<"): clean_mid = f"<{clean_mid}>"
    
    mail_doc = mails_col.find_one({"message_id": {"$in": [clean_mid, message_id, message_id.strip("<>")]}})
    
    if not mail_doc:
        return Response(status_code=404)

    data, ctype, fname = get_imap_content(mail_doc, filename, mode="filename")
    
    if data:
        # Dosya ismi güvenliği
        from urllib.parse import quote
        encoded_filename = quote(fname)
        return StreamingResponse(
            io.BytesIO(data), 
            media_type=ctype or "application/octet-stream",
            headers={"Content-Disposition": f"attachment; filename*=utf-8''{encoded_filename}"}
        )
    else:
        return Response(status_code=404)

# =========================================================================
# ROUTINGLER (SETUP, LOGIN, DASHBOARD vb.)
# =========================================================================

@router.get("/setup", response_class=HTMLResponse)
async def setup_page(request: Request):
    if is_configured(): return RedirectResponse(url="/login")
    return templates.TemplateResponse("setup_web.html", {"request": request})

@router.post("/setup")
async def run_setup(full_name: str = Form(...), company_name: str = Form(...), email: str = Form(...), 
                    app_password: str = Form(...), master_password: str = Form(...), signature: str = Form(...)):
    try:
        from cryptography.fernet import Fernet
        new_key = Fernet.generate_key().decode()
        os.environ["ENCRYPTION_KEY"] = new_key
        
        enc_pass = encrypt_password(app_password)
        hashed_master = hash_master_password(master_password)
        
        users_col.update_many({}, {"$set": {"is_active": False}})
        user_data = {
            "full_name": full_name, "company_name": company_name, "email": email,
            "app_password": enc_pass, "master_password": hashed_master,
            "signature": signature, "is_active": True, "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        users_col.update_one({"email": email}, {"$set": user_data}, upsert=True)
        
        user = users_col.find_one({"email": email})
        first_account = {
            "user_id": user["_id"], "email": email, "password": enc_pass,
            "provider": "gmail", "auth_type": "password", "signature": signature,
            "is_active": True, "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        if not accounts_col.find_one({"email": email}):
            accounts_col.insert_one(first_account)

        if tags_col.count_documents({}) == 0:
            import json
            defaults_path = os.path.join(app_dir, "defaults.json")
            if os.path.exists(defaults_path):
                with open(defaults_path, "r", encoding="utf-8") as f:
                    default_tags = json.load(f)
                    if default_tags: tags_col.insert_many(default_tags)

        return RedirectResponse(url="/login?msg=Basarili", status_code=303)
    except Exception as e: return RedirectResponse(url=f"/setup?error={str(e)}", status_code=303)

@router.get("/", response_class=HTMLResponse)
@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    if not is_configured(): return RedirectResponse(url="/setup")
    return templates.TemplateResponse("login.html", {"request": request})

@router.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    load_dotenv(ENV_PATH, override=True)
    env_email = users_col.find_one({"is_active": True})["email"]
    env_master = users_col.find_one({"is_active": True})["master_password"]
    
    if username.strip() == env_email and verify_master_password(password, env_master):
        return RedirectResponse(url="/ui/dashboard", status_code=303)
    return templates.TemplateResponse("login.html", {"request": request, "error": "Hatalı Giriş!"})

@router.get("/ui/accounts", response_class=HTMLResponse)
async def accounts_page(request: Request):
    user = users_col.find_one({"is_active": True})
    accounts = list(accounts_col.find({"user_id": user["_id"]}))
    for acc in accounts: acc["_id"] = str(acc["_id"])
    return templates.TemplateResponse("accounts.html", {"request": request, "user": user, "accounts": accounts})

@router.post("/ui/accounts/add")
async def add_account(email: str = Form(...), app_password: str = Form(...), signature: str = Form(...)):
    user = users_col.find_one({"is_active": True})
    enc_pass = encrypt_password(app_password)
    new_account = {
        "user_id": user["_id"], "email": email, "password": enc_pass,
        "provider": "gmail", "auth_type": "password", "signature": signature,
        "is_active": True, "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    accounts_col.insert_one(new_account)
    return RedirectResponse(url="/ui/accounts?msg=Hesap+Basariyla+Eklendi", status_code=303)

@router.post("/ui/accounts/delete/{account_id}")
async def delete_account(account_id: str):
    accounts_col.delete_one({"_id": ObjectId(account_id)})
    return RedirectResponse(url="/ui/accounts?msg=Hesap+Silindi", status_code=303)

@router.get("/ui/dashboard", response_class=HTMLResponse)
def home_dashboard(request: Request):
    if not is_configured(): return RedirectResponse(url="/setup")
    user = users_col.find_one({"is_active": True})
    stats = {
        "pending_mails": mails_col.count_documents({"status": "WAITING_APPROVAL"}),
        "pending_tasks": tasks_col.count_documents({"status": "WAITING_APPROVAL"}),
        "total_contacts": contacts_col.count_documents({}),
    }
    urgent_tasks = list(tasks_col.find({"status": "CONFIRMED"}).sort([("urgency_score", -1), ("due_date", 1)]).limit(5))
    for t in urgent_tasks: t["_id"] = str(t["_id"])
    
    # --- GRUPLAMA MOTORU BAŞLANGIÇ ---
    # 1. Bekleyen mailleri çek
    raw_mails = list(mails_col.find({
        "status": {"$in": ["WAITING_APPROVAL", "REPLIED"]},
        "type": {"$ne": "outbound"}
    }).sort("created_at", -1))
    
    # 2. Gruplama Mantığı
    grouped_mails = {}
    
    for m in raw_mails:
        # Konuyu normalize et
        subj = m.get("subject_normalized")
        if not subj:
            subj = normalize_subject(m.get("subject", ""))
            
        if subj not in grouped_mails:
            # İlk kez görülen konu
            m["_id"] = str(m["_id"])
            if "is_read" not in m: m["is_read"] = False
            m["thread_count"] = 1
            grouped_mails[subj] = m
        else:
            # Zaten var, sayacı artır
            grouped_mails[subj]["thread_count"] += 1
            
            # En güncel maili göster
            current_date = grouped_mails[subj].get("created_at")
            new_date = m.get("created_at")
            
            if new_date and current_date and new_date > current_date:
                m["_id"] = str(m["_id"])
                m["thread_count"] = grouped_mails[subj]["thread_count"]
                grouped_mails[subj] = m

    # Listeye çevir ve sırala
    final_mail_list = list(grouped_mails.values())
    final_mail_list.sort(key=lambda x: x.get("created_at"), reverse=True)
    # --- GRUPLAMA MOTORU BİTİŞ ---

    # Etiketler
    all_tags = list(tags_col.find({}))
    tags_map = {t["slug"]: t for t in all_tags}

    return templates.TemplateResponse("home.html", {
        "request": request, 
        "stats": stats, 
        "urgent_tasks": urgent_tasks, 
        "user": user
    })

@router.get("/ui/tasks", response_class=HTMLResponse)
async def tasks_page(request: Request):
    user = users_col.find_one({"is_active": True})
    tasks = list(tasks_col.find().sort([("status", 1), ("urgency_score", -1)]))
    for t in tasks: t["_id"] = str(t["_id"])
    accounts = list(accounts_col.find({"user_id": user["_id"]}))
    return templates.TemplateResponse("tasks.html", {"request": request, "tasks": tasks, "user": user, "accounts": accounts})

@router.post("/ui/task/approve/{task_id}")
async def approve_task(task_id: str):
    tasks_col.update_one({"_id": ObjectId(task_id)}, {"$set": {"status": "CONFIRMED", "is_approved": True}})
    return RedirectResponse(url="/ui/tasks?msg=Gorev+Onaylandi", status_code=303)

@router.post("/ui/task/reject/{task_id}")
async def reject_task(task_id: str):
    tasks_col.update_one({"_id": ObjectId(task_id)}, {"$set": {"status": "REJECTED"}})
    return RedirectResponse(url="/ui/tasks?msg=Reddedildi", status_code=303)

@router.post("/ui/task/delete/{task_id}")
async def delete_task(task_id: str):
    tasks_col.delete_one({"_id": ObjectId(task_id)})
    return RedirectResponse(url="/ui/tasks?msg=Silindi", status_code=303)

@router.get("/ui", response_class=HTMLResponse)
def inbox(request: Request):
    user = users_col.find_one({"is_active": True})
    
    # --- GRUPLAMA MOTORU (DASHBOARD İÇİN) ---
    # 1. Bekleyen mailleri çek
    raw_mails = list(mails_col.find({
        "status": {"$in": ["WAITING_APPROVAL", "REPLIED"]},
        "type": {"$ne": "outbound"}
    }).sort("created_at", -1))
    
    # 2. Gruplama
    grouped_mails = {}
    
    for m in raw_mails:
        subj = m.get("subject_normalized")
        if not subj:
            subj = normalize_subject(m.get("subject", ""))
            
        if subj not in grouped_mails:
            m["_id"] = str(m["_id"])
            if "is_read" not in m: m["is_read"] = False
            m["thread_count"] = 1
            grouped_mails[subj] = m
        else:
            grouped_mails[subj]["thread_count"] += 1
            current_date = grouped_mails[subj].get("created_at")
            new_date = m.get("created_at")
            if new_date and current_date and new_date > current_date:
                m["_id"] = str(m["_id"])
                m["thread_count"] = grouped_mails[subj]["thread_count"]
                grouped_mails[subj] = m

    final_mail_list = list(grouped_mails.values())
    final_mail_list.sort(key=lambda x: x.get("created_at"), reverse=True)

    all_tags = list(tags_col.find({}))
    tags_map = {t["slug"]: t for t in all_tags}

    return templates.TemplateResponse("dashboard.html", {
        "request": request, "mails": final_mail_list, "user": user, "tags_map": tags_map
    })

@router.get("/ui/drafts", response_class=HTMLResponse)
async def drafts_page(request: Request):
    user = users_col.find_one({"is_active": True})
    drafts = list(mails_col.find({"status": "DRAFT", "type": "outbound"}))
    for d in drafts:
        d["_id"] = str(d["_id"])
        if "updated_at" not in d: d["updated_at"] = d.get("created_at")
        content = d.get("body", "") 
        clean_content = clean_html(content)
        d["preview"] = clean_content[:100] if clean_content else "İçerik Yok"
        d["recipient"] = d.get("to", "Alıcı Yok")

    drafts.sort(key=lambda x: x.get("updated_at") or "", reverse=True)
    return templates.TemplateResponse("drafts.html", {"request": request, "drafts": drafts, "user": user})

@router.post("/save-writer-draft")
async def save_writer_draft(draft: WriterDraftRequest):
    try:
        draft_data = {
            "user_email": draft.sender_email, "from": draft.sender_email, "to": draft.to_email,
            "subject": draft.subject, "body": draft.body,
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "type": "outbound", "status": "DRAFT"
        }
        if draft.draft_id and len(draft.draft_id) > 10:
            mails_col.update_one({"_id": ObjectId(draft.draft_id)}, {"$set": draft_data})
            return {"status": "success", "draft_id": draft.draft_id}
        else:
            draft_data["created_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            result = mails_col.insert_one(draft_data)
            return {"status": "success", "draft_id": str(result.inserted_id)}
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})

@router.post("/save-draft")
async def api_save_draft(draft: ReplyDraftRequest):
    try:
        mails_col.update_one(
            {"_id": ObjectId(draft.mail_id)},
            {"$set": {"reply_draft": draft.draft_content, "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}}
        )
        return {"status": "success"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})

@router.delete("/delete-draft/{mail_id}")
async def delete_draft_api(mail_id: str):
    try:
        mails_col.delete_one({"_id": ObjectId(mail_id)})
        return {"status": "success"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@router.get("/ui/editor/{mail_id}", response_class=HTMLResponse)
async def mail_editor(request: Request, mail_id: str):
    user = users_col.find_one({"is_active": True})
    mail = mails_col.find_one({"_id": ObjectId(mail_id)})
    if not mail: return RedirectResponse(url="/ui")

    mark_mail_read(mail_id)
    
    target_email = mail.get("user_email")
    target_account = accounts_col.find_one({"email": target_email})
    account_signature = target_account.get("signature", "") if target_account else user.get("signature", "")

    if not mail.get("reply_draft"):
        draft = generate_reply(mail["body"], tone="formal")
        mails_col.update_one(
            {"_id": ObjectId(mail_id)}, 
            {"$set": {"reply_draft": draft}, "$push": {"draft_history": {
                "body": draft, "source": "AI", "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }}}
        )
        mail["reply_draft"] = draft
        mail["draft_history"] = [{"body": draft, "source": "AI", "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}]

    # Thread Fetching
    subject_norm = mail.get("subject_normalized") or normalize_subject(mail.get("subject", ""))
    strict_regex = rf"^\s*(?:(?:re|fw|fwd)\s*:\s*)*{re.escape(subject_norm)}\s*$"
    
    query = {"$or": [{"subject_normalized": subject_norm}, {"subject": {"$regex": strict_regex, "$options": "i"}}]}
    thread = list(mails_col.find(query).sort("created_at", 1))
    thread = filter_thread_chain(thread, str(mail_id))
    
    for m in thread:
        m["_id"] = str(m["_id"])
        m["is_owner"] = (m.get("type") == "outbound")

    return templates.TemplateResponse("editor.html", {
        "request": request, "mail": mail, "user": user, "account_signature": account_signature, "thread": thread
    })

@router.post("/ui/task_action/{mail_id}/{action_type}")
async def task_action(mail_id: str, action_type: str):
    mail = mails_col.find_one({"_id": ObjectId(mail_id)})
    new_draft = ""
    decision_val = "neutral"
    if action_type == "approve":
        new_draft = generate_decision_reply(mail["body"], decision="approve")
        decision_val = "approve"
    elif action_type == "reject":
        new_draft = generate_decision_reply(mail["body"], decision="reject")
        decision_val = "reject"
    elif action_type == "regenerate":
        new_draft = generate_reply(mail["body"], tone="formal")
    
    add_draft_version(mail_id, new_draft, source="AI")
    mails_col.update_one(
        {"_id": ObjectId(mail_id)}, 
        {"$set": {"reply_draft": new_draft, "decision": decision_val, "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}}
    )
    return RedirectResponse(url=f"/ui/editor/{mail_id}", status_code=303)

@router.post("/ui/mail/delete/{mail_id}")
async def delete_mail(request: Request, mail_id: str):
    mails_col.delete_one({"_id": ObjectId(mail_id)})
    referer = request.headers.get("referer")
    if referer and "history" in referer: return RedirectResponse(url="/ui/history?msg=Silindi", status_code=303)
    elif referer and "drafts" in referer: return RedirectResponse(url="/ui/drafts?msg=Silindi", status_code=303)
    return RedirectResponse(url="/ui?msg=Silindi", status_code=303)

@router.post("/ui/restore/{mail_id}")
async def restore_mail(mail_id: str):
    mails_col.update_one({"_id": ObjectId(mail_id)}, {"$set": {"status": "WAITING_APPROVAL"}})
    return RedirectResponse(url="/ui?msg=Mail+Geri+Yuklendi", status_code=303)

@router.post("/ui/update/{mail_id}")
async def update_draft(mail_id: str, reply_draft: str = Form(...)):
    add_draft_version(mail_id, reply_draft, source="USER")
    mails_col.update_one(
        {"_id": ObjectId(mail_id)}, 
        {"$set": {"reply_draft": reply_draft, "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}}
    )
    return RedirectResponse(url=f"/ui/editor/{mail_id}?msg=Kaydedildi", status_code=303)

@router.post("/ui/approve/{mail_id}")
def send_approved_mail(mail_id: str, reply_draft: str = Form(...)):
    mail = mails_col.find_one({"_id": ObjectId(mail_id)})
    user = users_col.find_one({"is_active": True})
    account = accounts_col.find_one({"email": mail.get("user_email")})
    signature = account.get("signature", "") if account else user.get("signature", "")
    
    final_body = f"{reply_draft}\n\n---\n{signature}"
    
    # Threading ID oluşturma
    reply_message_id = f"<gen-{uuid.uuid4()}@mail-ai.local>"
    parent_mid = mail.get("message_id", "").strip()
    
    refs = []
    existing_refs = mail.get("references") or []
    if isinstance(existing_refs, str): existing_refs = existing_refs.split()
    if existing_refs: refs.extend(existing_refs)
    if parent_mid and parent_mid not in refs: refs.append(parent_mid)

    is_sent, error_msg = send_gmail_via_user(
        mail["user_email"], mail["from"], f"RE: {mail['subject']}", final_body,
        message_id=reply_message_id, in_reply_to=parent_mid, references=refs
    )
    
    if is_sent:
        mails_col.update_one({"_id": ObjectId(mail_id)}, {"$set": {"status": "REPLIED", "handled_at": datetime.utcnow()}})
        sent_reply_doc = {
            "message_id": reply_message_id, "type": "outbound", "user_email": mail["user_email"], 
            "from": mail["user_email"], "to": mail["from"], "subject": f"Re: {mail['subject']}",
            "subject_normalized": mail.get("subject_normalized"), "body": final_body,
            "body_html": f"<div style='white-space: pre-wrap;'>{final_body}</div>",
            "created_at": datetime.utcnow(), "status": "SENT", "is_owner": True,
            "tags": mail.get("tags", []), "in_reply_to": parent_mid, "references": refs,
        }
        mails_col.insert_one(sent_reply_doc)
        
        if mail.get("extracted_task") and mail.get("decision") != "reject":
            tasks_col.insert_one({
                "user_email": mail["user_email"], "title": mail["extracted_task"]["title"],
                "due_date": mail["extracted_task"].get("date"), "category": mail.get("category", "Diğer"),
                "urgency_score": mail.get("urgency_score", 0), "sender": mail["from"],
                "status": "CONFIRMED", "is_approved": True, "created_at": datetime.utcnow()
            })
        return RedirectResponse(url="/ui?msg=Gonderildi", status_code=303)
    else:
        return RedirectResponse(url=f"/ui/editor/{mail_id}?error={error_msg}", status_code=303)

@router.post("/ui/cancel/{mail_id}")
async def cancel_mail(mail_id: str):
    mails_col.update_one({"_id": ObjectId(mail_id)}, {"$set": {"status": "CANCELED"}})
    return RedirectResponse(url="/ui?msg=Arsive+Kaldirildi", status_code=303)

@router.get("/ui/history", response_class=HTMLResponse)
def history(request: Request):
    user = users_col.find_one({"is_active": True})
    old_mails = list(mails_col.find({"status": {"$in": ["SENT", "CANCELED"]}}).sort("created_at", -1).limit(50))
    for m in old_mails: m["_id"] = str(m["_id"])
    return templates.TemplateResponse("history.html", {"request": request, "mails": old_mails, "user": user})

@router.get("/ui/view/{mail_id}", response_class=HTMLResponse)
async def view_mail(request: Request, mail_id: str):
    user = users_col.find_one({"is_active": True})
    try:
        current_mail = mails_col.find_one({"_id": ObjectId(mail_id)})
    except: return RedirectResponse(url="/ui/history")
    
    if not current_mail: return RedirectResponse(url="/ui/history")
    mark_mail_read(mail_id)

    subject_norm = current_mail.get("subject_normalized") or normalize_subject(current_mail.get("subject", ""))
    strict_regex = rf"^\s*(?:(?:re|fw|fwd)\s*:\s*)*{re.escape(subject_norm)}\s*$"
    
    query = {"$or": [{"subject_normalized": subject_norm}, {"subject": {"$regex": strict_regex, "$options": "i"}}]}
    thread = list(mails_col.find(query).sort("created_at", 1))
    thread = filter_thread_chain(thread, str(mail_id))
    
    for m in thread:
        m["_id"] = str(m["_id"])
        m["is_owner"] = (m.get("type") == "outbound")
        if m.get("body"): m["body"] = clean_reply_body(m["body"])

    return templates.TemplateResponse("view_mail.html", {"request": request, "thread": thread, "user": user})

@router.get("/ui/contacts", response_class=HTMLResponse)
async def contacts_page(request: Request, account: str = "all"):
    user = users_col.find_one({"is_active": True})
    accounts = list(accounts_col.find({"user_id": user["_id"]}))
    
    # Oto-tamir
    all_contacts = list(contacts_col.find())
    for contact in all_contacts:
        if "owners" not in contact:
            mails_from_contact = list(mails_col.find({"from": contact["email"]}, {"user_email": 1}))
            found_owners = list(set([m["user_email"] for m in mails_from_contact if "user_email" in m]))
            contacts_col.update_one({"_id": contact["_id"]}, {"$set": {"owners": found_owners}})

    filter_query = {}
    if account != "all": filter_query = {"owners": account}
    contacts = list(contacts_col.find(filter_query).sort("name", 1))
    
    return templates.TemplateResponse("contacts.html", {
        "request": request, "contacts": contacts, "user": user, "accounts": accounts, "selected_account": account
    })

@router.post("/ui/contacts/delete")
async def delete_contact(contact_id: str = Form(...), delete_mode: str = Form(...)):
    contact = contacts_col.find_one({"_id": ObjectId(contact_id)})
    if not contact: return RedirectResponse(url="/ui/contacts?error=Kisi+Bulunamadi", status_code=303)
    
    if delete_mode == "with_history":
        mails_col.delete_many({"from": contact.get("email")})
    
    contacts_col.delete_one({"_id": ObjectId(contact_id)})
    return RedirectResponse(url="/ui/contacts?msg=Kisi+Silindi", status_code=303)

@router.get("/ui/contact/{email}", response_class=HTMLResponse)
async def contact_detail(request: Request, email: str):
    user = users_col.find_one({"is_active": True})
    contact = contacts_col.find_one({"email": email})
    if not contact: return RedirectResponse(url="/ui/contacts")
    history = list(mails_col.find({"from": email}).sort("created_at", -1))
    for h in history: h["_id"] = str(h["_id"])
    return templates.TemplateResponse("contact_detail.html", {"request": request, "contact": contact, "history": history, "user": user})

@router.get("/ui/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    user = users_col.find_one({"is_active": True})
    tags = list(tags_col.find({}).sort("created_at", 1))
    return templates.TemplateResponse("settings.html", {"request": request, "user": user, "tags": tags})

@router.post("/ui/settings/tags/add")
async def add_tag(name: str = Form(...), color: str = Form(...), description: str = Form(...)):
    slug = re.sub(r'[^a-z0-9-]', '', name.strip().lower().replace(" ", "-").replace("ı", "i").replace("ğ", "g").replace("ü", "u").replace("ş", "s").replace("ö", "o").replace("ç", "c"))
    if tags_col.find_one({"slug": slug}):
        return RedirectResponse(url="/ui/settings?error=error_tag_exists", status_code=303)
    
    new_tag = {"name": name, "slug": slug, "color": color, "description": description, "created_at": datetime.now()}
    tags_col.insert_one(new_tag)
    return RedirectResponse(url="/ui/settings?msg=msg_tag_added", status_code=303)

@router.post("/ui/settings/tags/delete/{tag_id}")
async def delete_tag(tag_id: str):
    tags_col.delete_one({"_id": ObjectId(tag_id)})
    return RedirectResponse(url="/ui/settings?msg=msg_tag_deleted", status_code=303)

@router.post("/ui/settings/tags/update/{tag_id}")
async def update_tag(tag_id: str, name: str = Form(...), color: str = Form(...), description: str = Form(...)):
    slug = re.sub(r'[^a-z0-9-]', '', name.strip().lower().replace(" ", "-").replace("ı", "i").replace("ğ", "g").replace("ü", "u").replace("ş", "s").replace("ö", "o").replace("ç", "c"))
    tags_col.update_one({"_id": ObjectId(tag_id)}, {"$set": {"name": name, "slug": slug, "color": color, "description": description, "updated_at": datetime.now()}})
    return RedirectResponse(url="/ui/settings?msg=msg_tag_updated", status_code=303)

@router.get("/ui/writer", response_class=HTMLResponse)
async def writer_page(request: Request, draft_id: Optional[str] = None):
    user = users_col.find_one({"is_active": True})
    accounts = list(accounts_col.find({"user_id": user["_id"]}))
    draft = None
    if draft_id:
        try:
            draft = mails_col.find_one({"_id": ObjectId(draft_id)})
            if draft: draft["_id"] = str(draft["_id"])
        except: pass
    return templates.TemplateResponse("writer.html", {"request": request, "user": user, "accounts": accounts, "draft": draft})

@router.post("/ui/writer/generate")
async def generate_writer_draft(prompt: str = Form(...)):
    try:
        draft = generate_reply(prompt, tone="formal") 
        return {"draft": draft}
    except Exception as e:
        return {"draft": f"Hata: {str(e)}"}

@router.post("/ui/writer/send")
async def send_writer_mail(sender_email: str = Form(...), to_email: str = Form(...), subject: str = Form(...), body: str = Form(...), draft_id: Optional[str] = Form(None)):
    user = users_col.find_one({"is_active": True})
    account = accounts_col.find_one({"email": sender_email})
    signature = account.get("signature", "") if account else user.get("signature", "")
    
    final_body = f"{body}\n\n---\n{signature}"
    is_sent, msg = send_gmail_via_user(sender_email, to_email, subject, final_body)
    
    if is_sent:
        mails_col.insert_one({
            "user_email": sender_email, "from": sender_email, "to": to_email,
            "subject": subject, "body": body, "status": "SENT",
            "created_at": datetime.utcnow(), "type": "outbound"
        })
        if draft_id and len(draft_id) > 10: mails_col.delete_one({"_id": ObjectId(draft_id)})
        return RedirectResponse(url="/ui/dashboard?msg=Mail+Gonderildi", status_code=303)
    else:
        return RedirectResponse(url=f"/ui/writer?error={msg}", status_code=303)

@router.get("/ui/search-api")
async def search_mails(q: str = Query(..., min_length=1)):
    try:
        query_vector = get_embedding(q)
        if not query_vector:
            return {"results": [], "message": "Vektör oluşturulamadı."}

        pipeline = [
            {"$vectorSearch": {
                "index": "vector_index", "path": "embedding", "queryVector": query_vector,
                "numCandidates": 100, "limit": 10
            }},
            {"$project": {
                "_id": {"$toString": "$_id"}, "subject": 1, "sender": 1,
                "snippet": {"$substr": ["$body", 0, 150]}, "date": 1,
                "score": {"$meta": "vectorSearchScore"}
            }}
        ]
        results = list(mails_col.aggregate(pipeline))
        return {"results": results}
    except Exception as e:
        return {"results": [], "error": str(e)}