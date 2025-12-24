# FastAPI router
from fastapi import APIRouter

# MongoDB mails collection
from app.database import mails_col

# MongoDB ObjectId için
from bson import ObjectId

router = APIRouter()

@router.get("/next-mail")
def next_mail():
    """
    Onay bekleyen EN ESKİ maili getirir
    """

    mail = mails_col.find_one(
        {"status": "WAITING_APPROVAL"},      # Sadece bekleyenler
        sort=[("created_at", 1)]             # FIFO mantığı
    )

    # Bekleyen mail yoksa
    if not mail:
        return {"message": "NO_MAIL"}

    # ObjectId JSON’da sorun çıkarır → string’e çevir
    mail["_id"] = str(mail["_id"])
    return mail


@router.post("/mail/{mail_id}/approve")
def approve(mail_id: str):
    """
    Kullanıcı maili onayladı
    """

    mails_col.update_one(
        {"_id": ObjectId(mail_id)},          # Hangi mail
        {"$set": {"status": "SENT"}}         # Gönderildi olarak işaretle
    )

    return {"status": "SENT"}


@router.post("/mail/{mail_id}/cancel")
def cancel(mail_id: str):
    """
    Kullanıcı maili iptal etti
    """

    mails_col.update_one(
        {"_id": ObjectId(mail_id)},
        {"$set": {"status": "CANCELED"}}     # Gönderilmeyecek
    )

    return {"status": "CANCELED"}
