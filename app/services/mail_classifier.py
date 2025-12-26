# LLaMA ile konuşmak için Ollama servis fonksiyonunu import ediyoruz
from app.services.ollama_service import ask_llama


def should_reply(mail_text: str) -> dict:
    """
    Mail cevaplanmalı mı?

    return:
    {
        "should_reply": bool,
        "decision": "YES" | "NO" | "UNKNOWN",
        "raw_output": str
    }
    """


    prompt = f"""
You are an email filtering AI.

TASK:
Determine if the email below is a real human email that requires a reply (e.g., questions, meeting requests, confirmations).

RULES:
1. Reply ONLY with "YES" or "NO".
2. Do NOT write any explanation or reasoning.
3. Do NOT correct grammar or spelling.
4. If the email is spam, advertisement, or an automated notification, reply "NO".
5. If you are unsure, reply "YES".

EMAIL CONTENT:
{mail_text}

RESPONSE:
"""

    # LLaMA çağrısı
    result = ask_llama(prompt)

    # Fail-safe: model boş / None / patlak cevap dönerse
    # Risk almıyoruz → cevap yaz
    if not result:
        return {
            "should_reply": True,
            "decision": "UNKNOWN",
            "raw_output": ""
        }

    # Temizleme
    raw_output = result.strip()
    decision_upper = raw_output.upper()

    # Debug (Konsolda ne döndüğünü görmek için)
    print(f"LLM RAW OUTPUT: {raw_output}")

    # --- KARAR MEKANİZMASI ---
    # Model bazen "Answer: NO" veya "NO." (noktalı) dönebilir.
    # Bu yüzden sadece == "NO" demek yerine "içinde NO var mı" diye bakmak daha güvenli.
    
    # Eğer cevapta net bir şekilde NO varsa ve YES yoksa -> Cevaplama
    if "NO" in decision_upper and "YES" not in decision_upper:
        return {
            "should_reply": False,
            "decision": "NO",
            "raw_output": raw_output
        }

    # Diğer her durumda (YES dediğinde veya saçmaladığında) -> Cevapla
    return {
        "should_reply": True,
        "decision": "YES",
        "raw_output": raw_output
    }