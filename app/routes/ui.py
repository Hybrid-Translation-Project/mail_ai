import os
import re
import uuid 
from typing import Optional, List
from fastapi import APIRouter, Request, Form, Depends, HTTPException, Body, Query
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv 
from datetime import datetime
from bson import ObjectId
import json 
# Diğer importlar...

# --- HELPER: Clean Reply Body ---
def clean_reply_body(body):
    """
    Mail içeriğindeki 'On ... wrote:' gibi alıntı satırlarını ve sonrasını temizler.
    Sadece yeni yazılan cevabı göstermek için kullanılır.
    """
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
        
        if is_quote_line:
            break 
            
        clean_lines.append(line)
    
    cleaned_text = "\n".join(clean_lines).strip()
    
    # Eğer temizlik sonrası elie bişey kalmazsa (örn: adam inline cevap yazmışsa)
    # Hiçbir şey göstermemektense, orijinali göstermek daha iyidir.
    if not cleaned_text:
        return body
        
    return cleaned_text
from fastapi.templating import Jinja2Templates
from bson import ObjectId
from datetime import datetime
from dotenv import load_dotenv, set_key
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
    # Eğer embedding modülü henüz hazır değilse hata vermesin, boş fonksiyon dönsün
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

# Writer (Yeni Mail) için Model
class WriterDraftRequest(BaseModel):
    draft_id: Optional[str] = None
    sender_email: str
    to_email: str
    subject: str
    body: str

# Editor (Cevaplama) için Model
class ReplyDraftRequest(BaseModel):
    mail_id: str
    draft_content: str

# --- YARDIMCI FONKSİYONLAR ---

def is_configured():
    if not os.path.exists(ENV_PATH): return False
    return users_col.find_one({"is_active": True}) is not None

def clean_html(raw_html):
    """HTML etiketlerini temizler (Taslak önizlemesi için)"""
    if not raw_html: return ""
    cleanr = re.compile('<.*?>')
    cleantext = re.sub(cleanr, '', raw_html)
    return cleantext.replace('&nbsp;', ' ')

def add_draft_version(mail_id: str, content: str, source: str = "USER"):
    """Mevcut cevap taslağını tarihçeye ekler (Gelen kutusu cevapları için)"""
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
    """Maili 'okundu' olarak işaretler (Inbox'tan düşürmez / status değiştirmez)."""
    try:
        mails_col.update_one(
            {"_id": ObjectId(mail_id)},
            {"$set": {"is_read": True, "read_at": datetime.utcnow()}}
        )
    except Exception:
        pass

# --- KURULUM (SETUP) ---
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
        set_key(ENV_PATH, "ENCRYPTION_KEY", new_key)
        os.environ["ENCRYPTION_KEY"] = new_key
        load_dotenv(ENV_PATH, override=True)
        
        enc_pass = encrypt_password(app_password)
        hashed_master = hash_master_password(master_password)
        
        set_key(ENV_PATH, "EMAIL", email)
        set_key(ENV_PATH, "MASTER_PASSWORD", hashed_master)
        set_key(ENV_PATH, "MONGO_URI", "mongodb://localhost:27017/")
        set_key(ENV_PATH, "DB_NAME", "mail_asistani_db")
        set_key(ENV_PATH, "OLLAMA_MODEL", "mistral")
        
        # --- GÜVENLİK ÖNLEMİ: ÇAKIŞMAYI ÖNLE ---
        # Yeni kurulum yapılıyorsa, eski tüm kullanıcıları pasife çek.
        # Böylece sistemde sadece 1 tane "Aktif" yönetici olur.
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

        # --- VARSAYILAN ETİKETLERİ EKLE (JSON'dan) ---
        if tags_col.count_documents({}) == 0:
            import json
            defaults_path = os.path.join(app_dir, "defaults.json")
            if os.path.exists(defaults_path):
                with open(defaults_path, "r", encoding="utf-8") as f:
                    default_tags = json.load(f)
                    if default_tags:
                        tags_col.insert_many(default_tags)

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
    env_email = os.getenv("EMAIL", "").strip()
    env_master = os.getenv("MASTER_PASSWORD", "").strip()
    if username.strip() == env_email and verify_master_password(password, env_master):
        return RedirectResponse(url="/ui/dashboard", status_code=303)
    return templates.TemplateResponse("login.html", {"request": request, "error": "Hatalı Giriş!"})

