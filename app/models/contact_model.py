from datetime import datetime

def create_contact(data: dict):
    """
    Bir kişi (contact) için standart MongoDB dokümanı oluşturur
    """

    return {
        # Kişinin mail adresi (unique gibi düşünebilirsin)
        "email": data["email"].strip().lower(),

        # Kişinin adı (opsiyonel ama UI için çok faydalı)
        "name": data.get("name"),

        # Bu kişiyle varsayılan konuşma tonu
        # formal | friendly
        "default_tone": data.get("default_tone", "formal"),

        # Bu kişiyle kaç kez mailleşildi
        "mail_count": data.get("mail_count", 0),

        # Kullanıcının bu kişiyle olan ilişki notu (opsiyonel)
        # Örn: "müşteri", "arkadaş", "yönetici"
        "tag": data.get("tag"),

        # Oluşturulma tarihi
        "created_at": datetime.utcnow(),

        # En son mailleşme zamanı
        "last_contact_at": None
    }
