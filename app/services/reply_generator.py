from app.services.ollama_service import ask_llama
from app.utils.prompt_templates import TONE_INSTRUCTIONS, REPLY_PROMPT_TEMPLATE

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

def _clean_reply(reply: str) -> str:
    """AI cevabını temizleyen ve formatlayan yardımcı fonksiyon"""
    if not reply:
        return ""
    
    # Gereksiz tırnakları ve boşlukları temizle
    reply = reply.strip().strip('"').strip("'")
    
    # Eğer AI 'Konu:' veya 'Subject:' diye başlık eklerse onları temizle (Editor sayfasında sadece body lazım)
    lines = reply.splitlines()
    cleaned_lines = [line for line in lines if not line.lower().startswith(("subject:", "konu:", "re:"))]
    
    # Profesyonel maillerde 8 satır bazen yetmeyebilir (imza ve boşluklar dahil), sınırı 12'ye çektim.
    if len(cleaned_lines) > 12:
        reply = "\n".join(cleaned_lines[:12])
    else:
        reply = "\n".join(cleaned_lines)
        
    return reply