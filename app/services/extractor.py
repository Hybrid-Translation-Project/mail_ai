import json
import re
from app.services.ollama_service import ask_llama

def extract_insights_and_tasks(mail_body):
    """
    Mail içeriğini derinlemesine analiz eder:
    1. 'task': Yapılacak iş, toplantı veya randevu bilgilerini çeker.
    2. 'insight': Kişi/Şirket hakkında kalıcı karakter/alışkanlık notları çıkarır.
    3. 'is_proposal': İçeriğin bir onay bekleyen teklif (Soru/Öneri) olup olmadığını belirler.
    """

    prompt = f"""
    Sen profesyonel bir yönetici asistanısın. Aşağıdaki mail içeriğini analiz et ve SADECE JSON formatında sonuç dön.
    
    ANALİZ KRİTERLERİN:
    1. 'task': Mailde bir randevu, toplantı, deadline veya aksiyon gereken bir iş var mı? 
       Varsa kısa bir başlık ve tarih (bulabiliyorsan) yaz.
    2. 'insight': Gönderen kişi/kurum hakkında kalıcı bir bilgi (Örn: "Salı günleri kapalılar", "WhatsApp sevmiyor") var mı?
    3. 'is_proposal': Bu bir teklif veya soru mu? (Örn: "Müsait misiniz?", "Gelebilir misiniz?") 
       Eğer onay gerektiren bir soruysa true, kesinleşmiş bir bilgilendirmeyse false yaz.

    MAIL İÇERİĞİ:
    {mail_body}

    KURALLAR:
    - SADECE JSON formatında cevap ver.
    - Metin açıklaması ekleme.
    - Bilgi yoksa o alanı null bırak.

    CEVAP FORMATI:
    {{
        "task": {{ "title": "Başlık", "date": "YYYY-MM-DD" }},
        "insight": "Kalıcı not",
        "is_proposal": true/false
    }}
    """

    try:
        # LLaMA ile analiz yapıyoruz
        raw_response = ask_llama(prompt)
        
        # JSON yapısını metin içerisinden cımbızla çekiyoruz
        json_match = re.search(r'\{.*\}', raw_response, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group(0))
            
            # Varsayılan değerlerin kontrolü
            if "task" not in data: data["task"] = None
            if "insight" not in data: data["insight"] = None
            if "is_proposal" not in data: data["is_proposal"] = False
            
            return data
        
        return {"task": None, "insight": None, "is_proposal": False}

    except Exception as e:
        print(f" Akıllı Extraction Hatası: {e}")
        return {"task": None, "insight": None, "is_proposal": False}