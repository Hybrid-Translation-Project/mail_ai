import io
import pdfplumber
import pytesseract
from PIL import Image
import os

# NOT: Eğer "Tesseract bulunamadı" hatası alırsan alttaki satırın başındaki # işaretini kaldır
# ve kendi kurduğun yolu yaz. (Genelde C:\Program Files\Tesseract-OCR\tesseract.exe olur)
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def extract_text_from_pdf(file_bytes):
    """PDF dosyasının içindeki metni (Selectable Text) okur."""
    text = ""
    try:
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
    except Exception as e:
        print(f"📄 PDF Okuma Hatası: {e}")
    return text

def extract_text_from_image(file_bytes):
    """Resim dosyasındaki yazıları (OCR) okur."""
    text = ""
    try:
        image = Image.open(io.BytesIO(file_bytes))
        # Türkçe (tur) ve İngilizce (eng) dillerini aynı anda dener
        text = pytesseract.image_to_string(image, lang='tur+eng')
    except Exception as e:
        print(f"📷 Resim OCR Hatası: {e}")
    return text

def analyze_attachment(filename, file_bytes):
    """Dosya uzantısına göre doğru okuyucuyu seçer."""
    filename = filename.lower()
    content = ""
    
    # 1. PDF ise
    if filename.endswith(".pdf"):
        content = extract_text_from_pdf(file_bytes)
        
    # 2. Resim ise (Fatura fotoğrafı vb.)
    elif filename.endswith((".png", ".jpg", ".jpeg", ".tiff", ".bmp")):
        content = extract_text_from_image(file_bytes)
        
    return content.strip()