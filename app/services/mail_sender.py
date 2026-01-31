import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, Sequence, Union
from app.core.security import decrypt_password
from app.database import users_col, accounts_col  # accounts_col eklendi

def _normalize_message_id(value: str) -> str:
    v = (value or "").strip()
    if not v:
        return ""
    # RFC style: "<id@domain>"
    if not v.startswith("<"):
        v = "<" + v
    if not v.endswith(">"):
        v = v + ">"
    return v

def _normalize_references(value: Union[str, Sequence[str], None]) -> str:
    """
    References header: space-separated message-id list.
    Input: already string, or list/tuple of ids (with or without <>).
    """
    if not value:
        return ""
    if isinstance(value, str):
        return " ".join([_normalize_message_id(x) for x in value.split() if x.strip()])
    return " ".join([_normalize_message_id(x) for x in value if str(x).strip()])

def send_gmail_via_user(
    user_email: str,
    to_email: str,
    subject: str,
    body: str,
    *,
    message_id: Optional[str] = None,
    in_reply_to: Optional[str] = None,
    references: Union[str, Sequence[str], None] = None,
):
    """
    Belirtilen gönderici (user_email) için önce ACCOUNTS tablosuna, 
    bulamazsa USERS tablosuna bakar, şifreyi çözer ve maili gönderir.
    """
    try:
        print(f"📤 Mail Gönderimi Başlatılıyor: {user_email} -> {to_email}")

        # --- 1. HESAP VE ŞİFRE TESPİTİ ---
        enc_pass = None
        
        # A) Önce yeni 'accounts' tablosuna bak (Multi-Account)
        account = accounts_col.find_one({"email": user_email})
        if account:
            enc_pass = account.get("password")
        
        # B) Eğer orada yoksa eski 'users' tablosuna bak (Fallback/Yedek)
        if not enc_pass:
            user = users_col.find_one({"email": user_email})
            if user:
                enc_pass = user.get("app_password") or user.get("encrypted_password")

        # C) Hiçbir yerde bulunamadıysa hata ver
        if not enc_pass:
            print(f"Hata: {user_email} gönderici hesabı sistemde kayıtlı değil.")
            return False, "Gönderici hesabı bulunamadı."

        # --- 2. ŞİFRE ÇÖZME ---
        try:
            decrypted_pass = decrypt_password(enc_pass)
        except Exception as e:
            print(f"Şifre çözme hatası: {e}")
            return False, "Şifre çözülemedi (Anahtar hatası)."

        # --- 3. MAIL OBJESİNİ HAZIRLA ---
        msg = MIMEMultipart()
        msg['From'] = user_email
        msg['To'] = to_email
        msg['Subject'] = subject
        
        # Threading headers (reply gibi görünmesi için kritik)
        norm_mid = _normalize_message_id(message_id) if message_id else ""
        if norm_mid:
            msg["Message-ID"] = norm_mid
        
        norm_irt = _normalize_message_id(in_reply_to) if in_reply_to else ""
        if norm_irt:
            msg["In-Reply-To"] = norm_irt
        
        norm_refs = _normalize_references(references)
        if norm_refs:
            msg["References"] = norm_refs

        # HTML formatında içerik ekle
        msg.attach(MIMEText(body, 'html', 'utf-8')) 

        # --- 4. SMTP SUNUCUSUNA BAĞLAN VE GÖNDER ---
        # İleride Outlook vb. eklenirse buraya 'if provider == ...' eklenebilir.
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        
        try:
            server.login(user_email, decrypted_pass)
            server.sendmail(user_email, to_email, msg.as_string())
            print(f"✅ Mail başarıyla gönderildi: {to_email}")
            return True, "Başarılı"
        
        except smtplib.SMTPAuthenticationError:
            print(f"⛔ Giriş Hatası: {user_email} şifresi kabul edilmedi.")
            return False, "Gmail Giriş Hatası: Şifre reddedildi."
        finally:
            server.quit()

    except Exception as e:
        print(f"Kritik Mail Gönderme Hatası: {str(e)}")
        return False, f"Teknik Hata: {str(e)}"