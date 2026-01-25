// app/static/js/editor.js

const draftTextarea = document.getElementById('replyDraft');
const statusIndicator = document.getElementById('saveStatus');
let saveTimeout;

// Sayfa yüklendiğinde çalışacaklar
document.addEventListener('DOMContentLoaded', () => {
    if (draftTextarea) {
        // Kullanıcı her tuşa bastığında sayacı sıfırla
        draftTextarea.addEventListener('input', () => {
            showStatus('writing');
            clearTimeout(saveTimeout);
            
            // Kullanıcı yazmayı bıraktıktan 1000ms (1 saniye) sonra ARKA PLANDA kaydet
            saveTimeout = setTimeout(saveDraft, 1000);
        });
    }
});

// Durum Göstergesini Güncelleme
function showStatus(state) {
    if (!statusIndicator) return;

    if (state === 'writing') {
        statusIndicator.innerText = '✍️ Yazıyor...';
        statusIndicator.className = 'save-status saving';
    } else if (state === 'saving') {
        statusIndicator.innerText = '💾 Kaydediliyor...';
        statusIndicator.className = 'save-status saving';
    } else if (state === 'saved') {
        statusIndicator.innerText = '✅ Güncel';
        statusIndicator.className = 'save-status saved';
    } else if (state === 'error') {
        statusIndicator.innerText = '❌ Hata!';
        statusIndicator.className = 'save-status text-danger';
    }
}

// Taslağı Sunucuya Kaydet (Sessiz Auto-Save)
// Bu fonksiyon, gelen kutusundaki mailin 'reply_draft' alanını günceller.
// Maili 'Taslaklar' sayfasına taşımaz, statüsünü değiştirmez.
async function saveDraft() {
    // Textarea yoksa hata vermesin diye kontrol
    if (!draftTextarea) return;

    const mailId = draftTextarea.getAttribute('data-mail-id');
    const content = draftTextarea.value;

    showStatus('saving');

    try {
        // ui.py'deki api_save_draft fonksiyonuna gider
        const response = await fetch('/save-draft', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                mail_id: mailId,
                draft_content: content
            })
        });

        if (response.ok) {
            showStatus('saved');
        } else {
            console.error('Kayıt başarısız');
            showStatus('error');
        }
    } catch (error) {
        console.error('Bağlantı hatası:', error);
        showStatus('error');
    }
}

// Manuel "Şimdi Kaydet" butonu için
function forceSave() {
    clearTimeout(saveTimeout);
    saveDraft();
}

// Geçmiş versiyona tıklayınca editöre yükle
function restoreVersion(content) {
    if (!content) return; // Boş veri gelirse işlem yapma

    if (confirm("Mevcut yazdıklarınız bu versiyonla değiştirilecek. Emin misiniz?")) {
        draftTextarea.value = content;
        // Değişiklik olduğu için hemen yeni halini de kaydedelim
        saveDraft();
    }
}

// AI Aksiyon Butonları (Yenile, Onayla, Reddet)
// BU KISIM DÜZELTİLDİ: Artık POST isteği gönderiyor.
async function handleAction(action, mailId) {
    let confirmMsg = "";
    
    if (action === 'regenerate') {
        confirmMsg = "Yapay zeka taslağı baştan yazacak. Mevcut düzenlemeleriniz kaybolabilir. Devam mı?";
    } else if (action === 'approve') {
        confirmMsg = "Cevap, 'Kabul Ediyorum' tonunda yeniden yazılacak. Devam mı?";
    } else if (action === 'reject') {
        confirmMsg = "Cevap, 'Reddediyorum' tonunda yeniden yazılacak. Devam mı?";
    }

    if (confirm(confirmMsg)) {
        // Backend (ui.py) POST isteği beklediği için dinamik bir form oluşturup gönderiyoruz.
        // Bu sayede sayfa yenilenir ve yeni AI verisi ekrana gelir.
        const form = document.createElement('form');
        form.method = 'POST';
        form.action = `/ui/task_action/${mailId}/${action}`;
        
        // Formu sayfaya ekle ve gönder
        document.body.appendChild(form);
        form.submit();
    }
}