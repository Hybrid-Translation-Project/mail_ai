import os
from fastapi import APIRouter, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from bson import ObjectId
from datetime import datetime
from dotenv import load_dotenv, set_key

# Veritabanı ve Servisler
from app.database import mails_col, contacts_col, tasks_col, users_col
from app.services.mail_sender import send_gmail_via_user
from app.services.reply_generator import generate_reply, generate_decision_reply
from app.core.security import encrypt_password, verify_master_password, hash_master_password

router = APIRouter()

# --- DİZİN VE ŞABLON AYARLARI ---
current_dir = os.path.dirname(os.path.abspath(__file__)) 
app_dir = os.path.dirname(current_dir) 
root_dir = os.path.dirname(app_dir) 
ENV_PATH = os.path.join(root_dir, ".env")

templates = Jinja2Templates(directory=os.path.join(app_dir, "templates"))

# Başlangıçta .env'yi oku
load_dotenv(ENV_PATH, override=True)

def is_configured():
    if not os.path.exists(ENV_PATH): return False
    return users_col.find_one({"is_active": True}) is not None

# --- KURULUM ---
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
        set_key(ENV_PATH, "OLLAMA_MODEL", "llama3.2")
        
        users_col.update_one({"email": email}, {"$set": {
            "full_name": full_name, "company_name": company_name, "email": email,
            "app_password": enc_pass, "master_password": hashed_master,
            "signature": signature, "is_active": True, "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }}, upsert=True)
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
    return templates.TemplateResponse("tasks.html", {"request": request, "tasks": tasks, "user": user})

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

# --- MAİL İŞLEMLERİ ---
@router.get("/ui", response_class=HTMLResponse)
def inbox(request: Request):
    user = users_col.find_one({"is_active": True})
    waiting_mails = list(mails_col.find({"status": "WAITING_APPROVAL"}).sort("created_at", -1))
    for m in waiting_mails: m["_id"] = str(m["_id"])
    return templates.TemplateResponse("dashboard.html", {"request": request, "mails": waiting_mails, "user": user})

@router.get("/ui/editor/{mail_id}", response_class=HTMLResponse)
async def mail_editor(request: Request, mail_id: str):
    user = users_col.find_one({"is_active": True})
    mail = mails_col.find_one({"_id": ObjectId(mail_id)})
    if not mail: return RedirectResponse(url="/ui")
    
    # Otomatik taslak oluşturma
    if not mail.get("reply_draft"):
        draft = generate_reply(mail["body"], tone="formal")
        mails_col.update_one({"_id": ObjectId(mail_id)}, {"$set": {"reply_draft": draft}})
        mail["reply_draft"] = draft

    return templates.TemplateResponse("editor.html", {"request": request, "mail": mail, "user": user})

# --- KARAR MEKANİZMASI VE BUTONLAR (GÜNCELLENDİ) ---
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
    
    # Kararı (decision) ve yeni taslağı kaydediyoruz
    mails_col.update_one(
        {"_id": ObjectId(mail_id)}, 
        {"$set": {"reply_draft": new_draft, "decision": decision_val}}
    )
    return RedirectResponse(url=f"/ui/editor/{mail_id}", status_code=303)

@router.post("/ui/mail/delete/{mail_id}")
async def delete_mail(mail_id: str):
    mails_col.delete_one({"_id": ObjectId(mail_id)})
    return RedirectResponse(url="/ui?msg=Silindi", status_code=303)

@router.post("/ui/update/{mail_id}")
async def update_draft(mail_id: str, reply_draft: str = Form(...)):
    mails_col.update_one({"_id": ObjectId(mail_id)}, {"$set": {"reply_draft": reply_draft}})
    return RedirectResponse(url=f"/ui/editor/{mail_id}?msg=Kaydedildi", status_code=303)

# --- ONAY VE GÖNDERME (GÜNCELLENDİ) ---
@router.post("/ui/approve/{mail_id}")
def send_approved_mail(mail_id: str, reply_draft: str = Form(...)):
    mail = mails_col.find_one({"_id": ObjectId(mail_id)})
    user = users_col.find_one({"is_active": True})
    
    final_body = f"{reply_draft}\n\n---\n{user.get('signature', '')}"
    is_sent, error_msg = send_gmail_via_user(mail["user_email"], mail["from"], f"RE: {mail['subject']}", final_body)
    
    if is_sent:
        mails_col.update_one({"_id": ObjectId(mail_id)}, {"$set": {"status": "SENT", "handled_at": datetime.utcnow()}})
        
        # SADECE KARAR 'REJECT' DEĞİLSE GÖREV OLUŞTUR
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

# --- YENİ MAİL GÖRÜNTÜLEME ROTASI (EKLENDİ) ---
@router.get("/ui/view/{mail_id}", response_class=HTMLResponse)
async def view_mail(request: Request, mail_id: str):
    """Geçmiş mailleri sadece görüntülemek için (Read-Only)"""
    user = users_col.find_one({"is_active": True})
    mail = mails_col.find_one({"_id": ObjectId(mail_id)})
    if not mail: return RedirectResponse(url="/ui/history")
    
    return templates.TemplateResponse("view_mail.html", {"request": request, "mail": mail, "user": user})

@router.get("/ui/contacts", response_class=HTMLResponse)
async def contacts_page(request: Request):
    user = users_col.find_one({"is_active": True})
    contacts = list(contacts_col.find().sort("name", 1))
    return templates.TemplateResponse("contacts.html", {"request": request, "contacts": contacts, "user": user})

@router.get("/ui/contact/{email}", response_class=HTMLResponse)
async def contact_detail(request: Request, email: str):
    user = users_col.find_one({"is_active": True})
    contact = contacts_col.find_one({"email": email})
    if not contact: return RedirectResponse(url="/ui/contacts")
    history = list(mails_col.find({"from": email}).sort("created_at", -1))
    for h in history: h["_id"] = str(h["_id"])
    return templates.TemplateResponse("contact_detail.html", {"request": request, "contact": contact, "history": history, "user": user})

@router.get("/ui/writer", response_class=HTMLResponse)
async def writer_page(request: Request):
    user = users_col.find_one({"is_active": True})
    return templates.TemplateResponse("writer.html", {"request": request, "user": user})

@router.get("/ui/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    user = users_col.find_one({"is_active": True})
    return templates.TemplateResponse("settings.html", {"request": request, "user": user})