import os
from fastapi import APIRouter, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from bson import ObjectId
from datetime import datetime
from dotenv import load_dotenv, set_key
from cryptography.fernet import Fernet

# Veritabanı ve Servisler
from app.database import mails_col, contacts_col, tasks_col, users_col
from app.services.mail_sender import send_gmail_via_user
from app.services.reply_generator import generate_reply, generate_decision_reply
from app.core.security import encrypt_password, verify_master_password

router = APIRouter()

# --- YAPILANDIRMA ---
current_dir = os.path.dirname(os.path.abspath(__file__))
app_dir = os.path.dirname(current_dir)
root_dir = os.path.dirname(app_dir)
ENV_PATH = os.path.join(root_dir, ".env")

load_dotenv(ENV_PATH, override=True)
templates = Jinja2Templates(directory=os.path.join(app_dir, "templates"))

# --- GİRİŞ SİSTEMİ ---

@router.get("/", response_class=HTMLResponse)
@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@router.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    """
    Hem mail adresini hem de setup.py ile belirlenen MASTER_PASSWORD'ü kontrol eder.
    """
    env_email = os.getenv("EMAIL", "").strip().replace('"', '').replace("'", "")
    env_master_pass = os.getenv("MASTER_PASSWORD", "").strip()
    
    # Güvenlik kontrolü: Mail ve Panel Şifresi eşleşmeli
    if username.strip() == env_email and verify_master_password(password, env_master_pass):
        return RedirectResponse(url="/ui/dashboard", status_code=303)
    
    return templates.TemplateResponse("login.html", {
        "request": request, 
        "error": "E-posta veya Panel Şifresi hatalı!"
    })

# --- ⚙️ AYARLAR VE HESAP YÖNETİMİ (YENİ) ---