# --- HESAP YÖNETİMİ ---
@router.get("/ui/accounts", response_class=HTMLResponse)
async def accounts_page(request: Request):
    user = users_col.find_one({"is_active": True})
    accounts = list(accounts_col.find({"user_id": user["_id"]}))
    
    if not accounts and user.get("email") and user.get("app_password"):
        first_account = {
            "user_id": user["_id"], "email": user["email"], "password": user["app_password"], 
            "provider": "gmail", "auth_type": "password",
            "signature": user.get("signature", "Saygılarımla,"), "is_active": True,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        accounts_col.insert_one(first_account)
        accounts = [first_account]

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

# --- DASHBOARD ---
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
    return templates.TemplateResponse("home.html", {"request": request, "stats": stats, "urgent_tasks": urgent_tasks, "user": user})

# --- GÖREVLER ---
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

# --- GELEN KUTUSU (Gelen mailler sadece burada kalır) ---
@router.get("/ui", response_class=HTMLResponse)
def inbox(request: Request):
    user = users_col.find_one({"is_active": True})
    # 'outbound' (Writer taslakları) olanları Inbox'ta gösterme
    waiting_mails = list(mails_col.find({
        # Gmail gibi: cevaplandıktan sonra da Inbox listede kalsın
        "status": {"$in": ["WAITING_APPROVAL", "REPLIED"]},
        "type": {"$ne": "outbound"}
    }).sort("created_at", -1))
    
    for m in waiting_mails:
        m["_id"] = str(m["_id"])
        if "is_read" not in m:
            m["is_read"] = False

    # YENİ: Etiketleri (Tags) çek ve map'le
    # Mail'lerde sadece "slug" tutuyoruz. Ekranda rengini ve ismini göstermek için
    # tüm tagleri çekip bir sözlük (dictionary) yapıyoruz.
    all_tags = list(tags_col.find({}))
    tags_map = {t["slug"]: t for t in all_tags}

    return templates.TemplateResponse("dashboard.html", {
        "request": request, 
        "mails": waiting_mails, 
        "user": user,
        "tags_map": tags_map # Template'e gönderiyoruz
    })

# --- TASLAKLAR SAYFASI (Sadece WRITER'dan gelen yarım kalmış mailler) ---
@router.get("/ui/drafts", response_class=HTMLResponse)
async def drafts_page(request: Request):
    user = users_col.find_one({"is_active": True})
    
    # Sadece Writer'dan oluşturulmuş (type=outbound) ve gönderilmemiş (status=DRAFT) olanları çek.
    # Gelen kutusundaki cevap taslaklarını buraya almıyoruz.
    drafts = list(mails_col.find({
        "status": "DRAFT",
        "type": "outbound"
    }))

    # Önyüz verileri
    for d in drafts:
        d["_id"] = str(d["_id"])
        if "updated_at" not in d: d["updated_at"] = d.get("created_at")
        
        # İçerik özeti (HTML temizliği yapılmış)
        content = d.get("body", "") 
        clean_content = clean_html(content)
        d["preview"] = clean_content[:100] if clean_content else "İçerik Yok"
        
        d["recipient"] = d.get("to", "Alıcı Yok")

    drafts.sort(key=lambda x: x.get("updated_at") or "", reverse=True)

    return templates.TemplateResponse("drafts.html", {"request": request, "drafts": drafts, "user": user})

# --- WRITER AUTO-SAVE API (YENİ) ---
@router.post("/save-writer-draft")
async def save_writer_draft(draft: WriterDraftRequest):
    """
    Writer sayfasındaki içeriği kaydeder (Yeni mail veya güncelleme).
    status='DRAFT', type='outbound' yapar.
    """
    try:
        draft_data = {
            "user_email": draft.sender_email,
            "from": draft.sender_email,
            "to": draft.to_email,
            "subject": draft.subject,
            "body": draft.body,
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "type": "outbound",  # Bu bir giden mail taslağıdır
            "status": "DRAFT"    # Henüz gönderilmedi
        }

        # Eğer ID varsa GÜNCELLE
        if draft.draft_id and len(draft.draft_id) > 10:
            mails_col.update_one(
                {"_id": ObjectId(draft.draft_id)},
                {"$set": draft_data}
            )
            return {"status": "success", "draft_id": draft.draft_id}
        
        # ID yoksa YENİ OLUŞTUR
        else:
            draft_data["created_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            result = mails_col.insert_one(draft_data)
            return {"status": "success", "draft_id": str(result.inserted_id)}

    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})

# --- EDITOR AUTO-SAVE API (SADECE CEVAPLAR İÇİN) ---
@router.post("/save-draft")
async def api_save_draft(draft: ReplyDraftRequest):
    """
    Gelen kutusundaki cevap taslağını günceller.
    ASLA status='DRAFT' yapmaz, böylece Taslaklar sayfasına düşmez.
    """
    try:
        mails_col.update_one(
            {"_id": ObjectId(draft.mail_id)},
            {
                "$set": {
                    "reply_draft": draft.draft_content,
                    "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
            }
        )
        return {"status": "success"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})

