# LLaMA çağrısı için
from app.services.ollama_service import ask_llama

def generate_reply(mail_text: str, tone: str) -> str:
    """
    Mail içeriğine ve tona göre cevap üretir
    tone: formal / friendly (ileride genişler)
    """

    # Prompt, tonu belirleyerek oluşturulur
    prompt = f"""
Bu mail için {tone} bir cevap yaz.
Kısa, net ve profesyonel olsun.
İmza ekleme.

MAIL:
{mail_text}
"""

    # LLaMA cevabını döndür
    return ask_llama(prompt)