@router.get("/ui/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    """Hesap bilgilerinin güncellendiği sayfa"""
    current_email = os.getenv("EMAIL", "")
    return templates.TemplateResponse("settings.html", {
        "request": request, 
        "current_email": current_email
    })

@router.post("/ui/settings/update-profile")
async def update_profile(email: str = Form(...), current_password: str = Form(...)):
    """Mail adresini günceller (Güvenlik için panel şifresi ister)"""
    env_master_pass = os.getenv("MASTER_PASSWORD", "").strip()
    
    if not verify_master_password(current_password, env_master_pass):
        return RedirectResponse(url="/ui/settings?error=Sifre+Hatali", status_code=303)
    
    set_key(ENV_PATH, "EMAIL", email)
    # MongoDB'deki kullanıcı kaydını da güncelle
    users_col.update_one({"is_active": True}, {"$set": {"email": email, "username": email}})
    
    return RedirectResponse(url="/ui/settings?msg=Profil+Guncellendi", status_code=303)

@router.post("/ui/settings/update-password")
async def update_panel_password(old_password: str = Form(...), new_password: str = Form(...)):
    """Web paneli giriş şifresini değiştirir"""
    env_master_pass = os.getenv("MASTER_PASSWORD", "").strip()
    
    if not verify_master_password(old_password, env_master_pass):
        return RedirectResponse(url="/ui/settings?error=Eski+Sifre+Hatali", status_code=303)
    
    set_key(ENV_PATH, "MASTER_PASSWORD", new_password)
    users_col.update_one({"is_active": True}, {"$set": {"master_password": new_password}})
    
    return RedirectResponse(url="/ui/settings?msg=Sifre+Degistirildi", status_code=303)

@router.post("/ui/settings/update-api-key")
async def update_api_key(new_app_password: str = Form(...), master_password: str = Form(...)):
    """16 haneli Google uygulama şifresini günceller"""
    env_master_pass = os.getenv("MASTER_PASSWORD", "").strip()
    
    if not verify_master_password(master_password, env_master_pass):
        return RedirectResponse(url="/ui/settings?error=Dogrulama+Sifresi+Hatali", status_code=303)
    
    # Yeni 16 haneli şifreyi Fernet ile şifrele
    encrypted_key = encrypt_password(new_app_password)
    set_key(ENV_PATH, "EMAIL_PASSWORD", encrypted_key)
    users_col.update_one({"is_active": True}, {"$set": {"app_password": encrypted_key}})
    
    return RedirectResponse(url="/ui/settings?msg=API+Anahtari+Guncellendi", status_code=303)

# --- 🚀 KOMUTA MERKEZİ (HOME) ---

@router.get("/ui/dashboard", response_class=HTMLResponse)
def home_dashboard(request: Request):
    stats = {
        "pending_mails": mails_col.count_documents({"status": "WAITING_APPROVAL"}),
        "pending_tasks": tasks_col.count_documents({"status": "WAITING_APPROVAL"}),
        "total_contacts": contacts_col.count_documents({}),
    }
    urgent_tasks = list(tasks_col.find({"status": "CONFIRMED"}).sort("due_date", 1).limit(5))
    for t in urgent_tasks: t["_id"] = str(t["_id"])

    return templates.TemplateResponse("home.html", {
        "request": request,
        "stats": stats,
        "urgent_tasks": urgent_tasks
    })

# --- 📥 GELEN KUTUSU & ARŞİV ---

@router.get("/ui", response_class=HTMLResponse)
def inbox(request: Request):
    waiting_mails = list(mails_col.find({"status": "WAITING_APPROVAL"}).sort("created_at", -1))
    for m in waiting_mails: m["_id"] = str(m["_id"])
    tasks = list(tasks_col.find({"status": "WAITING_APPROVAL"}))
    return templates.TemplateResponse("dashboard.html", {"request": request, "mails": waiting_mails, "tasks": tasks})

@router.get("/ui/history", response_class=HTMLResponse)
def history(request: Request):
    old_mails = list(mails_col.find({"status": {"$in": ["SENT", "CANCELED"]}}).sort("created_at", -1).limit(50))
    for m in old_mails: m["_id"] = str(m["_id"])
    return templates.TemplateResponse("history.html", {"request": request, "mails": old_mails})

# --- ✅ GÖREVLER VE KARAR AKSİYONLARI ---

@router.get("/ui/tasks", response_class=HTMLResponse)
async def tasks_page(request: Request):
    tasks = list(tasks_col.find().sort("created_at", -1))
    for t in tasks: t["_id"] = str(t["_id"])
    return templates.TemplateResponse("tasks.html", {"request": request, "tasks": tasks})

@router.post("/ui/task/approve/{task_id}")
async def approve_task(task_id: str):
    task = tasks_col.find_one({"_id": ObjectId(task_id)})
    if not task: return RedirectResponse(url="/ui/tasks")
    
    tasks_col.update_one({"_id": ObjectId(task_id)}, {"$set": {"status": "CONFIRMED"}})
    mail = mails_col.find_one({"from": task["sender"], "user_email": task["user_email"]})
    
    if mail:
        approval_draft = generate_decision_reply(mail["body"], decision="approve")
        mails_col.update_one({"_id": mail["_id"]}, {"$set": {"reply_draft": approval_draft}})
        return RedirectResponse(url=f"/ui/editor/{mail['_id']}", status_code=303)
    return RedirectResponse(url="/ui/tasks")

@router.post("/ui/task_action/{mail_id}/{action}")
async def editor_task_action(mail_id: str, action: str):
    mail = mails_col.find_one({"_id": ObjectId(mail_id)})
    if not mail: return RedirectResponse(url="/ui")
    
    new_draft = generate_decision_reply(mail["body"], decision=action, tone="formal")
    mails_col.update_one({"_id": ObjectId(mail_id)}, {"$set": {"reply_draft": new_draft}})
    return RedirectResponse(url=f"/ui/editor/{mail_id}", status_code=303)

# --- 🗑️ SİLME İŞLEMLERİ ---

@router.post("/ui/task/delete/{task_id}")
async def delete_task(task_id: str):
    tasks_col.delete_one({"_id": ObjectId(task_id)})
    return RedirectResponse(url="/ui/tasks", status_code=303)

@router.post("/ui/mail/delete/{mail_id}")
async def delete_mail(mail_id: str):
    mails_col.delete_one({"_id": ObjectId(mail_id)})
    return RedirectResponse(url=os.getenv("HTTP_REFERER", "/ui"), status_code=303)

# --- 👥 REHBER ---

@router.get("/ui/contacts", response_class=HTMLResponse)
async def contacts_page(request: Request):
    contacts = list(contacts_col.find().sort("name", 1))
    return templates.TemplateResponse("contacts.html", {"request": request, "contacts": contacts})

@router.get("/ui/contact/{email}", response_class=HTMLResponse)
async def contact_detail(request: Request, email: str):
    contact = contacts_col.find_one({"email": email})
    if not contact: return RedirectResponse(url="/ui/contacts")
    
    history_list = list(mails_col.find({"from": email}).sort("created_at", -1))
    for m in history_list: m["_id"] = str(m["_id"])
    ai_notes = contact.get("ai_notes", ["Bu branch için henüz AI çıkarımı yapılmadı."])
    
    return templates.TemplateResponse("contact_detail.html", {
        "request": request, 
        "contact_name": contact.get("name", email), 
        "history": history_list, 
        "ai_notes": ai_notes
    })

# --- 🔄 EDİTÖR İŞLEMLERİ ---

@router.get("/ui/editor/{mail_id}", response_class=HTMLResponse)
def editor(request: Request, mail_id: str):
    mail = mails_col.find_one({"_id": ObjectId(mail_id)})
    if not mail: return RedirectResponse(url="/ui")
    mail["_id"] = str(mail["_id"])
    return templates.TemplateResponse("editor.html", {"request": request, "mail": mail})

@router.post("/ui/update/{mail_id}")
def update_draft(mail_id: str, reply_draft: str = Form(...)):
    mails_col.update_one({"_id": ObjectId(mail_id)}, {"$set": {"reply_draft": reply_draft}})
    return RedirectResponse(url=f"/ui/editor/{mail_id}", status_code=303)

@router.post("/ui/approve/{mail_id}")
def send_approved_mail(mail_id: str, reply_draft: str = Form(...)):
    mail = mails_col.find_one({"_id": ObjectId(mail_id)})
    if not mail: return RedirectResponse(url="/ui")
    
    is_sent, _ = send_gmail_via_user(mail["user_email"], mail["from"], f"RE: {mail['subject']}", reply_draft)
    if is_sent:
        mails_col.update_one({"_id": ObjectId(mail_id)}, {"$set": {"status": "SENT", "handled_at": datetime.utcnow()}})
    
    return RedirectResponse(url="/ui/history", status_code=303)

@router.post("/ui/cancel/{mail_id}")
def cancel_mail(mail_id: str):
    mails_col.update_one({"_id": ObjectId(mail_id)}, {"$set": {"status": "CANCELED", "handled_at": datetime.utcnow()}})
    return RedirectResponse(url="/ui", status_code=303)

@router.post("/ui/regenerate/{mail_id}")
async def regenerate_mail(mail_id: str):
    mail = mails_col.find_one({"_id": ObjectId(mail_id)})
    if mail:
        new_draft = generate_reply(mail["body"], tone="formal")
        mails_col.update_one({"_id": ObjectId(mail_id)}, {"$set": {"reply_draft": new_draft}})
    return RedirectResponse(url=f"/ui/editor/{mail_id}", status_code=303)

@router.get("/ui/writer", response_class=HTMLResponse)
async def writer_page(request: Request):
    return templates.TemplateResponse("writer.html", {"request": request})