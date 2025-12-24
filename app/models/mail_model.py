from datetime import datetime

def create_mail(data: dict):
    """
    Gelen bir mail için MongoDB dokümanını standart hale getirir
    """

    return {
        # Maili gönderen kişinin email adresi
        "from": data["from"],

        # Mail konusu
        "subject": data.get("subject", ""),

        # Gelen mailin ham içeriği
        "body": data["body"],

        # AI tarafından üretilmiş cevap taslağı
        # Henüz gönderilmemiştir
        "reply_draft": data.get("reply_draft"),

        # Bu mail için kullanılan konuşma tonu
        # contact.default_tone’dan gelir
        "tone": data.get("tone", "formal"),

        # Mailin durumu (queue mantığı)
        # NEW → AUTO_REPLIED → WAITING_APPROVAL → SENT / CANCELED
        "status": data.get("status", "NEW"),

        # Bu mail spam mi olarak işaretlendi?
        "is_spam": data.get("is_spam", False),

        # LLaMA karar açıklaması (neden cevapladı / cevaplamadı)
        # Debug ve eğitim için çok faydalı
        "decision_reason": data.get("decision_reason"),

        # Mail sisteme ne zaman girdi
        "created_at": datetime.utcnow(),

        # Kullanıcı ne zaman onayladı / iptal etti
        "handled_at": None
    }
