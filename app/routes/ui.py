import os
import re
from typing import Optional, List
from fastapi import APIRouter, Request, Form, Depends, HTTPException, Body, Query
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
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
        "status": "WAITING_APPROVAL",
        "type": {"$ne": "outbound"}
    }).sort("created_at", -1))
    
    for m in waiting_mails: m["_id"] = str(m["_id"])

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

    return templates.TemplateResponse("editor.html", {
        "request": request, 
        "mail": mail, 
        "user": user, 
        "account_signature": account_signature
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
    
    is_sent, error_msg = send_gmail_via_user(mail["user_email"], mail["from"], f"RE: {mail['subject']}", final_body)
    
    if is_sent:
        mails_col.update_one({"_id": ObjectId(mail_id)}, {"$set": {"status": "SENT", "handled_at": datetime.utcnow()}})
        
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
        return RedirectResponse(url="/ui/history?msg=Gonderildi", status_code=303)
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
    mail = mails_col.find_one({"_id": ObjectId(mail_id)})
    if not mail: return RedirectResponse(url="/ui/history")
    return templates.TemplateResponse("view_mail.html", {"request": request, "mail": mail, "user": user})

# --- REHBER ---
@router.get("/ui/contacts", response_class=HTMLResponse)
async def contacts_page(request: Request):
    user = users_col.find_one({"is_active": True})
    contacts = list(contacts_col.find().sort("name", 1))
    accounts = list(accounts_col.find({"user_id": user["_id"]}))
    return templates.TemplateResponse("contacts.html", {"request": request, "contacts": contacts, "user": user, "accounts": accounts})

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

# --- YENİ EKLENEN: SEMANTİK ARAMA API ENDPOINT'İ ---
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