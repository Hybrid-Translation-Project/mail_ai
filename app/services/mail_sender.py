import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.core.security import decrypt_password
from app.database import users_col, accounts_col  # accounts_col eklendi

def send_gmail_via_user(user_email: str, to_email: str, subject: str, body: str):
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