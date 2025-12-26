import os
from fastapi import APIRouter, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from bson import ObjectId
from datetime import datetime
from dotenv import load_dotenv
from cryptography.fernet import Fernet

# Veritabanı ve Mail servisi
from app.database import mails_col
from app.services.mail_sender import send_gmail_via_user

router = APIRouter()

# --- DİNAMİK YOL VE .ENV YAPILANDIRMASI ---
current_dir = os.path.dirname(os.path.abspath(__file__)) # app/routes
app_dir = os.path.dirname(current_dir)                 # app
root_dir = os.path.dirname(app_dir)                    # Ana Dizin

# .env dosyasını ana dizinden zorla yükle
env_path = os.path.join(root_dir, ".env")
load_dotenv(env_path, override=True)

# Templates yolunu ayarla
templates_path = os.path.join(app_dir, "templates")
templates = Jinja2Templates(directory=templates_path)

# --- GİRİŞ / LOGIN MEKANİZMASI ---

@router.get("/", response_class=HTMLResponse)
@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Giriş sayfasını gösterir"""
    return templates.TemplateResponse("login.html", {"request": request})

@router.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    """Giriş bilgilerini .env ile (şifreli veya düz) doğrular"""
    
    # .env'den ham verileri al
    env_email = os.getenv("EMAIL")
    env_pass = os.getenv("EMAIL_PASSWORD")
    env_key = os.getenv("ENCRYPTION_KEY")

    if not env_email or not env_pass:
        return templates.TemplateResponse("login.html", {
            "request": request, 
            "error": "Sistem hatası: .env dosyası bulunamadı veya boş!"
        })

    # Temizlik: Tırnakları ve kenar boşluklarını sil
    correct_email = env_email.strip().replace('"', '').replace("'", "")
    
    # Şifre Kontrolü: Encrypted (Fernet) mı yoksa Düz Metin mi?
    decrypted_pass = ""
    try:
        if env_pass.startswith("gAAAA") and env_key:
            # Şifreli ise çöz
            f = Fernet(env_key.encode())
            decrypted_pass = f.decrypt(env_pass.encode()).decode()
        else:
            # Düz metin ise temizle
            decrypted_pass = env_pass.strip().replace('"', '').replace("'", "")
    except Exception as e:
        # Çözme başarısız olursa düz metin kabul et
        decrypted_pass = env_pass.strip().replace('"', '').replace("'", "")

    # Karşılaştırma (Büyük/Küçük harf duyarlı)
    if username.strip() == correct_email and password.strip() == decrypted_pass:
        return RedirectResponse(url="/ui", status_code=303)
    else:
        # Debug için terminale bas (Giriş yapamazsan buraya bak kanka)
        print(f"--- GİRİŞ HATASI ---")
        print(f"Deneme: {username.strip()}")
        print(f"Beklenen: {correct_email}")
        print(f"--------------------")
        return templates.TemplateResponse("login.html", {
            "request": request, 
            "error": "Email veya şifre hatalı!"
        })

# --- DASHBOARD (LİSTE) SAYFASI ---

@router.get("/ui", response_class=HTMLResponse)
def dashboard(request: Request):
    """Onay bekleyen TÜM mailleri listeler"""
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

# --- EYLEMLER ---

@router.post("/ui/update/{mail_id}")
def update_draft(mail_id: str, reply_draft: str = Form(...)):
    mails_col.update_one(
        {"_id": ObjectId(mail_id)},
        {"$set": {"reply_draft": reply_draft}}
    )
    return RedirectResponse(url=f"/ui/editor/{mail_id}", status_code=303)

@router.post("/ui/approve/{mail_id}")
def approve_mail(mail_id: str, reply_draft: str = Form(...)):
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
    mails_col.update_one(
        {"_id": ObjectId(mail_id)},
        {"$set": {"status": "CANCELED", "handled_at": datetime.utcnow()}}
    )
    return RedirectResponse(url="/ui", status_code=303)