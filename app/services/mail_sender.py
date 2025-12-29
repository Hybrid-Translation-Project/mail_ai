import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.core.security import decrypt_password
from app.database import users_col

def send_gmail_via_user(user_email: str, to_email: str, subject: str, body: str):
    """
    Kullanıcının veritabanındaki şifreli parolasını okur,
    çözer ve Gmail üzerinden HTML formatında mail gönderir.
    """
    try:
        # 1. Kullanıcıyı ve Şifreyi Doğrula
        user = users_col.find_one({"email": user_email})
        
        if not user:
            print(f"Hata: {user_email} kullanıcısı veritabanında bulunamadı.")
            return False, "Kullanıcı bulunamadı."

        # Şifre alanını esnek kontrol et
        enc_pass = user.get("password") or user.get("encrypted_password")
        
        if not enc_pass:
            return False, "Veritabanında şifre alanı bulunamadı."

        # Şifreyi güvenlik modülü ile çöz
        try:
            decrypted_pass = decrypt_password(enc_pass)
        except Exception as e:
            print(f"Şifre çözme hatası: {e}")
            return False, "Şifre çözülemedi (Anahtar/Key hatası)."

        # 2. Mail Objesini Hazırla
        msg = MIMEMultipart()
        msg['From'] = user_email
        msg['To'] = to_email
        msg['Subject'] = subject

        # AI'nın oluşturduğu taslaklardaki satır sonları ve formatın (HTML)
        # korunması için 'html' ve 'utf-8' parametreleri kritiktir.
        msg.attach(MIMEText(body, 'html', 'utf-8')) 

        # 3. SMTP Sunucusuna Bağlan ve Gönder
        # Gmail için SSL üzerinden 465 portunu kullanıyoruz.
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        
        server.login(user_email, decrypted_pass)
        server.sendmail(user_email, to_email, msg.as_string())
        server.quit()
        
        print(f" Mail başarıyla gönderildi: {to_email}")
        return True, "Başarılı"

    except smtplib.SMTPAuthenticationError:
        print(f"Kimlik Doğrulama Hatası: {user_email} için Uygulama Şifresi hatalı.")
        return False, "Gmail Giriş Hatası: Şifre veya Uygulama Şifresi geçersiz."
    except Exception as e:
        print(f"Kritik Mail Gönderme Hatası: {str(e)}")
        return False, f"Teknik Hata: {str(e)}"