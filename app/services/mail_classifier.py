# LLaMA ile konuşmak için
from app.services.ollama_service import ask_llama

def should_reply(mail_text: str) -> bool:
    """
    Mail cevaplanmalı mı?
    True  -> cevap yaz
    False -> ignore et
    """

    # LLM’ye NET ve kısa bir talimat veriyoruz
    prompt = f"""
Bu mail otomatik, reklam veya spam mi?
Sadece YES veya NO cevapla.

MAIL:
{mail_text}
"""

    # LLaMA cevabını al
    result = ask_llama(prompt)

    # Büyük harfe çeviriyoruz (YES / yes / Yes fark etmesin)
    result = result.upper()

    # Eğer spam DEĞİLSE → cevap yaz
    # "NO" = spam değil
    return "NO" in result