# --- TASLAK SİLME ---
@router.delete("/delete-draft/{mail_id}")
async def delete_draft_api(mail_id: str):
    # Writer taslağını veritabanından tamamen siler
    try:
        mails_col.delete_one({"_id": ObjectId(mail_id)})
        return {"status": "success"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

# --- EDITOR SAYFASI (Gelen Mail Cevaplama) ---
@router.get("/ui/editor/{mail_id}", response_class=HTMLResponse)
async def mail_editor(request: Request, mail_id: str):
    user = users_col.find_one({"is_active": True})
    mail = mails_col.find_one({"_id": ObjectId(mail_id)})
    if not mail: return RedirectResponse(url="/ui")

    # Mail açıldı -> okundu işaretle (Inbox'tan düşürmez)
    mark_mail_read(mail_id)
    
    target_email = mail.get("user_email")
    target_account = accounts_col.find_one({"email": target_email})
    account_signature = target_account.get("signature", "") if target_account else user.get("signature", "")

    # AI ilk taslağı oluşturur (Veritabanında reply_draft güncellenir ama status değişmez)
    if not mail.get("reply_draft"):
        draft = generate_reply(mail["body"], tone="formal")
        mails_col.update_one(
            {"_id": ObjectId(mail_id)}, 
            {
                "$set": {"reply_draft": draft},
                "$push": {"draft_history": {
                    "body": draft, 
                    "source": "AI", 
                    "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }}
            }
        )
        mail["reply_draft"] = draft
        mail["draft_history"] = [{
            "body": draft, "source": "AI", "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }]

    # --- THREAD FETCHING (YENİ) ---
    subject_norm = mail.get("subject_normalized")
    if not subject_norm:
        subject_norm = normalize_subject(mail.get("subject", ""))
    
    strict_regex = rf"^\s*(?:(?:re|fw|fwd)\s*:\s*)*{re.escape(subject_norm)}\s*$"
    
    query = {
        "$or": [
            {"subject_normalized": subject_norm},
            {"subject": {"$regex": strict_regex, "$options": "i"}}
        ]
    }
    # Thread'i çek ve sırala
    thread_cursor = mails_col.find(query).sort("created_at", 1)
    thread = list(thread_cursor)
    
    # STRICT FILTERING (YENİ)
    thread = filter_thread_chain(thread, str(mail_id))
    
    # ObjectId -> String ve Owner check
    for m in thread:
        m["_id"] = str(m["_id"])
        is_owner = False
        if m.get("type") == "outbound": is_owner = True
        # elif accounts_col.find_one({"email": m.get("from")}): is_owner = True # İPTAL
        m["is_owner"] = is_owner

    return templates.TemplateResponse("editor.html", {
        "request": request, 
        "mail": mail, 
        "user": user, 
        "account_signature": account_signature,
        "thread": thread # <-- Template'e gönder
    })

# --- KARAR MEKANİZMASI ---
@router.post("/ui/task_action/{mail_id}/{action_type}")
async def task_action(mail_id: str, action_type: str):
    mail = mails_col.find_one({"_id": ObjectId(mail_id)})
    if not mail: return {"status": "error", "message": "Mail bulunamadı"}
    
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
        {
            "$set": {
                "reply_draft": new_draft, 
                "decision": decision_val,
                "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        }
    )
    return RedirectResponse(url=f"/ui/editor/{mail_id}", status_code=303)

# ==========================================================
# 🛠️ DÜZELTİLEN KISIM: AKILLI SİLME YÖNLENDİRMESİ
# ==========================================================
@router.post("/ui/mail/delete/{mail_id}")
async def delete_mail(request: Request, mail_id: str):
    mails_col.delete_one({"_id": ObjectId(mail_id)})
    
    # Kullanıcının geldiği sayfayı (Referer) alıyoruz
    referer = request.headers.get("referer")
    
    # 1. Eğer "history" sayfasından silme tuşuna basıldıysa, History'ye geri dön
    if referer and "history" in referer:
        return RedirectResponse(url="/ui/history?msg=Silindi", status_code=303)
    
    # 2. Eğer "drafts" (taslaklar) sayfasından geldiyse oraya dön
    elif referer and "drafts" in referer:
        return RedirectResponse(url="/ui/drafts?msg=Silindi", status_code=303)
        
    # 3. Varsayılan (Inbox veya başka yer) -> Dashboard'a dön
    return RedirectResponse(url="/ui?msg=Silindi", status_code=303)

# --- MAİL GERİ YÜKLEME (RESTORE) ---
@router.post("/ui/restore/{mail_id}")
async def restore_mail(mail_id: str):
    # İptal edilen maili tekrar 'WAITING_APPROVAL' yaparak Gelen Kutusuna atar
    mails_col.update_one(
        {"_id": ObjectId(mail_id)}, 
        {"$set": {"status": "WAITING_APPROVAL"}}
    )
    return RedirectResponse(url="/ui?msg=Mail+Geri+Yuklendi", status_code=303)

# --- MANUEL KAYDETME (EDITOR) ---
@router.post("/ui/update/{mail_id}")
async def update_draft(mail_id: str, reply_draft: str = Form(...)):
    """Editor sayfasındaki manuel kaydetme"""
    add_draft_version(mail_id, reply_draft, source="USER")
    mails_col.update_one(
        {"_id": ObjectId(mail_id)}, 
        {"$set": {"reply_draft": reply_draft, "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}}
    )
    return RedirectResponse(url=f"/ui/editor/{mail_id}?msg=Kaydedildi", status_code=303)

# --- ONAY VE GÖNDERME (EDITOR) ---
@router.post("/ui/approve/{mail_id}")
def send_approved_mail(mail_id: str, reply_draft: str = Form(...)):
    mail = mails_col.find_one({"_id": ObjectId(mail_id)})
    user = users_col.find_one({"is_active": True})
    account = accounts_col.find_one({"email": mail.get("user_email")})
    signature = account.get("signature", "") if account else user.get("signature", "")
    
    final_body = f"{reply_draft}\n\n---\n{signature}"

    # --- THREADING (Reply gibi çalışması için KRİTİK) ---
    def _as_mid(v: str) -> str:
        v = (v or "").strip()
        if not v:
            return ""
        if not v.startswith("<"):
            v = "<" + v
        if not v.endswith(">"):
            v = v + ">"
        return v

    parent_mid = _as_mid(mail.get("message_id", ""))
    # Kendi ürettiğimiz Message-ID'yi hem SMTP header'a hem DB'ye yazıyoruz.
    # Böylece Sent Listener sonradan aynı Message-ID ile gelirse duplicate oluşmaz.
    reply_message_id = f"<gen-{uuid.uuid4()}@mail-ai.local>"

    # References: varsa mevcut zinciri koru + parent ekle
    existing_refs = mail.get("references") or []
    if isinstance(existing_refs, str):
        existing_refs = existing_refs.split()
    refs = []
    for x in list(existing_refs) + ([parent_mid] if parent_mid else []):
        mid = _as_mid(str(x))
        if mid and mid not in refs:
            refs.append(mid)

    is_sent, error_msg = send_gmail_via_user(
        mail["user_email"],
        mail["from"],
        f"RE: {mail['subject']}",
        final_body,
        message_id=reply_message_id,
        in_reply_to=parent_mid or None,
        references=refs or None,
    )
    
    if is_sent:
        # 1. Orijinal mailin durumunu güncelle
        mails_col.update_one({"_id": ObjectId(mail_id)}, {"$set": {"status": "REPLIED", "handled_at": datetime.utcnow()}})
        
        # 2. Giden cevabı AYRI BİR KAYIT olarak ekle (Thread'de görünmesi için)
        sent_reply_doc = {
            # SMTP header ile aynı Message-ID (thread bağlantısı ve dedupe için kritik)
            "message_id": reply_message_id,
            "type": "outbound", 
            "user_email": mail["user_email"], 
            "from": mail["user_email"],
            "to": mail["from"],
            "subject": f"Re: {mail['subject']}",
            "subject_normalized": mail.get("subject_normalized") or normalize_subject(mail["subject"]),
            "body": final_body,
            "body_html": f"<div style='white-space: pre-wrap;'>{final_body}</div>",
            "created_at": datetime.utcnow(),
            "status": "SENT",
            "is_owner": True,
            "tags": mail.get("tags", []),

            # Threading linkleri (filter_thread_chain için kritik)
            "in_reply_to": parent_mid,
            "references": refs,
        }
        mails_col.insert_one(sent_reply_doc)
        
        decision = mail.get("decision", "neutral")
        if mail.get("extracted_task") and decision != "reject":
            tasks_col.insert_one({
                "user_email": mail["user_email"],
                "title": mail["extracted_task"]["title"],
                "due_date": mail["extracted_task"].get("date"),
                "category": mail.get("category", "Diğer"),
                "urgency_score": mail.get("urgency_score", 0),
                "sender": mail["from"],
                "status": "CONFIRMED",
                "is_approved": True,
                "created_at": datetime.utcnow()
            })
        # Gmail gibi: cevaplandıktan sonra Inbox listede kalsın
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

def normalize_subject(subject):
    """
    Konu başlığını temizler:
    - re:, fw:, fwd: gibi ön ekleri kaldırır
    - Küçük harfe çevirir
    Örn: "Re: Fwd: Proje Detayları" -> "proje detaylari"
    """
    if not subject: return ""
    s = subject.lower()
    clean_pattern = r'^\s*(?:re|fw|fwd)\s*:\s*'
    while re.match(clean_pattern, s):
        s = re.sub(clean_pattern, '', s)
    return s.strip()

# --- STRICT THREADING ENGINE ---
def filter_thread_chain(candidates, target_id):
    """
    Sadece kriptografik olarak bağlı mailleri (Message-ID, In-Reply-To, References)
    birbirine bağlar. Konu benzerliği olsa bile zincir dışındakileri eler.
    """
    if not candidates: return []
    
    # 1. Node Haritası Oluştur
    id_map = {} # mail_id -> mail_doc
    msg_id_map = {} # Message-ID -> mail_id
    
    # Hedef mailin Message-ID'sini bul (traverse başlangıcı için)
    target_msg_id = None
    
    for m in candidates:
        m_id = str(m["_id"])
        id_map[m_id] = m
        
        # Message-ID temizle
        raw_mid = m.get("message_id")
        if raw_mid:
            clean_mid = raw_mid.strip().strip("<>")
            msg_id_map[clean_mid] = m_id
            
        if m_id == target_id:
            target_msg_id = raw_mid.strip().strip("<>") if raw_mid else None

    # 2. Graph Oluştur (Adjacency List)
    # Graph: { "mail_id": set(["linked_mail_id_1", "linked_mail_id_2"]) }
    graph = {mid: set() for mid in id_map}
    
    for m in candidates:
        curr_id = str(m["_id"])
        
        # A) In-Reply-To Bağlantısı
        in_reply_to = m.get("in_reply_to")
        if in_reply_to:
            clean_irt = in_reply_to.strip().strip("<>")
            parent_id = msg_id_map.get(clean_irt)
            if parent_id:
                # İki yönlü bağla (Parent <-> Child)
                graph[curr_id].add(parent_id)
                graph[parent_id].add(curr_id)
        
        # B) References Bağlantısı
        refs = m.get("references")
        if refs:
            if isinstance(refs, str): refs = refs.split()
            for ref in refs:
                clean_ref = ref.strip().strip("<>")
                ref_id = msg_id_map.get(clean_ref)
                if ref_id:
                    graph[curr_id].add(ref_id)
                    graph[ref_id].add(curr_id)

    # 3. BFS/DFS ile Zinciri Gez (Connected Component)
    # Target ID'den başla, gidebildiğin her yere git.
    visited = set()
    queue = [target_id]
    
    while queue:
        node = queue.pop(0)
        if node in visited: continue
        visited.add(node)
        
        # Komşuları ekle
        for neighbor in graph[node]:
            if neighbor not in visited:
                queue.append(neighbor)
                
    # 4. Sadece ziyaret edilenleri döndür
    filtered_thread = [id_map[mid] for mid in visited]
    
    # Tarihe göre sırala
    filtered_thread.sort(key=lambda x: x.get("created_at") or "")
    
    return filtered_thread

def clean_reply_body(body):
    """
    Mail içeriğindeki 'On ... wrote:' gibi alıntı satırlarını ve sonrasını temizler.
    Sadece yeni yazılan cevabı göstermek için kullanılır.
    """
    if not body: return ""
    
    # 1. Yaygın alıntı başlıkları (Regex)
    # Örnek: "On Thu, Jan 29, 2026 at 9:51 PM Asir Can Aslan <...> wrote:"
    # Örnek: "Le lun. 29 janv. 2026 à 21:51, Asir Can Aslan <...> a écrit :"
    
    quote_patterns = [
        r'On\s+.*,\s+.*at\s+.*wrote:', # İngilizce standart
        r'Le\s+.*à\s+.*a\s+écrit\s*:', # Fransızca
        r'El\s+.*,\s+.*escribió:',    # İspanyolca
        r'-----\s*Original Message\s*-----', # Outlook vb.
        r'From:\s*.*Sent:\s*.*To:\s*.*Subject:', # Outlook Header
        r'________________________________', # Ayırıcı çizgi
    ]
    
    lines = body.split('\n')
    clean_lines = []
    
    for line in lines:
        is_quote_line = False
        for pattern in quote_patterns:
            if re.search(pattern, line, re.IGNORECASE):
                is_quote_line = True
                break
        
        # Eğer alıntı başlangıcı bulduysak, buradan sonrasını kesip atabiliriz
        # YA DA sadece o satırı atabiliriz. Genelde sonrası full alıntıdır.
        if is_quote_line:
            # Bazen alıntı işaretleri (>) ile devam eder.
            # Şimdilik "On ... wrote:" gördüğümüz yerden sonrasını komple kesiyoruz.
            # Ancak çok agresif olabilir, opsiyonel yapalım.
            # Kullanıcı "maildekini almasak" dediği için kesiyoruz.
            break 
            
        clean_lines.append(line)
    
    return "\n".join(clean_lines).strip()

@router.get("/ui/view/{mail_id}", response_class=HTMLResponse)
async def view_mail(request: Request, mail_id: str):
    user = users_col.find_one({"is_active": True})
    
    # 1. İstenen maili çek
    try:
        current_mail = mails_col.find_one({"_id": ObjectId(mail_id)})
    except:
        return RedirectResponse(url="/ui/history")

    if not current_mail: return RedirectResponse(url="/ui/history")

    # Thread ekranı açıldı -> okundu işaretle (Inbox'tan düşürmez)
    mark_mail_read(mail_id)

    # 2. Konuyu Normalize Et
    # Eğer mail yeni sistemle kaydedildiyse subject_normalized vardır, yoksa biz hesaplarız
    current_subject_norm = current_mail.get("subject_normalized")
    if not current_subject_norm:
        current_subject_norm = normalize_subject(current_mail.get("subject", ""))

    # 3. Thread Araması (Eski ve Yeni Sistemi Kapsa)
    # Strateji: 
    # - subject_normalized eşleşenleri getir (YENİ SİSTEM)
    # - VEYA subject içinde normalize edilmiş metin geçenleri getir (ESKİ SİSTEM - Regex)
    #   Ancak "regex" araması çok geniş olabilir (substring match). 
    #   Bu yüzden başa ve sona çapa (anchor) atarak "Tam Eşleşme" arıyoruz.
    #   (Sadece Re, Fwd gibi ön ekleri görmezden geliyoruz)
    
    strict_regex = rf"^\s*(?:(?:re|fw|fwd)\s*:\s*)*{re.escape(current_subject_norm)}\s*$"
    
    query = {
        "$or": [
            {"subject_normalized": current_subject_norm}, # Yeni kayıtlar
            {"subject": {"$regex": strict_regex, "$options": "i"}} # Eski kayıtlar (Strict Regex)
        ]
    }
    
    # Sadece ilgili kullanıcıya/hesaba ait olanları çek (Güvenlik/Karmaşıklık önlemi)
    # Not: user_email filtresi eklemek iyi olabilir ama thread farklı hesaplar arasında dönüyorsa (cc vs) bunu engeller.
    # Şimdilik genel bırakıyoruz.

    # 4. Verileri Çek ve Sırala (Eskiden Yeniye)
    thread_cursor = mails_col.find(query).sort("created_at", 1)
    thread = list(thread_cursor)
    
    # 5. STRICT FILTERING (YENİ)
    # Konuyla bulduklarımızı, gerçek bağlantı kontrolünden geçiriyoruz.
    thread = filter_thread_chain(thread, str(mail_id))

    # 6. ObjectId -> String dönüşümü ve Ek İşlemler
    for m in thread:
        m["_id"] = str(m["_id"])
    
        is_owner = False
        if m.get("type") == "outbound":
            is_owner = True  
        m["is_owner"] = is_owner

        # GÖRÜNÜM İÇİN TEMİZLİK
        if m.get("body"):
            m["body"] = clean_reply_body(m["body"])

    return templates.TemplateResponse("view_mail.html", {"request": request, "thread": thread, "user": user})

# --- REHBER (GÜNCELLENEN KISIM) ---
@router.get("/ui/contacts", response_class=HTMLResponse)
async def contacts_page(request: Request, account: str = "all"):
    """
    Rehber Sayfası.
    account parametresi: 'all' veya 'serhtay16@gmail.com' gibi spesifik bir mail.
    """
    user = users_col.find_one({"is_active": True})
    accounts = list(accounts_col.find({"user_id": user["_id"]}))
    
    # --- 🛠️ OTO-TAMİR BAŞLANGICI ---
    # Bu blok, rehberdeki kişilerin "owners" (sahipler) listesini günceller.
    # Her maili tarar ve "Bu maili kimden aldım?" -> "Rehbere o hesabı ekle" mantığıyla çalışır.
    
    all_contacts = list(contacts_col.find())
    for contact in all_contacts:
        if "owners" not in contact:
            # Bu kişinin gönderdiği mailleri bul
            mails_from_contact = list(mails_col.find({"from": contact["email"]}, {"user_email": 1}))
            
            # Hangi hesaplarımıza mail atmış? (Tekilleştirme: set)
            found_owners = list(set([m["user_email"] for m in mails_from_contact if "user_email" in m]))
            
            # Veritabanını güncelle
            contacts_col.update_one(
                {"_id": contact["_id"]},
                {"$set": {"owners": found_owners}}
            )
    # --- 🛠️ OTO-TAMİR BİTİŞİ ---

    # --- FİLTRELEME MANTIĞI ---
    filter_query = {}
    if account != "all":
        # Sadece seçilen hesaba ait (owners listesinde bu mail var mı?)
        filter_query = {"owners": account}

    contacts = list(contacts_col.find(filter_query).sort("name", 1))
    
    return templates.TemplateResponse("contacts.html", {
        "request": request, 
        "contacts": contacts, 
        "user": user, 
        "accounts": accounts,
        "selected_account": account  # Frontend'de hangi sekmenin aktif olduğunu bilmek için
    })

# --- KİŞİ SİLME İŞLEMİ (ÇİFT MODLU - YENİ) ---
@router.post("/ui/contacts/delete")
async def delete_contact(contact_id: str = Form(...), delete_mode: str = Form(...)):
    """
    Kişiyi siler.
    delete_mode:
      - 'only_contact': Sadece rehberden siler, mailler kalır.
      - 'with_history': Kişiyi VE ona ait tüm geçmiş mailleri siler.
    """
    # 1. Kişiyi bul
    contact = contacts_col.find_one({"_id": ObjectId(contact_id)})
    if not contact:
        return RedirectResponse(url="/ui/contacts?error=Kisi+Bulunamadi", status_code=303)
    
    # 2. Eğer "Geçmişi de sil" dendiyse -> Mailleri temizle
    if delete_mode == "with_history":
        email = contact.get("email")
        if email:
            # Güvenlik için şimdilik sadece 'from' (onun attıklarını) siliyoruz.
            mails_col.delete_many({"from": email})

    # 3. Kişiyi rehberden sil
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
    user = users_col.find_one({"is_active": True})
    tags = list(tags_col.find({}).sort("created_at", 1))
    return templates.TemplateResponse("settings.html", {"request": request, "user": user, "tags": tags})

# --- TAG YÖNETİMİ (YENİ) ---
@router.post("/ui/settings/tags/add")
async def add_tag(name: str = Form(...), color: str = Form(...), description: str = Form(...)):
    user = users_col.find_one({"is_active": True})
    
    # Otomatik slug oluşturma (Örn: "Acil İşler" -> "acil-isler")
    slug = name.strip().lower().replace(" ", "-").replace("ı", "i").replace("ğ", "g").replace("ü", "u").replace("ş", "s").replace("ö", "o").replace("ç", "c")
    slug = re.sub(r'[^a-z0-9-]', '', slug)
    
    # Aynı slug varsa ekleme
    if tags_col.find_one({"slug": slug}):
        return RedirectResponse(url="/ui/settings?error=error_tag_exists", status_code=303)


    new_tag = {
        "name": name,
        "slug": slug,
        "color": color,
        "description": description,
        "created_at": datetime.now()
    }
    tags_col.insert_one(new_tag)

    # --- JSON DOSYASINI GÜNCELLE (PERSISTENT DEFAULT) ---
    import json
    defaults_path = os.path.join(app_dir, "defaults.json")
    
    # Mevcut listeyi oku
    current_defaults = []
    if os.path.exists(defaults_path):
        try:
            with open(defaults_path, "r", encoding="utf-8") as f:
                current_defaults = json.load(f)
        except: pass
    
    # Eğer bu slug zaten dosyada yoksa ekle
    if not any(t.get("slug") == slug for t in current_defaults):
        # _id ve datetime objesi JSON'a gitmez, temiz kopya oluştur
        json_tag = {
            "name": name, 
            "slug": slug, 
            "color": color, 
            "description": description
        }
        current_defaults.append(json_tag)
        
        # Dosyayı güncelle
        with open(defaults_path, "w", encoding="utf-8") as f:
            json.dump(current_defaults, f, ensure_ascii=False, indent=4)

    return RedirectResponse(url="/ui/settings?msg=msg_tag_added", status_code=303)

@router.post("/ui/settings/tags/delete/{tag_id}")
async def delete_tag(tag_id: str):
    # Tag silindiğinde, maillerdeki referanslar (slug) kalır.
    # Ancak Dashboard'da tags_map içinde bulunamayacağı için sessizce yok sayılır (Soft fail).
    tags_col.delete_one({"_id": ObjectId(tag_id)})
    return RedirectResponse(url="/ui/settings?msg=msg_tag_deleted", status_code=303)

@router.post("/ui/settings/tags/update/{tag_id}")
async def update_tag(tag_id: str, name: str = Form(...), color: str = Form(...), description: str = Form(...)):
    user = users_col.find_one({"is_active": True})
    
    # Yeni slug oluştur (İsim değişmiş olabilir)
    slug = name.strip().lower().replace(" ", "-").replace("ı", "i").replace("ğ", "g").replace("ü", "u").replace("ş", "s").replace("ö", "o").replace("ç", "c")
    slug = re.sub(r'[^a-z0-9-]', '', slug)

    # Güncelle
    tags_col.update_one(
        {"_id": ObjectId(tag_id)},
        {"$set": {
            "name": name,
            "slug": slug,
            "color": color,
            "description": description,
            "updated_at": datetime.now()
        }}
    )
    return RedirectResponse(url="/ui/settings?msg=msg_tag_updated", status_code=303)

# --- WRITER (YENİ MAIL OLUŞTURMA) ---
@router.get("/ui/writer", response_class=HTMLResponse)
async def writer_page(request: Request, draft_id: Optional[str] = None):
    """
    Yeni mail yazma sayfası.
    Eğer 'draft_id' parametresi varsa, o taslağın verilerini çeker ve sayfaya doldurur.
    """
    user = users_col.find_one({"is_active": True})
    accounts = list(accounts_col.find({"user_id": user["_id"]}))
    
    draft = None
    if draft_id:
        try:
            draft = mails_col.find_one({"_id": ObjectId(draft_id)})
            if draft:
                draft["_id"] = str(draft["_id"])
        except:
            pass

    return templates.TemplateResponse("writer.html", {
        "request": request, 
        "user": user, 
        "accounts": accounts,
        "draft": draft # Template'de inputları doldurmak için
    })

@router.post("/ui/writer/generate")
async def generate_writer_draft(prompt: str = Form(...)):
    try:
        draft = generate_reply(prompt, tone="formal") 
        return {"draft": draft}
    except Exception as e:
        return {"draft": f"Hata: {str(e)}"}

@router.post("/ui/writer/send")
async def send_writer_mail(
    sender_email: str = Form(...), 
    to_email: str = Form(...), 
    subject: str = Form(...), 
    body: str = Form(...),
    draft_id: Optional[str] = Form(None) # Gönderilen taslağı silmek için ID
):
    user = users_col.find_one({"is_active": True})
    account = accounts_col.find_one({"email": sender_email})
    signature = account.get("signature", "") if account else user.get("signature", "")
    
    final_body = f"{body}\n\n---\n{signature}"
    is_sent, msg = send_gmail_via_user(sender_email, to_email, subject, final_body)
    
    if is_sent:
        # Mail başarıyla gönderildi, SENT olarak kaydet
        mails_col.insert_one({
            "user_email": sender_email, "from": sender_email, "to": to_email,
            "subject": subject, "body": body, "status": "SENT",
            "created_at": datetime.utcnow(), "type": "outbound"
        })

        # Eğer bu bir taslaktıysa, taslaklar klasöründen sil
        if draft_id and len(draft_id) > 10:
            mails_col.delete_one({"_id": ObjectId(draft_id)})

        return RedirectResponse(url="/ui/dashboard?msg=Mail+Gonderildi", status_code=303)
    else:
        return RedirectResponse(url=f"/ui/writer?error={msg}", status_code=303)

# --- SEMANTİK ARAMA API ENDPOINT'İ ---
@router.get("/ui/search-api")
async def search_mails(q: str = Query(..., min_length=1)):
    """
    Frontend'den gelen arama isteğini karşılar.
    MongoDB Atlas Vector Search kullanarak 'anlamsal' arama yapar.
    Örn: "Fatura" aratırsan, içinde fatura yazmasa bile ödeme maillerini bulur.
    """
    try:
        # 1. Kullanıcının sorgusunu vektöre çevir (Sayısal hale getir)
        # NOT: Embeddings modülü henüz tam yüklenmemişse boş dönebilir, kontrol edelim.
        query_vector = get_embedding(q)
        
        if not query_vector:
            # Fallback: Vektör oluşturulamazsa boş dön (veya basit regex arama yapılabilir)
            return {"results": [], "message": "Vektör oluşturulamadı veya model yüklenemedi."}

        # 2. MongoDB Aggregation Pipeline (Sorgu Hattı)
        pipeline = [
            {
                "$vectorSearch": {
                    "index": "vector_index", # database.py'de oluşturduğumuz indeks adı
                    "path": "embedding",     # Vektörün kayıtlı olduğu alan
                    "queryVector": query_vector,
                    "numCandidates": 100,    # Aday havuzu (performans ayarı)
                    "limit": 10              # En alakalı 10 sonucu getir
                }
            },
            {
                "$project": {
                    "_id": {"$toString": "$_id"}, # ObjectId'yi stringe çevir (JSON hatası almamak için)
                    "subject": 1,
                    "sender": 1,
                    "snippet": {"$substr": ["$body", 0, 150]}, # Metnin ilk 150 karakteri
                    "date": 1,
                    "score": {"$meta": "vectorSearchScore"} # Benzerlik puanı (Ne kadar alakalı?)
                }
            }
        ]
        
        # 3. Sorguyu çalıştır
        results = list(mails_col.aggregate(pipeline))
        
        return {"results": results}

    except Exception as e:
        print(f"❌ Arama Hatası: {e}")
        return {"results": [], "error": str(e)}