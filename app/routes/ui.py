import os
from fastapi import APIRouter, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from bson import ObjectId
from datetime import datetime

# Veritabanı ve Mail servisi
from app.database import mails_col
from app.services.mail_sender import send_gmail_via_user

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

# --- GİRİŞ / LOGIN MEKANİZMASI ---

@router.get("/", response_class=HTMLResponse)
@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Giriş sayfasını gösterir"""
    return templates.TemplateResponse("login.html", {"request": request})

@router.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    """Giriş bilgilerini .env ile doğrular"""
    # .env'deki bilgileri alıyoruz
    correct_email = os.getenv("EMAIL")
    correct_pass = os.getenv("EMAIL_PASSWORD")

    if username == correct_email and password == correct_pass:
        # Not: Gerçek bir sistemde burada 'session' veya 'cookie' set edilmelidir.
        # Şimdilik basit tutmak adına doğrulanınca direkt dashboard'a yönlendiriyoruz.
        return RedirectResponse(url="/ui", status_code=303)
    else:
        return templates.TemplateResponse("login.html", {
            "request": request, 
            "error": "Email veya şifre hatalı!"
        })

# --- DASHBOARD (LİSTE) SAYFASI ---

@router.get("/ui", response_class=HTMLResponse)
def dashboard(request: Request):
    """Onay bekleyen TÜM mailleri listeler (Yeni > Eski)"""
    waiting_mails = list(mails_col.find(
        {"status": "WAITING_APPROVAL"},
        sort=[("created_at", -1)] 
    ))
    
    for mail in waiting_mails:
        mail["_id"] = str(mail["_id"])

    return templates.TemplateResponse("dashboard.html", {
        "request": request, 
        "mails": waiting_mails
    })

# --- EDİTÖR SAYFASI ---

@router.get("/ui/editor/{mail_id}", response_class=HTMLResponse)
def editor(request: Request, mail_id: str):
    """Seçilen tek bir maili düzenleme ekranı"""
    try:
        mail = mails_col.find_one({"_id": ObjectId(mail_id)})
    except:
        return RedirectResponse(url="/ui")
    
    if not mail:
        return RedirectResponse(url="/ui")
        
    mail["_id"] = str(mail["_id"])
    
    return templates.TemplateResponse("editor.html", {
        "request": request, 
        "mail": mail
    })

# --- ARŞİV SAYFASI ---

@router.get("/ui/history", response_class=HTMLResponse)
def history(request: Request):
    """Gönderilmiş veya İptal edilmiş son 50 mail"""
    old_mails = list(mails_col.find(
        {"status": {"$in": ["SENT", "CANCELED"]}},
        sort=[("created_at", -1)]
    ).limit(50))
    
    for mail in old_mails:
        mail["_id"] = str(mail["_id"])

    return templates.TemplateResponse("history.html", {
        "request": request, 
        "mails": old_mails
    })

# --- EYLEMLER (GÖNDER / KAYDET / İPTAL) ---

@router.post("/ui/update/{mail_id}")
def update_draft(mail_id: str, reply_draft: str = Form(...)):
    """Sadece taslağı kaydeder"""
    mails_col.update_one(
        {"_id": ObjectId(mail_id)},
        {"$set": {"reply_draft": reply_draft}}
    )
    return RedirectResponse(url=f"/ui/editor/{mail_id}", status_code=303)

@router.post("/ui/approve/{mail_id}")
def approve_mail(mail_id: str, reply_draft: str = Form(...)):
    """Maili gönderir ve Arşive atar"""
    mail = mails_col.find_one({"_id": ObjectId(mail_id)})
    if not mail:
        return RedirectResponse(url="/ui", status_code=303)

    is_sent, msg = send_gmail_via_user(
        user_email=mail["user_email"],
        to_email=mail["from"],
        subject=f"RE: {mail['subject']}",
        body=reply_draft
    )

    status = "SENT" if is_sent else "ERROR"
    mails_col.update_one(
        {"_id": ObjectId(mail_id)},
        {"$set": {
            "status": status, 
            "reply_draft": reply_draft,
            "handled_at": datetime.utcnow()
        }}
    )
    
    return RedirectResponse(url="/ui", status_code=303)

@router.post("/ui/cancel/{mail_id}")
def cancel_mail(mail_id: str):
    """Maili iptal eder"""
    mails_col.update_one(
        {"_id": ObjectId(mail_id)},
        {"$set": {"status": "CANCELED", "handled_at": datetime.utcnow()}}
    )
    return RedirectResponse(url="/ui", status_code=303)