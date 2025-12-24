# FastAPI'nin router yapısını kullanıyoruz.
# UI (arayüz) ile ilgili endpointleri ayrı bir dosyada toplamak için.
from fastapi import APIRouter, Request, Form

# HTML sayfası döndürmek için HTMLResponse,
# işlem sonrası başka sayfaya yönlendirmek için RedirectResponse kullanıyoruz.
from fastapi.responses import HTMLResponse, RedirectResponse

# FastAPI'nin Jinja2 template sistemi.
# HTML dosyalarını render etmek için kullanılır.
from fastapi.templating import Jinja2Templates

# MongoDB'deki mails collection'ına erişiyoruz.
from app.database import mails_col

# MongoDB ObjectId tipini kullanabilmek için.
from bson import ObjectId


# Bu dosyaya ait router tanımı.
# main.py içinde app.include_router(ui.router) şeklinde eklenecek.
router = APIRouter()

# HTML template dosyalarının bulunduğu klasörü tanımlıyoruz.
templates = Jinja2Templates(directory="app/templates")


@router.get("/ui", response_class=HTMLResponse)
def approval_ui(request: Request):
    """
    Kullanıcının tarayıcıdan açtığı ana ekran.

    Bu ekran iki bölümden oluşur:
    1) Üstte: Onay bekleyen mail (varsa)
    2) Altta: Daha önce gönderilmiş mailler tablosu
    """

    # 1️⃣ ONAY BEKLEYEN MAIL
    # MongoDB'de status'u WAITING_APPROVAL olan
    # EN ESKİ maili alıyoruz.
    # Bu bir kuyruk (queue) mantığıdır.
    waiting_mail = mails_col.find_one(
        {"status": "WAITING_APPROVAL"},
        sort=[("created_at", 1)]
    )

    # Eğer bekleyen mail varsa:
    # MongoDB _id alanı ObjectId olduğu için
    # HTML tarafında kullanabilmek adına string'e çeviriyoruz.
    if waiting_mail:
        waiting_mail["_id"] = str(waiting_mail["_id"])

    # 2️⃣ DAHA ÖNCE GÖNDERİLEN MAILLER
    # Kullanıcı "az önce ne gönderdim?" diye bakabilsin diye
    # status'u SENT olan mailleri alıyoruz.
    sent_mails = list(
        mails_col.find(
            {"status": "SENT"},
            sort=[("created_at", -1)]  # En yeni en üstte
        ).limit(10)  # UI şişmesin diye son 10 mail
    )

    # Gönderilen maillerin ObjectId'lerini de string'e çeviriyoruz.
    for mail in sent_mails:
        mail["_id"] = str(mail["_id"])

    # approval.html dosyasını render ediyoruz.
    # mail -> bekleyen mail
    # sent_mails -> gönderilmiş mailler tablosu
    return templates.TemplateResponse(
        "approval.html",
        {
            "request": request,       # FastAPI bunu zorunlu ister
            "mail": waiting_mail,     # Üstte gösterilecek mail
            "sent_mails": sent_mails  # Alttaki tablo
        }
    )


@router.post("/ui/update/{mail_id}")
def update_reply(mail_id: str, reply_draft: str = Form(...)):
    """
    Kullanıcı AI tarafından yazılan cevabı
    textarea üzerinden düzenlediğinde buraya gelir.
    """

    # Belirtilen mailin reply_draft alanını güncelliyoruz.
    mails_col.update_one(
        {"_id": ObjectId(mail_id)},           # Hangi mail?
        {"$set": {"reply_draft": reply_draft}}  # Yeni cevap
    )

    # Güncellemeden sonra tekrar UI ekranına dön.
    # Aynı mail kullanıcıya tekrar gösterilir.
    return RedirectResponse(url="/ui", status_code=303)


@router.post("/ui/approve/{mail_id}")
def approve_and_next(mail_id: str):
    """
    Kullanıcı 'Onayla ve Gönder' dediğinde:
    - Mail APPROVED olur
    - n8n bu maili alıp gönderecektir
    """

    mails_col.update_one(
        {"_id": ObjectId(mail_id)},
        {"$set": {"status": "APPROVED"}}
    )

    # Sonraki maili göstermek için tekrar UI'ya dön.
    return RedirectResponse(url="/ui", status_code=303)


@router.post("/ui/cancel/{mail_id}")
def cancel_and_next(mail_id: str):
    """
    Kullanıcı bu maili göndermek istemezse:
    - Status CANCELED olur
    - Bir daha UI'da görünmez
    """

    mails_col.update_one(
        {"_id": ObjectId(mail_id)},
        {"$set": {"status": "CANCELED"}}
    )

    # UI'ya geri dön → sıradaki mail gelir.
    return RedirectResponse(url="/ui", status_code=303)
