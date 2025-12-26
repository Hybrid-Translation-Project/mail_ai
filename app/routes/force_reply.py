from fastapi import APIRouter
from bson import ObjectId
from app.database import mails_col
from app.services.reply_generator import generate_reply

router = APIRouter()


@router.post("/force-reply/{mail_id}")
def force_reply(mail_id: str):
    mail = mails_col.find_one({"_id": ObjectId(mail_id)})

    if not mail:
        return {"error": "MAIL_NOT_FOUND"}

    reply = generate_reply(mail["body"], tone="formal")

    mails_col.update_one(
        {"_id": ObjectId(mail_id)},
        {"$set": {
            "reply_draft": reply,
            "status": "WAITING_APPROVAL",
            "forced": True
        }}
    )

    return {"status": "FORCED_REPLY"}
