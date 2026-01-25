import json
import re
from app.services.ollama_service import ask_llama
from app.utils.prompt_templates import TONE_INSTRUCTIONS, REPLY_PROMPT_TEMPLATE

def extract_json_safe(text: str) -> dict:
    """
    AI çıktısından sadece JSON kısmını cımbızla çeker (HATA ÇÖZÜCÜ FONKSİYON).
    Öncesindeki veya sonrasındaki gevezelikleri temizler.
    """
    if not text:
        return {}

    # 1. Yöntem: Direkt dene (Eğer AI temiz verdiyse)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 2. Yöntem: Regex ile ilk '{' ve son '}' arasını bul
    try:
        # DOTALL bayrağı, yeni satır karakterlerini de kapsamasını sağlar
        match = re.search(r'(\{.*\})', text, re.DOTALL)
        if match:
            json_str = match.group(1)
            return json.loads(json_str)
    except Exception as e:
        print(f"JSON Parse Hatası (Regex sonrası): {e}")
        
    # 3. Eğer hiçbiri çalışmazsa boş döndür (Sistemi patlatma)
    return {}

def generate_reply(mail_text: str, tone: str = "formal") -> str:
    """
    Genel mail cevapları üretir (Gelen kutusunda otomatik oluşan taslaklar için).
    """
    tone = tone.lower()
    tone_instruction = TONE_INSTRUCTIONS.get(tone, TONE_INSTRUCTIONS["formal"])

    prompt = REPLY_PROMPT_TEMPLATE.format(
        tone_instruction=tone_instruction,
        mail_text=mail_text
    )

    reply = ask_llama(prompt)
    return _clean_reply(reply)

def generate_decision_reply(mail_text: str, decision: str, tone: str = "formal") -> str:
    """
    Kullanıcının 'approve' (Kabul) veya 'reject' (Red) kararına göre özel mail üretir.
    """
    tone = tone.lower()
    tone_instruction = TONE_INSTRUCTIONS.get(tone, TONE_INSTRUCTIONS["formal"])
    
    # Karara göre AI'ya verilecek net talimat
    if decision == "approve":
        decision_goal = "Kullanıcı bu teklifi/toplantıyı KABUL EDİYOR. Nazikçe onaylayan, teşekkür eden ve olumlu geri dönüş yapan bir cevap yaz."
    else:
        decision_goal = "Kullanıcı bu teklifi/toplantıyı REDDEDİYOR. Nazikçe teşekkür eden ama şu an için uygun olmadığını/olumsuz olduğunu belirten profesyonel bir red cevabı yaz."

    prompt = f"""
    ### ROL
    Sen profesyonel bir yönetici asistanısın.

    ### GELEN MAİL İÇERİĞİ
    {mail_text}

    ### KULLANICI KARARI VE HEDEF
    {decision_goal}

    ### DİL VE TON
    Dil: Gelen mail ile aynı dilde cevap ver.
    Ton: {tone_instruction}

    ### KURAL
    - Sadece mail gövdesini yaz. 
    - Giriş (Selam) ve Çıkış (İmza yeri) dahil olsun.
    - Gereksiz açıklamalar veya 'İşte cevabınız' gibi girişler yapma.
    """

    reply = ask_llama(prompt)
    return _clean_reply(reply)

def analyze_email_for_task(mail_text: str, sender: str = "") -> dict:
    """
    Gelen maili analiz edip içinden görev, tarih ve aciliyet çıkarır.
    JSON formatında döner.
    """
    prompt = f"""
    Aşağıdaki e-postayı analiz et. Eğer içinde bir görev, toplantı talebi veya hatırlatma varsa JSON formatında çıkar.
    Eğer net bir görev yoksa boş bir JSON {{}} döndür.

    FORMAT (Kesinlikle bu formatta ver):
    {{
        "title": "Görevin kısa başlığı (Örn: Fatura Ödemesi)",
        "date": "YYYY-MM-DD (Eğer tarih yoksa null)",
        "urgency_score": 1-10 arası bir sayı (10 çok acil),
        "category": "Toplantı/Fatura/Talep/Diğer"
    }}

    E-POSTA:
    {mail_text}
    """
    
    response = ask_llama(prompt)
    
    # İŞTE BURASI: Hata veren json.loads yerine güvenli fonksiyonu kullanıyoruz
    return extract_json_safe(response)

def _clean_reply(reply: str) -> str:
    """AI cevabını temizleyen ve formatlayan yardımcı fonksiyon"""
    if not reply:
        return ""
    
    # Gereksiz tırnakları ve boşlukları temizle
    reply = reply.strip().strip('"').strip("'")
    
    # Eğer AI 'Konu:' veya 'Subject:' diye başlık eklerse onları temizle (Editor sayfasında sadece body lazım)
    lines = reply.splitlines()
    cleaned_lines = [line for line in lines if not line.lower().startswith(("subject:", "konu:", "re:"))]
    
    # Satır limiti kontrolü
    if len(cleaned_lines) > 20: # Limiti biraz artırdım, bazen uzun mailler gerekebilir
        reply = "\n".join(cleaned_lines[:20])
    else:
        reply = "\n".join(cleaned_lines)
        
    return reply