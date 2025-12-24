# FastAPI router
from fastapi import APIRouter

# MongoDB mails collection
from app.database import mails_col

# Mail cevaplanmalı mı?
from app.services.mail_classifier import should_reply

# AI cevap üretimi
from app.services.reply_generator import generate_reply

# Router tanımı
router = APIRouter()

@router.post("/inbox")
def receive_mail(payload: dict):
    """
    n8n bu endpoint’e mail gönderir
    payload = { from, subject, body }
    """

    # Mail içeriğini al
    mail_text = payload["body"]

    # Spam / otomatik kontrolü
    if not should_reply(mail_text):
        # Spam ise hiçbir şey yapma
        return {"status": "IGNORED"}

    # AI cevap üretir (şimdilik herkes formal)
    reply = generate_reply(mail_text, tone="formal")

    # Mail DB’ye kaydedilir (GÖNDERİLMEZ)
    mails_col.insert_one({
        "from": payload["from"],            # Gönderen
        "subject": payload["subject"],      # Konu
        "body": mail_text,                  # Gelen mail
        "reply_draft": reply,               # AI taslak
        "status": "WAITING_APPROVAL"        # Kullanıcı onayı bekliyor
    })

    # n8n’e bilgi dön
    return {"status": "QUEUED"}
