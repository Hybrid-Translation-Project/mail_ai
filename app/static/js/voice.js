// app/static/js/voice.js

let mediaRecorder;
let audioChunks = [];
let isRecording = false;    // Kayıt yapılıyor mu?
let isProcessing = false;   // Şu an sunucu cevap veriyor mu? (KİLİT)
let activeElement = null;   // Kullanıcının en son tıkladığı kutu (Odak)

const voiceBtn = document.getElementById('voiceBtn');

// Whisper'ın sessizlikte uydurduğu saçma cümleler (Filtre Listesi)
const IGNORED_PHRASES = [
    "sürekli izlediğiniz için teşekkürler",
    "izlediğiniz için teşekkürler",
    "teşekkürler",
    "thanks for watching",
    "altyazı",
    "muhammet ali" // Bazen rastgele isimler de uydurabilir
];

document.addEventListener('DOMContentLoaded', () => {
    
    // 1. Odaklanma Takibi (Focus Tracking)
    const inputs = ['subject', 'aiPrompt', 'mailBody', 'toEmail'];
    
    inputs.forEach(id => {
        const el = document.getElementById(id);
        if (el) {
            el.addEventListener('focus', () => {
                activeElement = el;
                // Görsel temizlik
                document.querySelectorAll('.form-control').forEach(i => i.classList.remove('voice-focus'));
                el.classList.add('voice-focus');
            });
        }
    });

    // Varsayılan Odak
    const defaultBody = document.getElementById('mailBody');
    if (defaultBody) {
        activeElement = defaultBody;
        defaultBody.classList.add('voice-focus');
    }

    // 2. Mikrofon Butonu Dinleyicisi
    if (voiceBtn) {
        voiceBtn.addEventListener('click', toggleRecording);
    }
});

// --- KAYIT MANTIĞI ---

async function toggleRecording() {
    // EĞER SİSTEM MEŞGULSE (PROCESSING), HİÇBİR ŞEY YAPMA (KİLİT)
    if (isProcessing) return;

    if (!isRecording) {
        // Kaydı Başlat
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            startRecording(stream);
        } catch (err) {
            console.error("Mikrofon hatası:", err);
            alert("Mikrofona erişilemedi! Lütfen izin verin.");
        }
    } else {
        // Kaydı Durdur
        stopRecording();
    }
}

function startRecording(stream) {
    mediaRecorder = new MediaRecorder(stream);
    audioChunks = [];
    isRecording = true;

    // Görsel: Kırmızı ve Kare İkon
    voiceBtn.classList.add('listening');
    voiceBtn.innerHTML = '<i class="fas fa-stop"></i>'; 

    mediaRecorder.ondataavailable = event => {
        audioChunks.push(event.data);
    };

    mediaRecorder.onstop = sendAudioToBackend;

    mediaRecorder.start();
    console.log("🎤 Dinliyorum...");
}

function stopRecording() {
    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
        mediaRecorder.stop();
        isRecording = false;
        
        // Mikrofon akışını kapat
        mediaRecorder.stream.getTracks().forEach(track => track.stop());
        
        // Buradaki görsel değişimi artık sendAudioToBackend yönetecek
        // (Spinner'a döneceği için burada ikonu değiştirmemize gerek yok)
    }
}

// --- BACKEND İLETİŞİMİ ---

async function sendAudioToBackend() {
    // 1. KİLİTLEME BAŞLIYOR
    isProcessing = true; 
    
    // Görsel: Gri renk ve Dönen Spinner İkonu
    voiceBtn.classList.remove('listening'); // Kırmızıyı kaldır
    voiceBtn.classList.add('processing');   // Gri yap
    voiceBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>'; // Dönen ikon
    voiceBtn.style.cursor = 'wait'; // Mouse imleci bekleme olsun

    const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
    const formData = new FormData();
    formData.append("file", audioBlob, "voice_command.wav");

    try {
        console.log("⏳ Sunucuya gönderiliyor...");
        const response = await fetch('/api/voice-command', {
            method: 'POST',
            body: formData
        });

        const result = await response.json();
        console.log("🧠 AI Cevabı:", result);

        processVoiceResult(result);

    } catch (error) {
        console.error("Backend hatası:", error);
        // Hata olsa bile kullanıcıya hissettirme, belki sadece internet gitti
    } finally {
        // 2. KİLİDİ AÇ (Her durumda, hata olsa bile burası çalışır)
        isProcessing = false;
        
        // Görsel: Eski haline (Mikrofon) dön
        voiceBtn.classList.remove('processing');
        voiceBtn.innerHTML = '<i class="fas fa-microphone"></i>';
        voiceBtn.style.cursor = 'pointer';
        console.log("🔓 Buton kilidi açıldı.");
    }
}

// --- SONUÇ İŞLEME ---

function processVoiceResult(data) {
    
    // --- FİLTRELEME (Halüsinasyon Kontrolü) ---
    // Eğer gelen yazı yasaklı listedeyse veya çok kısaysa (<2 karakter) yoksay.
    if (data.content) {
        const cleanText = data.content.toLowerCase().trim().replace(/[.,!]/g, ''); // Noktalamayı temizle kontrol için
        
        // Yasaklı cümlelerden biri geçiyor mu?
        const isIgnored = IGNORED_PHRASES.some(phrase => cleanText.includes(phrase));
        
        if (isIgnored || cleanText.length < 2) {
            console.warn("🚫 Halüsinasyon algılandı ve engellendi:", data.content);
            return; // Fonksiyondan çık, ekrana yazma
        }
    }

    // --- NORMAL İŞLEMLER ---
    
    if (data.type === 'command') {
        // Komut işlemleri aynı...
        if (data.action === 'send_mail') {
            if (typeof handleVoiceSend === 'function') handleVoiceSend();
        } 
        else if (data.action === 'confirm_send') {
            if (typeof handleVoiceConfirm === 'function') handleVoiceConfirm();
        }
        else if (data.action === 'clear_input') {
            if (activeElement && typeof handleVoiceClear === 'function') {
                handleVoiceClear(activeElement.id);
            }
        }
        else if (data.action === 'generate_ai') {
            if (typeof handleVoiceGenerate === 'function') handleVoiceGenerate();
        }
    } 
    else if (data.type === 'text') {
        if (activeElement) {
            const currentText = activeElement.value;
            const newText = data.content;
            
            activeElement.value = currentText ? currentText + " " + newText : newText;
            activeElement.dispatchEvent(new Event('input')); // Auto-save tetikle
        }
    }
}