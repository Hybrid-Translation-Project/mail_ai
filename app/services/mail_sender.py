import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.core.security import decrypt_password
from app.database import users_col

def send_gmail_via_user(user_email: str, to_email: str, subject: str, body: str):
    """
    Kullanıcının veritabanındaki şifreli parolasını okur,
    çözer ve Gmail üzerinden maili gönderir.
    """
    try:
        # Kullanıcıyı bul
        user = users_col.find_one({"email": user_email})
        
        if not user:
            print(f"Hata: {user_email} kullanıcısı veritabanında bulunamadı.")
            return False, "Kullanıcı bulunamadı."

        # Şifre alanını kontrol et (Hem password hem encrypted_password bakıyoruz)
        enc_pass = user.get("password") or user.get("encrypted_password")
        
        if not enc_pass:
            return False, "Veritabanında şifre alanı bulunamadı."

        # Şifreyi çöz
        try:
            decrypted_pass = decrypt_password(enc_pass)
        except Exception as e:
            print(f"Şifre çözme hatası: {e}")
            return False, "Şifre çözülemedi (Anahtar hatası)."

        # Mail Objesini Hazırla
        msg = MIMEMultipart()
        msg['From'] = user_email
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain')) # Genelde düz metin daha güvenlidir

        # Gmail SMTP Bağlantısı
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(user_email, decrypted_pass)
        server.sendmail(user_email, to_email, msg.as_string())
        server.quit()
        
        print(f"Mail başarıyla gönderildi: {to_email}")
        return True, "Başarılı"

    except smtplib.SMTPAuthenticationError:
        return False, "Gmail Giriş Hatası: Uygulama Şifresi geçersiz."
    except Exception as e:
        print(f"Mail Gönderme Hatası: {str(e)}")
        return False, f"Hata: {str(e)}"