import json
import re
from app.services.ollama_service import ask_llama

def extract_insights_and_tasks(mail_body):
    """
    Mail içeriğini derinlemesine analiz eder:
    1. 'task': Yapılacak iş, toplantı veya randevu bilgilerini çeker.
    2. 'insight': Kişi/Şirket hakkında kalıcı karakter/alışkanlık notları çıkarır.
    3. 'category': Mailin türünü (Teklif, Şikayet, Ödeme vb.) belirler.
    4. 'urgency_score': 0-100 arası aciliyet puanı verir.
    """

    prompt = f"""
    Sen profesyonel bir yönetici asistanısın. Aşağıdaki mail içeriğini analiz et ve SADECE JSON formatında sonuç dön.
    
    ANALİZ KRİTERLERİN:
    1. 'task': Mailde bir randevu, toplantı, deadline veya aksiyon gereken bir iş var mı? 
       Varsa kısa bir başlık ve tarih (YYYY-MM-DD formatında) yaz.
    2. 'insight': Gönderen kişi/kurum hakkında kalıcı bir bilgi (Örn: "Cuma günleri erken çıkıyor") var mı?
    3. 'category': Maili şu kategorilerden birine ata: "Teklif", "Şikayet", "Ödeme", "Soru", "Randevu", "Diğer".
    4. 'urgency_score': Bu mail ne kadar acil? (0: Hiç acil değil, 100: Çok kritik/Hemen cevaplanmalı).
    5. 'is_proposal': Bu bir teklif veya onay gerektiren bir soru mu? (True/False).

    MAIL İÇERİĞİ:
    {mail_body}

    KURALLAR:
    - SADECE JSON formatında cevap ver.
    - 'category' alanı mutlaka yukarıdaki seçeneklerden biri olmalı.
    - 'urgency_score' tam sayı (integer) olmalı.

    CEVAP FORMATI:
    {{
        "task": {{ "title": "Başlık", "date": "YYYY-MM-DD" }},
        "insight": "Kalıcı not",
        "category": "Kategori Adı",
        "urgency_score": 85,
        "is_proposal": true
    }}
    """

    try:
        # LLaMA ile analiz yapıyoruz
        raw_response = ask_llama(prompt)
        
        # JSON yapısını metin içerisinden cımbızla çekiyoruz
        json_match = re.search(r'\{.*\}', raw_response, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group(0))
            
            # Varsayılan değerlerin kontrolü ve güvenli veri çekme
            if "task" not in data: data["task"] = None
            if "insight" not in data: data["insight"] = None
            if "category" not in data: data["category"] = "Diğer"
            if "urgency_score" not in data: data["urgency_score"] = 0
            if "is_proposal" not in data: data["is_proposal"] = False
            
            return data
        
        return {"task": None, "insight": None, "category": "Diğer", "urgency_score": 0, "is_proposal": False}

    except Exception as e:
        print(f"❌ Akıllı Extraction Hatası: {e}")
        return {"task": None, "insight": None, "category": "Diğer", "urgency_score": 0, "is_proposal": False}