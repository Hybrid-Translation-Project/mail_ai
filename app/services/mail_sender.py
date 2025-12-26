import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.core.security import decrypt_password

# app.database yerine app.utils.database üzerinden users_col çağrılıyor.
from app.database import users_col

def send_gmail_via_user(user_email: str, to_email: str, subject: str, body: str):
    """
    Kullanıcının veritabanındaki şifreli parolasını okur,
    çözer ve Gmail üzerinden maili gönderir.
    """
    try:
        # Kullanıcıyı email adresine göre veritabanından bul
        # (db.users yerine users_col kullanıyoruz)
        user = users_col.find_one({"email": user_email})
        
        if not user:
            print(f" Hata: {user_email} kullanıcısı veritabanında bulunamadı.")
            return False, "Kullanıcı bulunamadı."

        #Şifreli parolayı güvenlik modülü ile çöz
        try:
            decrypted_pass = decrypt_password(user["encrypted_password"])
        except Exception as e:
            print(f"Şifre çözme hatası: {e}")
            return False, "Kullanıcı şifresi çözülemedi (Encryption Key hatası olabilir)."

        # Mail Objesini Hazırla
        msg = MIMEMultipart()
        msg['From'] = user_email
        msg['To'] = to_email
        msg['Subject'] = subject

        # Mail içeriğini HTML olarak ekle (böylece kalın/italik yazı çalışır)
        msg.attach(MIMEText(body, 'html'))

        # Gmail SMTP Sunucusuna Bağlan (SSL - Port 465)
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        
        # Giriş yap ve gönder
        server.login(user_email, decrypted_pass)
        server.sendmail(user_email, to_email, msg.as_string())
        server.quit()
        
        print(f"Mail başarıyla gönderildi! (Kime: {to_email})")
        return True, "Başarılı"

    except smtplib.SMTPAuthenticationError:
        return False, "Gmail Giriş Hatası: Şifre yanlış veya Uygulama Şifresi (App Password) geçersiz."
    except Exception as e:
        print(f"Mail Gönderme Hatası: {str(e)}")
        return False, f"Teknik Hata: {str(e)}"