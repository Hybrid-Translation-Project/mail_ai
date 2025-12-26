from app.services.ollama_service import ask_llama
from app.utils.prompt_templates import TONE_INSTRUCTIONS, REPLY_PROMPT_TEMPLATE

def generate_reply(mail_text: str, tone: str = "formal") -> str:
    """
    Mail içeriğine göre kısa ve net cevap üretir.
    Prompt metinlerini harici dosyadan (prompt_templates.py) çeker.
    """

    # Eğer gelen tone listede yoksa varsayılan olarak "formal" seç
    tone = tone.lower()
    tone_instruction = TONE_INSTRUCTIONS.get(tone, TONE_INSTRUCTIONS["formal"])


    # prompt_templates.py dosyasındaki {yer_tutucuları} dolduruyoruz.
    prompt = REPLY_PROMPT_TEMPLATE.format(
        tone_instruction=tone_instruction,
        mail_text=mail_text
    )

    # 3. LLM (Ollama) Çağrısı
    reply = ask_llama(prompt)

    # 4. Güvenlik Kontrolleri
    if not reply:
        return ""

    # Fazlalıkları temizle
    reply = reply.strip()

    # Model bazen cevabı tırnak içine alır ("Merhaba..."), onları temizleyelim
    reply = reply.replace('"', '').replace("'", "")

    # Son güvenlik: Çok uzun cevapları kes (UI taşmasın diye)
    lines = reply.splitlines()
    if len(lines) > 8:
        reply = "\n".join(lines[:8])

    return reply